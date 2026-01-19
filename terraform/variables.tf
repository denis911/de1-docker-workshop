# Terraform Variables for GCP Configuration

variable "gcp_project_id" {
  description = "data-eng-78586"
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud Region for resources"
  type        = string
  default     = "us-central1"
}
