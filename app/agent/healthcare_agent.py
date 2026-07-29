import json
import logging

from app.config import DEFAULT_MODEL, TEMPERATURE
from app.infrastructure.synthetic.composition import (
    HealthcareServices,
    build_synthetic_services,
)
from app.llm.llm_client import get_llm_client
from app.memory.memory_extractor import MemoryExtractor
from app.memory.memory_manager import MemoryManager
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.tools.insurance import (
    InsuranceVerificationRequest,
    insurance_verification_tool,
    verify_insurance,
)
from app.tools.provider_search import (
    provider_search,
    provider_search_tool,
    ProviderSearchRequest,
)

from app.tools.tool_registry import (
    ToolRegistry,
    RegisteredTool,
)

from app.tools.appointment import (
    AppointmentBookingRequest,
    appointment_booking_tool,
    book_appointment,
)


logger = logging.getLogger(__name__)


class HealthcareAgent:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        memory_manager: MemoryManager,
        healthcare_services: HealthcareServices | None = None,
    ):
        self.registry = tool_registry
        self.manager = memory_manager
        self.healthcare_services = (
            healthcare_services or build_synthetic_services()
        )
        self.memory_extractor = MemoryExtractor()
        self.client = get_llm_client()
        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        self.registry.register(
            "provider_search",
            RegisteredTool(
                definition=provider_search_tool,
                request_model=ProviderSearchRequest,
                handler=lambda request: provider_search(
                    request,
                    self.healthcare_services.provider_directory,
                ),
            ),
        )
        self.registry.register(
            "verify_insurance",
            RegisteredTool(
                definition=insurance_verification_tool,
                request_model=InsuranceVerificationRequest,
                handler=lambda request: verify_insurance(
                    request,
                    self.healthcare_services.member_profiles,
                    self.healthcare_services.provider_directory,
                    self.healthcare_services.network_verification,
                ),
            ),
        )

        self.registry.register(
            "book_appointment",
            RegisteredTool(
                definition=appointment_booking_tool,
                request_model=AppointmentBookingRequest,
                handler=book_appointment,
            ),
        )

    def chat(self, user_input: str) -> str:
        memories = self.memory_extractor.extract(user_input)
        for key, value in memories.items():
            self.manager.save("deepak", key, value)

        user_memory = self.manager.load("deepak")
        if user_memory:
            self.messages.append(
                {
                    "role": "system",
                    "content": (
                        "Use this known user memory when relevant: "
                        f"{json.dumps(user_memory.preferences)}"
                    ),
                }
            )

        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        while True:
            assistant_message = self._call_llm()
            self.messages.append(assistant_message)

            if not assistant_message.tool_calls:
                return assistant_message.content or ""

            for tool_call in assistant_message.tool_calls:
                logger.info("Executing tool: %s", tool_call.function.name)

                result = self._execute_tool(tool_call)

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )

    def _create_chat_completion(self):

        return self.client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=self.messages,
            temperature=TEMPERATURE,
            tools=self.registry.get_tool_definitions(),
        )

    def _call_llm(self):

        response = self._create_chat_completion()

        return response.choices[0].message

    def _execute_tool(self, tool_call):
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        return self.registry.execute(
            tool_name,
            arguments,
        )
