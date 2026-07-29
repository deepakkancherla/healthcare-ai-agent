import re


class MemoryExtractor:
    def extract(self, message: str) -> dict[str, str]:
        memory = {}

        if match := re.search(r"my name is (.+)", message, re.IGNORECASE):
            memory["name"] = match.group(1).strip()

        return memory
