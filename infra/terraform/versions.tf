terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Remote state — enable once the tfstate bucket exists (Sprint 2).
  # Per-environment backend config lives in envs/<env>/backend.hcl
  # (terraform init -backend-config=envs/<env>/backend.hcl).
  # backend "gcs" {
  #   bucket = "REPLACE_ME-tfstate"
  #   prefix = "bridge"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
