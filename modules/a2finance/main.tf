# Random suffix for resource uniqueness
resource "random_id" "nonce" {
  byte_length = 4
}

# Bucket for leaked Git repo
resource "google_storage_bucket" "leak_bucket" {
  name                        = "a2-bucket-${random_id.nonce.hex}"
  location                    = "US"
  project                     = var.project_id
  force_destroy               = true
  uniform_bucket_level_access = true
}

# Service account for the VM
resource "google_service_account" "logging_instance_sa" {
  account_id   = "a2-logging-instance-sa"
  display_name = "Service account for a2-logging-instance"
}

# Grant logging roles to the logging_instance_sa
resource "google_project_iam_member" "logging_instance_logwriter" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.logging_instance_sa.email}"
}

resource "google_project_iam_member" "logging_instance_logviewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.logging_instance_sa.email}"
}

# VM with fluentd agent and attached service account
resource "google_compute_instance" "logging_instance" {
  name         = "a2-logging-instance"
  machine_type = "e2-micro"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  metadata = {
    startup-script = file("${path.module}/startup.sh")
  }

  network_interface { 
    network       = "default"
    access_config {}
  }

  tags = ["http-server"]

  service_account {
    email  = google_service_account.logging_instance_sa.email
    scopes = ["cloud-platform"]
  }
}

# Compromised service account to leak
resource "google_service_account" "a2finance_sa" {
  account_id   = "a2-access"
  display_name = "Compromised service account for a2finance"
}

# Custom role for the compromised account
resource "google_project_iam_custom_role" "a2_custom_viewer" {
  role_id     = "a2CustomViewer"
  title       = "A2Finance Custom Role"
  description = "Mimics original DM YAML permissions"
  project     = var.project_id

  permissions = [
    "compute.instances.get",
    "compute.instances.list",
    "compute.zones.list",
    "compute.zones.get",
    "storage.buckets.list",
    "storage.objects.list",
    "storage.objects.get"
  ]
}

# Bind custom role to compromised SA
resource "google_project_iam_member" "assign_custom" {
  project = var.project_id
  role    = google_project_iam_custom_role.a2_custom_viewer.name
  member  = "serviceAccount:${google_service_account.a2finance_sa.email}"
}

# Generate and write the compromised SA key to disk
resource "google_service_account_key" "a2finance_key" {
  service_account_id = google_service_account.a2finance_sa.name
}

resource "local_file" "service_account_key_file" {
  content  = base64decode(google_service_account_key.a2finance_key.private_key)
  filename = "${path.root}/start/a2-access.json"
}

resource "local_file" "bucket_name_file" {
  content  = google_storage_bucket.leak_bucket.name
  filename = "${path.root}/start/a2_bucket_name.txt"
}

# Track active level
resource "null_resource" "track_active_level" {
  provisioner "local-exec" {
    command = "mkdir -p config && echo a2finance > config/a2finance_active.txt"
  }

  triggers = {
    always_run = timestamp()
  }
}