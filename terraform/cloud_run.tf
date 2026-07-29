# ============================================================
# CLOUD RUN SERVICES
# ============================================================
# This maps directly to your docker-compose.yml:
#
#   docker-compose.yml          →  Terraform / Cloud Run
#   ─────────────────────────      ──────────────────────
#   healthcare-api (port 8000)  →  google_cloud_run_v2_service.api
#   healthcare-ui  (port 8501)  →  google_cloud_run_v2_service.ui
#
# Cloud Run runs your Docker container serverlessly:
#   - Scales to 0 when nobody is using it (no cost!)
#   - Scales up automatically under load
#   - Gives you an HTTPS URL for free
# ============================================================


# ----------------------------------------------------------
# SERVICE ACCOUNT
# ----------------------------------------------------------
# A "service account" is an identity for your app. Instead of
# running as your personal Google account, the app gets its
# own identity with only the permissions it needs.

resource "google_service_account" "healthcare_agent" {
  account_id   = "healthcare-agent-${var.environment}"
  display_name = "Healthcare Agent (${var.environment})"
}

# Grant the service account permission to read the OpenAI secret
resource "google_secret_manager_secret_iam_member" "secret_access" {
  secret_id = google_secret_manager_secret.openai_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.healthcare_agent.email}"
}


# ----------------------------------------------------------
# CLOUD RUN: FastAPI Backend (healthcare-api)
# ----------------------------------------------------------
# This is your FastAPI service. It:
#   - Runs the uvicorn command from your Dockerfile
#   - Gets the OPENAI_API_KEY injected from Secret Manager
#   - Is NOT public (only the UI service calls it)

resource "google_cloud_run_v2_service" "api" {
  name     = "healthcare-api-${var.environment}"
  location = var.region

  # "ingress" controls who can reach this service.
  # INGRESS_TRAFFIC_ALL = public internet (we'll restrict via IAM)
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    # Run as our dedicated service account
    service_account = google_service_account.healthcare_agent.email

    # Auto-scaling: 0 instances when idle, up to 3 under load
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      # This is the image path in YOUR Artifact Registry.
      # After terraform apply, you'll push your Docker image here.
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/healthcare-agent:latest"

      # Port your FastAPI app listens on
      ports {
        container_port = 8000
      }

      # Resources per container instance
      resources {
        limits = {
          cpu    = "1"     # 1 vCPU
          memory = "512Mi" # 512 MB RAM
        }
      }

      # The startup command — same as your docker-compose.yml
      # (This overrides the Dockerfile CMD)
      args = [
        "uvicorn", "app.api.main:app",
        "--host", "0.0.0.0",
        "--port", "8000"
      ]

      # Environment variables
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      # OPENAI_API_KEY pulled securely from Secret Manager
      # (NOT hardcoded in the config!)
      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }

      # Health check — matches your docker-compose healthcheck
      startup_probe {
        http_get {
          path = "/"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }
    }
  }

  depends_on = [
    google_project_service.cloud_run,
    google_secret_manager_secret_iam_member.secret_access
  ]
}


# ----------------------------------------------------------
# CLOUD RUN: Streamlit UI (healthcare-ui)
# ----------------------------------------------------------
# This is your Streamlit chat interface. It:
#   - Runs the streamlit command from your docker-compose.yml
#   - Points BACKEND_URL at the API service's internal URL
#   - IS public (users access this)

resource "google_cloud_run_v2_service" "ui" {
  name     = "healthcare-ui-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.healthcare_agent.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/healthcare-agent:latest"

      ports {
        container_port = 8501
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      # Streamlit startup command — same as your docker-compose.yml
      args = [
        "python", "-m", "streamlit", "run",
        "app/ui/streamlit_app.py",
        "--server.address=0.0.0.0",
        "--server.port=8501",
        "--server.headless=true"
      ]

      # Point the UI at the API service's URL
      # This replaces "BACKEND_URL: http://healthcare-api:8000"
      # from your docker-compose.yml
      env {
        name  = "BACKEND_URL"
        value = google_cloud_run_v2_service.api.uri
        #       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        #       REFERENCE! Terraform automatically gets the API's
        #       URL after creating it and injects it here.
        #       This is the magic — no hardcoded URLs.
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      startup_probe {
        tcp_socket {
          port = 8501
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 3
      }
    }
  }

  depends_on = [google_project_service.cloud_run]
}


# ----------------------------------------------------------
# IAM: Make the UI publicly accessible
# ----------------------------------------------------------
# By default, Cloud Run services require authentication.
# This makes the UI accessible to anyone with the URL.
# The API stays restricted — only the UI calls it.

resource "google_cloud_run_v2_service_iam_member" "ui_public" {
  name     = google_cloud_run_v2_service.ui.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Allow the UI's service account to call the API
resource "google_cloud_run_v2_service_iam_member" "api_invoker" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.healthcare_agent.email}"
}
