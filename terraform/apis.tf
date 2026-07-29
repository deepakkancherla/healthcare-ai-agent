# ============================================================
# ENABLE GCP APIs
# ============================================================
# GCP keeps APIs disabled by default. Before Terraform can
# create Cloud Run services or push Docker images, we need
# to flip these switches on.
#
# This replaces clicking "Enable API" in the GCP Console.
# ============================================================

resource "google_project_service" "cloud_run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secret_manager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}
