# ============================================================
# VARIABLES
# ============================================================
# All the inputs this Terraform config needs.
# Set actual values in terraform.tfvars (not checked into git).
# ============================================================

variable "project_id" {
  description = "Your GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "openai_api_key" {
  description = "Your OpenAI API key (stored securely in Secret Manager)"
  type        = string
  sensitive   = true # Terraform will never print this in logs
}
