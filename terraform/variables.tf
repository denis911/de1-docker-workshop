# Terraform Variables for GCP Configuration

variable "credentials" {
  description = "My Credentials"
  default     = "C:/tmp/gcp_keys/data-eng-78586-ebedbf91102f.json"
  #ex: if you have a directory where this file is called keys with your service account json file
  #saved there as my-creds.json you could use default = "./keys/my-creds.json"
}
variable "gcp_project_id" {
  description = "data-eng-78586"
  type        = string
  default = "data-eng-78586"
}

variable "project" {
  description = "Project"
  default     = "data-eng-78586"
}

variable "gcp_region" {
  description = "Google Cloud Region for resources"
  type        = string
  default     = "us-central1"
}

variable "region" {
  description = "Region"
  #Update the below to your desired region
  default     = "us-central1"
}

variable "location" {
  description = "Project Location"
  #Update the below to your desired location
  default     = "US"
}

variable "bq_dataset_name" {
  description = "BigQuery Dataset TEST"
  #Update the below to what you want your dataset to be called
  default     = "BQ_demo_dataset"
}

variable "gcs_bucket_name" {
  description = "TEST Storage Bucket Name"
  #Update the below to a unique bucket name
  default     = "data-eng-78586-bucket"
}

variable "gcs_storage_class" {
  description = "Bucket Storage Class"
  default     = "STANDARD"
}

