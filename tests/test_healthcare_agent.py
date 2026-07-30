import json

import pytest

from app.memory.memory_manager import MemoryManager

from .conftest import assistant_message, tool_call


def test_agent_recalls_name_across_two_turns(agent_factory):
    manager = MemoryManager()

    def answer_name_question(request):
        messages = request["messages"]
        memory_contexts = [
            message["content"]
            for message in messages
            if isinstance(message, dict)
            and message["role"] == "system"
            and "known user memory" in message["content"]
        ]

        assert memory_contexts
        assert '"name": "Deepak"' in memory_contexts[-1]
        return assistant_message("Your name is Deepak.")

    agent, client = agent_factory(
        [
            assistant_message("Nice to meet you, Deepak."),
            answer_name_question,
        ],
        memory_manager=manager,
    )

    first_response = agent.chat("My name is Deepak")
    second_response = agent.chat("What's my name?")

    assert first_response == "Nice to meet you, Deepak."
    assert second_response == "Your name is Deepak."
    assert manager.load("deepak").preferences["name"] == "Deepak"
    assert len(client.completions.calls) == 2


def test_agent_registers_phase_two_healthcare_tools(agent_factory):
    agent, _ = agent_factory([assistant_message("Done")])

    definitions = agent.registry.get_tool_definitions()
    tool_names = {
        definition["function"]["name"]
        for definition in definitions
    }

    assert tool_names == {
        "provider_search",
        "verify_insurance",
        "search_availability",
        "select_appointment_slot",
    }


def test_agent_reaches_confirmation_in_multi_step_tool_loop(
    agent_factory,
):
    agent, client = agent_factory(
        [
            assistant_message(
                tool_calls=[
                    tool_call(
                        "provider-call",
                        "provider_search",
                        json.dumps(
                            {
                                "location": "Plano",
                                "specialty": "Dermatology",
                                "gender": "Female",
                            }
                        ),
                    )
                ]
            ),
            assistant_message(
                tool_calls=[
                    tool_call(
                        "insurance-call",
                        "verify_insurance",
                        json.dumps(
                            {
                                "insurance_name": "BCBS",
                                "provider_name": "Dr. Sarah Johnson",
                                "provider_location": "Plano",
                                "specialty": "Dermatology",
                                "service_date": "2026-08-04",
                            }
                        ),
                    )
                ]
            ),
            assistant_message(
                tool_calls=[
                    tool_call(
                        "availability-call",
                        "search_availability",
                        json.dumps(
                            {
                                "provider_id": (
                                    "provider-sarah-johnson"
                                ),
                                "provider_location_id": (
                                    "location-sarah-plano"
                                ),
                                "start_date": "2026-08-04",
                                "end_date": "2026-08-04",
                                "modality": "in_person",
                            }
                        ),
                    )
                ]
            ),
            assistant_message(
                "I found a 10:00 AM appointment. Would you like it?"
            ),
            assistant_message(
                tool_calls=[
                    tool_call(
                        "selection-call",
                        "select_appointment_slot",
                        json.dumps(
                            {
                                "slot_id": (
                                    "slot-sarah-plano-20260804-1000"
                                )
                            }
                        ),
                    )
                ]
            ),
            assistant_message(
                "Please confirm the selected appointment."
            ),
        ]
    )

    options_response = agent.chat(
        "Find a dermatologist appointment for August 4."
    )
    confirmation_response = agent.chat(
        "Select the 10:00 AM appointment."
    )

    assert options_response == (
        "I found a 10:00 AM appointment. Would you like it?"
    )
    assert confirmation_response == (
        "Please confirm the selected appointment."
    )
    assert len(client.completions.calls) == 6

    tool_messages = [
        message
        for message in agent.messages
        if isinstance(message, dict) and message["role"] == "tool"
    ]

    assert [
        message["tool_call_id"]
        for message in tool_messages
    ] == [
        "provider-call",
        "insurance-call",
        "availability-call",
        "selection-call",
    ]

    provider_result = json.loads(tool_messages[0]["content"])
    insurance_result = json.loads(tool_messages[1]["content"])
    availability_result = json.loads(tool_messages[2]["content"])
    selection_result = json.loads(tool_messages[3]["content"])

    assert provider_result[0]["name"] == "Dr. Sarah Johnson"
    assert provider_result[0]["provider_id"] == (
        "provider-sarah-johnson"
    )
    assert insurance_result["accepted"] is True
    assert insurance_result["network_status"] == "in_network"
    assert insurance_result["health_plan_id"] == "plan-bcbs-ppo"
    assert availability_result["workflow_state"] == (
        "awaiting_selection"
    )
    assert availability_result["slots"][0]["slot_id"] == (
        "slot-sarah-plano-20260804-1000"
    )
    assert selection_result["workflow_state"] == (
        "awaiting_confirmation"
    )
    assert selection_result["requires_confirmation"] is True

    workflow = (
        agent.healthcare_services.scheduling_workflows
        .get_for_conversation("deepak", "conversation-deepak")
    )
    assert workflow is not None
    assert workflow.state.value == "awaiting_confirmation"
    assert workflow.selection is not None
    assert workflow.selection.slot_id == (
        "slot-sarah-plano-20260804-1000"
    )


def test_agent_propagates_llm_errors(agent_factory):
    agent, _ = agent_factory([RuntimeError("model unavailable")])

    with pytest.raises(RuntimeError, match="model unavailable"):
        agent.chat("Hello")
