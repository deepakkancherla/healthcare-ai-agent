from .models import UserMemory


class MemoryManager:
    def __init__(self):
        self.user_memories: dict[str, UserMemory] = {}

    def save(
        self,
        user_id: str,
        key: str,
        value: str | list[str],
    ) -> None:

        # Create a new memory for first-time users
        if user_id not in self.user_memories:
            self.user_memories[user_id] = UserMemory(user_id=user_id)

        # Update (or add) a single preference
        self.user_memories[user_id].preferences[key] = value

    def load(self, user_id: str) -> UserMemory | None:
        return self.user_memories.get(user_id)
