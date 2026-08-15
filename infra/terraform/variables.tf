variable "project_id" {
  type        = string
  description = "GCP project ID. No default — set per environment (envs/<env>/*.tfvars)."
}

variable "region" {
  type        = string
  description = "Primary GCP region."
  default     = "us-central1"
}
