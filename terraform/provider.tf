# ============================================================
# PROVIDER CONFIGURATION
# ============================================================
# Tells Terraform to use Google Cloud and pins the version.
# Terraform will use your local `gcloud` credentials.
# ============================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # ----------------------------------------------------------
  # REMOTE STATE (uncomment for team use)
  # ----------------------------------------------------------
  # Stores terraform.tfstate in a GCS bucket so your team
  # shares one source of truth instead of local files.
  #
  # backend "gcs" {
  #   bucket = "your-project-tf-state"
  #   prefix = "healthcare-agent"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
