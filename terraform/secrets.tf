# ============================================================
# SECRET MANAGER
# ============================================================
# Your app needs OPENAI_API_KEY. Hardcoding it in environment
# variables is insecure. Secret Manager stores it encrypted
# and Cloud Run reads it at startup.
#
# How it works:
#   1. We create a "secret" (a named container)
#   2. We create a "version" (the actual key value)
#   3. Cloud Run references the secret by name
# ============================================================

# The secret container
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key-${var.environment}"

  replication {
    auto {} # Google manages replication across regions
  }

  depends_on = [google_project_service.secret_manager]
}

# The actual secret value (your OpenAI key)
resource "google_secret_manager_secret_version" "openai_api_key_value" {
  secret      = google_secret_manager_secret.openai_api_key.id
  secret_data = var.openai_api_key
}
