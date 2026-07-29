# ============================================================
# ARTIFACT REGISTRY
# ============================================================
# This is GCP's Docker registry — like Docker Hub but private
# and inside your project. Your healthcare-agent image gets
# pushed here, and Cloud Run pulls from here.
#
# Your docker-compose already builds the image. We just need
# a place to store it in GCP.
# ============================================================

resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "healthcare-agent-${var.environment}"
  description   = "Docker images for the Healthcare AI Agent"
  format        = "DOCKER"

  # Clean up untagged images after 14 days to save storage costs
  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "1209600s" # 14 days in seconds
    }
  }

  depends_on = [google_project_service.artifact_registry]
}
