from app.memory.memory_extractor import MemoryExtractor
from app.memory.memory_manager import MemoryManager


def test_memory_extractor_finds_name_case_insensitively():
    extractor = MemoryExtractor()

    assert extractor.extract("MY NAME IS Deepak") == {"name": "Deepak"}


def test_memory_extractor_returns_empty_memory_for_unrelated_message():
    extractor = MemoryExtractor()

    assert extractor.extract("Find a dermatologist near Plano") == {}


def test_memory_manager_returns_none_for_unknown_user():
    manager = MemoryManager()

    assert manager.load("unknown-user") is None


def test_memory_manager_saves_and_updates_preferences():
    manager = MemoryManager()

    manager.save("deepak", "preferred_city", "Plano")
    manager.save("deepak", "preferred_city", "Dallas")
    manager.save("deepak", "languages", ["English", "Hindi"])

    memory = manager.load("deepak")

    assert memory is not None
    assert memory.user_id == "deepak"
    assert memory.preferences == {
        "preferred_city": "Dallas",
        "languages": ["English", "Hindi"],
    }


def test_memory_manager_isolates_users():
    manager = MemoryManager()

    manager.save("member-1", "name", "Deepak")
    manager.save("member-2", "name", "Asha")

    assert manager.load("member-1").preferences["name"] == "Deepak"
    assert manager.load("member-2").preferences["name"] == "Asha"
