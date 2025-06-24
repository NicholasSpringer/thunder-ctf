
resource "random_id" "nonce" {
  byte_length = 4
}

resource "random_password" "db_password" {
  length  = 64
  special = false
}

# === Service Accounts ===
resource "google_service_account" "dev" {
  account_id   = "dev-account"
  display_name = "Dev Account"
}

resource "google_service_account" "compute_admin" {
  account_id   = "compute-admin"
  display_name = "Compute Admin"
}

resource "google_service_account" "log_viewer" {
  account_id   = "log-viewer"
  display_name = "Log Viewer"
}

resource "google_service_account" "vm_sa" {
  account_id   = "audit-vm-sa"
  display_name = "Audit VM SA"
}

# === IAM Roles ===
resource "google_project_iam_member" "dev_editor" {
  project = var.project_id
  role    = "roles/editor"
  member  = "serviceAccount:${google_service_account.dev.email}"
}

resource "google_project_iam_member" "compute_admin_editor" {
  project = var.project_id
  role    = "roles/editor"
  member  = "serviceAccount:${google_service_account.compute_admin.email}"
}

resource "google_project_iam_member" "log_viewer_admin" {
  project = var.project_id
  role    = "roles/logging.admin"
  member  = "serviceAccount:${google_service_account.log_viewer.email}"
}

resource "google_project_iam_member" "vm_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.vm_sa.email}"
}

resource "google_project_iam_member" "vm_cloudsql_viewer" {
  project = var.project_id
  role    = "roles/cloudsql.viewer"
  member  = "serviceAccount:${google_service_account.vm_sa.email}"
}

resource "google_project_iam_member" "vm_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.vm_sa.email}"
}

resource "google_project_iam_member" "vm_secret_viewer" {
  project = var.project_id
  role    = "roles/secretmanager.viewer"
  member  = "serviceAccount:${google_service_account.vm_sa.email}"
}


resource "google_project_iam_member" "cloudfunction_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloudfunction_sa.email}"
}


# === Cloud SQL ===
resource "google_sql_database_instance" "db_instance" {
  name             = "audit-db-${random_id.nonce.hex}"
  database_version = "POSTGRES_13"
  region           = var.region

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "all"
        value = "0.0.0.0/0"
      }
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "db" {
  name     = "audit"
  instance = google_sql_database_instance.db_instance.name
}

resource "google_sql_user" "api_engine" {
  name     = "api-engine"
  instance = google_sql_database_instance.db_instance.name
  password = random_password.db_password.result
}

# === Secret Manager ===
resource "google_secret_manager_secret" "db_pass_secret" {
  secret_id = "defender_db_password"

  replication {
    user_managed {
      replicas {
        location = "us-central1"
      }
    }
  }
}

resource "google_secret_manager_secret_version" "db_pass_secret_version" {
  secret      = google_secret_manager_secret.db_pass_secret.id
  secret_data = random_password.db_password.result
}


resource "google_storage_bucket_object" "function_zip" {
  name   = "function.zip"
  bucket = google_storage_bucket.vm_bucket.name
  source = "${path.module}/function.zip"
}

resource "google_cloudfunctions_function" "rm_user" {
  name        = "rm-user-${random_id.nonce.hex}"
  description = "Cloud Function to remove a user"
  runtime     = "python311"
  region      = var.region
  entry_point = "main"  # your function name inside main.py

  available_memory_mb   = 512
  source_archive_bucket = google_storage_bucket.vm_bucket.name
  source_archive_object = google_storage_bucket_object.function_zip.name
  trigger_http          = true

  service_account_email = google_service_account.cloudfunction_sa.email

  environment_variables = {
    REGION      = var.region
    ZONE        = var.zone
    NONCE       = random_id.nonce.hex
    DB_PASSWORD = random_password.db_password.result
    PROJECT_ID  = var.project_id
  }
}

resource "google_cloudfunctions_function_iam_member" "allow_all_users" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.rm_user.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}


resource "google_service_account" "cloudfunction_sa" {
  account_id   = "rm-user-fn-sa"
  display_name = "Cloud Function Service Account"
}

resource "google_project_iam_member" "cloudfunction_sa_compute_viewer" {
  project = var.project_id
  role    = "roles/compute.viewer"
  member  = "serviceAccount:${google_service_account.cloudfunction_sa.email}"
}

# === Bucket ===
resource "google_storage_bucket" "vm_bucket" {
  name          = "vm-image-bucket-${random_id.nonce.hex}"
  location      = var.region
  force_destroy = true
}

# === VM ===
resource "google_compute_instance" "vm" {
  name         = "api-engine"
  machine_type = "e2-small"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    "gce-container-declaration" = <<EOF
spec:
  containers:
    - name: api
      image: docker.io/aujxn/defender-audit:latest
      stdin: false
      tty: false
  restartPolicy: Always
EOF
  }

  service_account {
    email  = google_service_account.vm_sa.email
    scopes = ["cloud-platform"]
  }
}

# === Provisioner ===
resource "null_resource" "audit_provision" {
  depends_on = [
    google_sql_user.api_engine,
    google_compute_instance.vm,
    google_storage_bucket.vm_bucket
  ]

  provisioner "local-exec" {
    command = "python3 ${path.module}/audit.py"
    environment = {
      NONCE        = random_id.nonce.hex
      REGION       = var.region
      ZONE         = var.zone
      DB_PASSWORD  = random_password.db_password.result
      GOOGLE_CLOUD_PROJECT = var.project_id
    }
  }

  triggers = {
    always_run = timestamp()
  }
}

# === Track Active Level ===
resource "null_resource" "track_active_level" {
  provisioner "local-exec" {
    command = "mkdir -p config && echo audit > config/audit_active.txt"
  }

  triggers = {
    always_run = timestamp()
  }
}
