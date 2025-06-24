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

variable "level_secret" {
  type        = string
  description = "Secret to store in the bucket"
  default     = "example-level-secret"
}
