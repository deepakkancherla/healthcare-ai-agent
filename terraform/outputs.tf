# ============================================================
# OUTPUTS
# ============================================================
# After `terraform apply`, these values are printed.
# They give you everything you need to use your deployment.
# ============================================================

output "ui_url" {
  description = "Public URL of the Streamlit chat interface"
  value       = google_cloud_run_v2_service.ui.uri
}

output "api_url" {
  description = "URL of the FastAPI backend"
  value       = google_cloud_run_v2_service.api.uri
}

output "docker_repo_url" {
  description = "Where to push your Docker image"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}"
}

output "docker_push_commands" {
  description = "Commands to build and push your Docker image"
  value       = <<-EOT

    # 1. Configure Docker to authenticate with Artifact Registry
    gcloud auth configure-docker ${var.region}-docker.pkg.dev

    # 2. Build and tag the image (run from your project root)
    docker build -t ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/healthcare-agent:latest .

    # 3. Push to Artifact Registry
    docker push ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/healthcare-agent:latest

    # 4. Redeploy Cloud Run services to pick up new image
    gcloud run services update healthcare-api-${var.environment} --region=${var.region} --image=${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/healthcare-agent:latest
    gcloud run services update healthcare-ui-${var.environment} --region=${var.region} --image=${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/healthcare-agent:latest

  EOT
}
