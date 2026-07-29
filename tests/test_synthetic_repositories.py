from app.infrastructure.synthetic.composition import (
    build_synthetic_repositories,
)


def test_repositories_return_typed_synthetic_records():
    repositories = build_synthetic_repositories()

    member = repositories.members.get("deepak")
    provider = repositories.providers.get(
        "provider-sarah-johnson"
    )
    slot = repositories.slots.get(
        "slot-sarah-plano-20260804-1000"
    )

    assert member is not None
    assert member.display_name == "Deepak"
    assert provider is not None
    assert provider.display_name == "Dr. Sarah Johnson"
    assert slot is not None
    assert slot.status == "available"
    assert repositories.appointments.list_all() == []


def test_repository_collections_are_returned_as_copies():
    repositories = build_synthetic_repositories()

    first_result = repositories.providers.list_all()
    first_result.clear()

    assert repositories.providers.list_all()
