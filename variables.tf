# ─────────────────────────────────────────────────────────────
# project_id: GCP project to deploy Thunder CTF resources into
# This must be set by the user when running Terraform
# ─────────────────────────────────────────────────────────────
variable "project_id" {
  type        = string
  description = "The GCP project ID to deploy Thunder CTF into"
}

# ─────────────────────────────────────────────────────────────
# region: Default deployment region for regional services
# Used for App Engine, Cloud Functions, etc.
# Default is set to 'us-central'
# ─────────────────────────────────────────────────────────────
variable "region" {
  type        = string
  default     = "us-central1"
  description = "Region for App Engine and other regional resources"
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

variable "ssh_username" {
  description = "Username for SSH login"
  type        = string
  default     = "clouduser"
}

