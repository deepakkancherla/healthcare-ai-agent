# Deploying Healthcare AI Agent to GCP with Terraform

This Terraform config deploys your Healthcare AI Agent
(FastAPI + Streamlit) to Google Cloud Run.

## What Terraform creates

| Resource                | Purpose                                       |
|-------------------------|-----------------------------------------------|
| 3 API enablements       | Cloud Run, Artifact Registry, Secret Manager  |
| Artifact Registry repo  | Stores your Docker image                      |
| Secret Manager secret   | Holds OPENAI_API_KEY encrypted                |
| Service Account         | Identity for your app (least-privilege)        |
| Cloud Run: API service  | Your FastAPI backend (port 8000)              |
| Cloud Run: UI service   | Your Streamlit frontend (port 8501)           |
| 2 IAM bindings          | UI is public; API restricted to UI only       |

Total: ~10 resources. Cost when idle: effectively $0 (Cloud Run
scales to zero).

---

## Prerequisites

### 1. Install tools
- Terraform: https://developer.hashicorp.com/terraform/install
- gcloud CLI: https://cloud.google.com/sdk/docs/install
- Docker: https://docs.docker.com/get-docker/

### 2. Authenticate with GCP
```bash
gcloud auth login
gcloud config set project YOUR-PROJECT-ID
gcloud auth application-default login
```

### 3. Fill in your values
Edit `terraform.tfvars`:
```hcl
project_id     = "your-actual-project-id"
region         = "us-central1"
environment    = "dev"
openai_api_key = "sk-your-actual-openai-key"
```

---

## Deploy (4 commands)

### Step 1: Initialize Terraform
```bash
cd terraform-healthcare-agent/
terraform init
```
Downloads the Google Cloud provider plugin.

### Step 2: Preview what will be created
```bash
terraform plan
```
Shows you exactly what Terraform will create. Read this carefully.
You should see ~10 resources to add.

### Step 3: Create everything
```bash
terraform apply
```
Type `yes` when prompted. Takes 2-3 minutes.
Terraform prints your URLs when done:
```
ui_url  = "https://healthcare-ui-dev-xxxxx.a.run.app"
api_url = "https://healthcare-api-dev-xxxxx.a.run.app"
```

### Step 4: Push your Docker image
The Cloud Run services need your Docker image. After `terraform apply`:
```bash
# Configure Docker to talk to your GCP registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build the image (from your healthcare-ai-agent repo root)
docker build -t us-central1-docker.pkg.dev/YOUR-PROJECT/healthcare-agent-dev/healthcare-agent:latest .

# Push it
docker push us-central1-docker.pkg.dev/YOUR-PROJECT/healthcare-agent-dev/healthcare-agent:latest

# Redeploy services to use the new image
gcloud run services update healthcare-api-dev --region=us-central1 \
  --image=us-central1-docker.pkg.dev/YOUR-PROJECT/healthcare-agent-dev/healthcare-agent:latest

gcloud run services update healthcare-ui-dev --region=us-central1 \
  --image=us-central1-docker.pkg.dev/YOUR-PROJECT/healthcare-agent-dev/healthcare-agent:latest
```

Replace `YOUR-PROJECT` with your GCP project ID. Terraform also
prints these exact commands in the `docker_push_commands` output.

### Step 5: Open your app
Visit the `ui_url` printed by Terraform. Your Streamlit chat
interface is live on the internet.

---

## Understanding the files

```
terraform-healthcare-agent/
├── provider.tf       # "Use Google Cloud, version 5.x"
├── variables.tf      # "These inputs are needed"
├── terraform.tfvars  # "Here are my actual values" (git-ignored)
├── apis.tf           # "Enable these GCP APIs"
├── registry.tf       # "Create a Docker image registry"
├── secrets.tf        # "Store OPENAI_API_KEY securely"
├── cloud_run.tf      # "Deploy the two Cloud Run services"
├── outputs.tf        # "Print URLs and commands when done"
├── .gitignore        # Excludes state files and secrets
└── DEPLOY.md         # This file
```

---

## How this maps to your docker-compose.yml

| docker-compose.yml               | Terraform equivalent                          |
|-----------------------------------|-----------------------------------------------|
| `build: context: .`              | `google_artifact_registry_repository` + push  |
| `healthcare-api` service          | `google_cloud_run_v2_service.api`             |
| `healthcare-ui` service           | `google_cloud_run_v2_service.ui`              |
| `OPENAI_API_KEY: ${OPENAI_API_KEY}` | `google_secret_manager_secret` → injected  |
| `BACKEND_URL: http://healthcare-api:8000` | Auto-resolved via Terraform reference |
| `depends_on: healthcare-api`     | Terraform reference creates implicit dependency |
| `ports: "8000:8000"`             | Cloud Run auto-assigns HTTPS URL              |
| `healthcheck`                    | `startup_probe` in Cloud Run                  |

---

## Day-to-day operations

### Update your code
After changing your Python code:
```bash
docker build -t us-central1-docker.pkg.dev/YOUR-PROJECT/healthcare-agent-dev/healthcare-agent:latest .
docker push us-central1-docker.pkg.dev/YOUR-PROJECT/healthcare-agent-dev/healthcare-agent:latest
gcloud run services update healthcare-api-dev --region=us-central1 --image=...
gcloud run services update healthcare-ui-dev  --region=us-central1 --image=...
```

### Check logs
```bash
gcloud run services logs read healthcare-api-dev --region=us-central1
gcloud run services logs read healthcare-ui-dev  --region=us-central1
```

### Tear down (stop all charges)
```bash
terraform destroy
```
Type `yes`. Removes everything Terraform created.

---

## Key Terraform concepts you just used

| Concept        | Where you saw it                               |
|----------------|-------------------------------------------------|
| **Reference**  | `google_cloud_run_v2_service.api.uri` used as   |
|                | the UI's BACKEND_URL — auto-resolved.           |
| **Sensitive**  | `openai_api_key` marked sensitive — never logged |
| **depends_on** | Cloud Run waits for API enablement               |
| **IAM**        | UI is public, API restricted to service account  |
| **Outputs**    | URLs printed after apply for immediate use       |
