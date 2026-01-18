# Terraform Provider Configuration for Google Cloud Platform
# https://registry.terraform.io/providers/hashicorp/google/latest/docs

provider "google" {
  # Credentials will be picked up from GOOGLE_APPLICATION_CREDENTIALS env var
  # Or can be specified directly via credentials parameter (not recommended for version control)
  project = var.gcp_project_id
  region  = var.gcp_region
}

# For BigQuery and other GCP services
provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}
