resource "random_id" "nonce" {
  byte_length = 4
}

# ───── GCS Bucket ─────
resource "google_storage_bucket" "a5_bucket" {
  name                        = "a5-bucket-${random_id.nonce.hex}"
  location                    = "US"
  force_destroy               = true
  uniform_bucket_level_access = true
  project                     = var.project_id
}

resource "local_file" "bucket_name_file" {
  content  = google_storage_bucket.a5_bucket.name
  filename = "${path.module}/generated/bucket_name.txt"
}

# ───── Service Accounts ─────
resource "google_service_account" "func_sa" {
  account_id   = "a5-func-${random_id.nonce.hex}-sa"
  display_name = "A5 Cloud Function SA"
}

resource "google_service_account" "a5_access" {
  account_id   = "a5-access"
  display_name = "Compromised Developer SA"
}

# ───── Custom Roles ─────
resource "google_project_iam_custom_role" "func_role" {
  role_id     = "a5_fcuntion_${random_id.nonce.hex}"
  title       = "Function SA IAM Escalation Role"
  project     = var.project_id
  permissions = [
    "iam.roles.get",
    "iam.roles.list",
    "iam.roles.update",
    "resourcemanager.projects.get",
    "resourcemanager.projects.getIamPolicy"
  ]
}

resource "google_project_iam_custom_role" "access_role" {
  role_id     = "a5_access_${random_id.nonce.hex}"
  title       = "Compromised SA Cloud Functions Role"
  project     = var.project_id
  permissions = [
    "cloudfunctions.functions.get",
    "cloudfunctions.functions.list",
    "cloudfunctions.locations.list",
    "cloudfunctions.functions.sourceCodeSet",
    "cloudfunctions.functions.update",
    "cloudfunctions.operations.get",
    "serviceusage.services.get"
  ]
}

# ───── IAM Bindings ─────
resource "google_project_iam_member" "bind_access_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.access_role.name
  member  = "serviceAccount:${google_service_account.a5_access.email}"
}

resource "google_project_iam_member" "bind_func_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.func_role.name
  member  = "serviceAccount:${google_service_account.func_sa.email}"
}

resource "google_project_iam_member" "allow_act_as_func_sa" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.a5_access.email}"
}

# ───── Function Bucket + Zip ─────
resource "google_storage_bucket" "function_bucket" {
  name          = "a5-func-code-${random_id.nonce.hex}"
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

# ───── Cloud Function ─────
resource "google_cloudfunctions_function" "a5_func" {
  name                  = "a5-func-${random_id.nonce.hex}"
  project               = var.project_id
  region                = var.region
  runtime               = "python312"
  entry_point           = "main"
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.function_zip.name
  trigger_http          = true
  service_account_email = google_service_account.func_sa.email
}

resource "google_cloudfunctions_function_iam_member" "invoker_binding" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.a5_func.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.a5_access.email}"
}

# ───── Provision Step ─────
resource "null_resource" "provision" {
  provisioner "local-exec" {
    command = "python3 ${path.module}/a5power_provision.py"
  }

  triggers = {
    always_run = timestamp()
  }

  depends_on = [
    google_storage_bucket.a5_bucket,
    google_service_account.a5_access
  ]
}

resource "null_resource" "track_active_level" {
  provisioner "local-exec" {
    command = "mkdir -p config && echo a5power > config/a5power_active.txt"
  }

  triggers = {
    always_run = timestamp()
  }
}

# ─────────────  CLEANUP ────────────────

resource "null_resource" "cleanup_function_bucket" {
  depends_on = [
    google_cloudfunctions_function.a5_func,
    google_storage_bucket_object.function_zip,
    null_resource.provision
  ]

  provisioner "local-exec" {
    command = "gsutil rm -r gs://${google_storage_bucket.function_bucket.name} || true"
  }

  triggers = {
    always_run = timestamp()
  }
}

