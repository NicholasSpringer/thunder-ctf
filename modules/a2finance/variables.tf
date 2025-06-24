variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "Region to deploy resources"
}

variable "zone" {
  type        = string
  description = "Zone for Compute Engine"
}

variable "ssh_username" {
  type        = string
  description = "SSH username for VM access"
}
