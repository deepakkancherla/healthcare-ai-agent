from dataclasses import replace

import pytest

from app.application.scheduling_services import (
    DefaultSchedulingWorkflowService,
)
from app.infrastructure.synthetic.composition import (
    build_synthetic_repositories,
)
from app.infrastructure.synthetic.repositories import (
    WorkflowVersionConflict,
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


def test_workflow_repository_enforces_optimistic_version():
    repositories = build_synthetic_repositories()
    service = DefaultSchedulingWorkflowService(
        repositories.workflows
    )
    workflow = service.start_or_resume(
        "deepak",
        "conversation-deepak",
    )
    stale_update = replace(workflow, version=workflow.version + 1)

    with pytest.raises(WorkflowVersionConflict, match="version"):
        repositories.workflows.save(
            stale_update,
            expected_version=0,
        )
