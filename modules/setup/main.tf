variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central"
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_service" "serviceusage" {
  service = "serviceusage.googleapis.com"
}

resource "google_project_service" "core" {
  for_each = toset([
    "cloudapis.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "datastore.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "deploymentmanager.googleapis.com",
    "storage-api.googleapis.com",
    "storage-component.googleapis.com",
    "appengine.googleapis.com",
    "vision.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "run.googleapis.com"
  ])
  service    = each.key
  depends_on = [google_project_service.serviceusage]
}

resource "google_project_iam_member" "deployment_manager_owner" {
  project = data.google_project.current.project_id
  role    = "roles/owner"
  member  = "serviceAccount:${data.google_project.current.number}@cloudservices.gserviceaccount.com"
}

resource "google_compute_firewall" "default_allow_http" {
  name    = "default-allow-http"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  direction     = "INGRESS"
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server"]
}

resource "google_app_engine_application" "default" {
  project     = var.project_id
  location_id = var.region
  depends_on  = [google_project_service.core]
}

locals {
  audit_services = [
    "cloudfunctions.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "compute.googleapis.com",
    "storage.googleapis.com"
  ]
}

resource "google_project_iam_audit_config" "audit_logs" {
  for_each = toset(local.audit_services)

  project = var.project_id
  service = each.key

  audit_log_config {
    log_type = "ADMIN_READ"
  }

  audit_log_config {
    log_type = "DATA_READ"
  }

  audit_log_config {
    log_type = "DATA_WRITE"
  }
}

output "level_instructions" {
  value = "Project has been initialized. All core services are enabled and IAM setup is complete.\n"
}
