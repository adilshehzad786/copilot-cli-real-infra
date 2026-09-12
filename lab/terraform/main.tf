# Local review fixture only. No real project or deployed resource is attached.
# The bucket below is deliberately unhardened: that is the exercise.

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "me-central2"
}

variable "project_id" {
  description = "Synthetic project identifier; this fixture must not be deployed."
  type        = string
}

resource "google_storage_bucket" "reports" {
  name     = "${var.project_id}-reports"
  location = "ME-CENTRAL2"

  force_destroy = true
}

resource "google_storage_bucket_iam_member" "public" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}
