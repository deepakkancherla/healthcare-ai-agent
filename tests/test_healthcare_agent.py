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


def test_agent_registers_existing_healthcare_tools(agent_factory):
    agent, _ = agent_factory([assistant_message("Done")])

    definitions = agent.registry.get_tool_definitions()
    tool_names = {
        definition["function"]["name"]
        for definition in definitions
    }

    assert tool_names == {
        "provider_search",
        "verify_insurance",
        "book_appointment",
    }


def test_agent_runs_existing_multi_step_tool_loop(agent_factory):
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
                            }
                        ),
                    )
                ]
            ),
            assistant_message(
                tool_calls=[
                    tool_call(
                        "booking-call",
                        "book_appointment",
                        json.dumps(
                            {
                                "provider_name": "Dr. Sarah Johnson",
                                "patient_name": "Deepak",
                                "appointment_date": "2026-08-04",
                                "appointment_time": "10:00",
                            }
                        ),
                    )
                ]
            ),
            assistant_message(
                "Your appointment is confirmed. Confirmation: ABC123."
            ),
        ]
    )

    response = agent.chat(
        "Find a dermatologist and book an appointment."
    )

    assert response == (
        "Your appointment is confirmed. Confirmation: ABC123."
    )
    assert len(client.completions.calls) == 4

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
        "booking-call",
    ]

    provider_result = json.loads(tool_messages[0]["content"])
    insurance_result = json.loads(tool_messages[1]["content"])
    booking_result = json.loads(tool_messages[2]["content"])

    assert provider_result[0]["name"] == "Dr. Sarah Johnson"
    assert insurance_result["accepted"] is True
    assert booking_result == {
        "provider_name": "Dr. Sarah Johnson",
        "patient_name": "Deepak",
        "appointment_date": "2026-08-04",
        "appointment_time": "10:00",
        "confirmation_number": "ABC123",
        "status": "confirmed",
    }


def test_agent_propagates_llm_errors(agent_factory):
    agent, _ = agent_factory([RuntimeError("model unavailable")])

    with pytest.raises(RuntimeError, match="model unavailable"):
        agent.chat("Hello")
