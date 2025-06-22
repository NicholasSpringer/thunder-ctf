
resource "random_id" "nonce" {
  byte_length = 4
}


# ──────────────── BUCKETS ────────────────
resource "google_storage_bucket" "a4_bucket" {
  name                        = "a4-bucket-${random_id.nonce.hex}"
  location                    = "US"
  project                     = var.project_id
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "local_file" "bucket_name_file" {
  content  = google_storage_bucket.a4_bucket.name
  filename = "${path.module}/generated/bucket_name.txt"
}

resource "google_storage_bucket" "function_bucket" {
  name          = "a4-func-code-${random_id.nonce.hex}"
  location      = "US"
  project       = var.project_id
  force_destroy = true
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "function.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = "${path.module}/function.zip"
  depends_on = [null_resource.provision]
}

# ──────────────── VM ────────────────
resource "google_compute_instance" "a4_instance" {
  name         = "a4-instance"
  machine_type = "e2-micro"
  zone         = "us-west1-b"
  project      = var.project_id

  boot_disk {
    initialize_params {
      image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
    }
  }

  network_interface {
    network       = "default"
    access_config {}
  }


  service_account {
    email  = google_service_account.instance_sa.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    startup-script = file("${path.module}/startup.sh")
    LEVEL_SECRET   = var.level_secret
  }

  tags = ["http-server"]
}

# ──────────────── SERVICE ACCOUNTS ────────────────
resource "google_service_account" "instance_sa" {
  account_id   = "a4-instance-sa"
  display_name = "VM service account for a4error"
}

resource "google_service_account" "a4_access" {
  account_id   = "a4-access"
  display_name = "Compromised service account"
}

# ──────────────── IAM ────────────────
resource "google_project_iam_custom_role" "a4_custom_role" {
  role_id     = "a4CustomRole_${random_id.nonce.hex}"
  title       = "a4error SA Custom Role"
  project     = var.project_id
  permissions = [
    "cloudfunctions.functions.list",
    "cloudfunctions.locations.list",
    "compute.instances.list",
    "compute.instances.get",
    "compute.zones.list"
  ]
}

resource "google_project_iam_member" "a4_custom_role_binding" {
  project = var.project_id
  role    = google_project_iam_custom_role.a4_custom_role.name
  member  = "serviceAccount:${google_service_account.a4_access.email}"
}

resource "google_project_iam_member" "a4_logging_viewer_binding" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.a4_access.email}"
}

resource "google_project_iam_custom_role" "a4_can_set_metadata" {
  role_id     = "a4SetMetadata"
  title       = "A4 Set Metadata Only"
  description = "Allows setting VM metadata"
  project     = var.project_id

  permissions = [
    "compute.instances.setMetadata"
  ]
}

resource "google_project_iam_member" "bind_a4_set_metadata" {
  project = var.project_id
  role    = google_project_iam_custom_role.a4_can_set_metadata.name
  member  = "serviceAccount:${google_service_account.a4_access.email}"
}

resource "google_project_iam_member" "a4_sauser_on_vm_sa" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.a4_access.email}"
}

# ──────────────── CLOUD FUNCTION ────────────────
resource "google_cloudfunctions_function" "a4_func" {
  name        = "a4-func-${random_id.nonce.hex}"
  project     = var.project_id
  region      = var.region
  runtime     = "python312"
  entry_point = "main"

  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.function_zip.name
  trigger_http          = true
  service_account_email = google_service_account.a4_access.email
}

resource "google_cloudfunctions_function_iam_member" "a4_func_invoker" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.a4_func.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.a4_access.email}"
}

# ──────────────── PROVISION + CLEANUP ────────────────
resource "null_resource" "provision" {
  depends_on = [
    google_storage_bucket.a4_bucket,
    google_compute_instance.a4_instance,
    google_service_account.a4_access,
    local_file.bucket_name_file
  ]

  provisioner "local-exec" {
    command = "python3 ${path.module}/a4error_provision.py"
  }

  triggers = {
    always_run = timestamp()
  }
}

resource "null_resource" "track_active_level" {
  provisioner "local-exec" {
    command = "mkdir -p config && echo a4error > config/a4error_active.txt"
  }

  triggers = {
    always_run = timestamp()
  }
}

resource "null_resource" "cleanup" {
  depends_on = [null_resource.provision]

  provisioner "local-exec" {
    command = <<EOT
      echo "[INFO] Cleaning up..."
      rm -rf ${path.module}/function
      rm -rf ${path.module}/generated
      rm -f ${path.module}/function.zip
      echo "[INFO] Cleanup complete."
    EOT
  }

  triggers = {
    always_run = timestamp()
  }
}