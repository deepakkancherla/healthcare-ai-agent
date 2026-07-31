import json

import pytest

from app.infrastructure.synthetic.composition import (
    build_synthetic_repositories,
    build_synthetic_services,
)
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


def test_agent_registers_phase_three_healthcare_tools(agent_factory):
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
        "prepare_booking_confirmation",
        "book_confirmed_appointment",
    }


def test_agent_completes_confirmed_multi_turn_booking(
    agent_factory,
):
    repositories = build_synthetic_repositories()
    services = build_synthetic_services(repositories)

    def request_confirmed_booking(request):
        preparation = next(
            json.loads(message["content"])
            for message in request["messages"]
            if isinstance(message, dict)
            and message.get("tool_call_id") == "preparation-call"
        )
        return assistant_message(
            tool_calls=[
                tool_call(
                    "booking-call",
                    "book_confirmed_appointment",
                    json.dumps(
                        {
                            "confirmation_fingerprint": (
                                preparation[
                                    "confirmation_fingerprint"
                                ]
                            ),
                            "confirmed": True,
                        }
                    ),
                )
            ]
        )

    def return_authoritative_confirmation(request):
        booking_result = next(
            json.loads(message["content"])
            for message in request["messages"]
            if isinstance(message, dict)
            and message.get("tool_call_id") == "booking-call"
        )
        assert set(booking_result) == {
            "appointment_id",
            "status",
            "confirmation_number",
        }
        return assistant_message(
            "Your appointment is confirmed. Confirmation: "
            f"{booking_result['confirmation_number']}."
        )

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
                tool_calls=[
                    tool_call(
                        "preparation-call",
                        "prepare_booking_confirmation",
                        "{}",
                    )
                ]
            ),
            assistant_message(
                (
                    "Please confirm: Dr. Sarah Johnson, Dermatology, "
                    "100 Synthetic Health Way, Plano, TX 75024, "
                    "August 4 at 10:00 AM America/Chicago, in person, "
                    "verified in-network."
                )
            ),
            request_confirmed_booking,
            return_authoritative_confirmation,
        ],
        healthcare_services=services,
    )

    options_response = agent.chat(
        "Find a dermatologist appointment for August 4."
    )
    preparation_response = agent.chat(
        "Select the 10:00 AM appointment."
    )
    workflow = services.scheduling_workflows.get_for_conversation(
        "deepak",
        "conversation-deepak",
    )
    assert workflow is not None
    assert workflow.state.value == "awaiting_confirmation"
    assert workflow.confirmation is not None
    assert repositories.appointments.list_all() == []

    booking_response = agent.chat("Confirm.")

    assert options_response == (
        "I found a 10:00 AM appointment. Would you like it?"
    )
    assert preparation_response == (
        "Please confirm: Dr. Sarah Johnson, Dermatology, "
        "100 Synthetic Health Way, Plano, TX 75024, "
        "August 4 at 10:00 AM America/Chicago, in person, "
        "verified in-network."
    )
    appointment = repositories.appointments.list_all()[0]
    assert booking_response == (
        "Your appointment is confirmed. Confirmation: "
        f"{appointment.confirmation_number}."
    )
    assert len(client.completions.calls) == 9

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
        "preparation-call",
        "booking-call",
    ]

    provider_result = json.loads(tool_messages[0]["content"])
    insurance_result = json.loads(tool_messages[1]["content"])
    availability_result = json.loads(tool_messages[2]["content"])
    selection_result = json.loads(tool_messages[3]["content"])
    preparation_result = json.loads(tool_messages[4]["content"])
    booking_result = json.loads(tool_messages[5]["content"])

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
    assert preparation_result["summary"]["provider_name"] == (
        "Dr. Sarah Johnson"
    )
    assert len(
        preparation_result["confirmation_fingerprint"]
    ) == 64
    assert booking_result == {
        "appointment_id": appointment.appointment_id,
        "status": "confirmed",
        "confirmation_number": appointment.confirmation_number,
    }

    confirmed_workflow = (
        services.scheduling_workflows.get_for_conversation(
            "deepak",
            "conversation-deepak",
        )
    )
    assert confirmed_workflow is not None
    assert confirmed_workflow.state.value == "confirmed"
    assert confirmed_workflow.appointment_id == (
        appointment.appointment_id
    )
    assert confirmed_workflow.selection is not None
    assert confirmed_workflow.selection.slot_id == (
        "slot-sarah-plano-20260804-1000"
    )


def test_agent_propagates_llm_errors(agent_factory):
    agent, _ = agent_factory([RuntimeError("model unavailable")])

    with pytest.raises(RuntimeError, match="model unavailable"):
        agent.chat("Hello")
