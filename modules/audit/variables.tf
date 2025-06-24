variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The region for resources (e.g. us-central1)"
  type        = string
}

variable "zone" {
  description = "The zone for the Compute Engine VM (e.g. us-central1-a)"
  type        = string
}
