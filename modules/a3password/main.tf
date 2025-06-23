resource "null_resource" "a3_provision" {
  provisioner "local-exec" {
    command = "python3 ${path.module}/a3password_provision.py"
  }

  triggers = {
    always_run = timestamp()
  }
}

resource "random_id" "nonce" {
  byte_length = 4
}

# Bucket to hold the secret
resource "google_storage_bucket" "secret_bucket" {
  name                        = "a3-bucket-${random_id.nonce.hex}"
  location                    = "US"
  project                     = var.project_id
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "secret_file" {
  name   = "secret.txt"
  bucket = google_storage_bucket.secret_bucket.name
  content = var.level_secret
}

# Compromised service account
resource "google_service_account" "a3_sa" {
  account_id   = "a3-access"
  display_name = "Compromised service account for a3password"
}

resource "google_project_iam_custom_role" "a3_custom_role" {
  role_id     = "a3CustomRole${random_id.nonce.hex}"
  title       = "A3Password Custom Role"
  description = "Custom role for a3 compromised account"
  project     = var.project_id

  permissions = [
    "cloudfunctions.functions.get",
    "cloudfunctions.functions.list",
    "cloudfunctions.locations.list",
    "cloudfunctions.functions.sourceCodeGet"
  ]
}

resource "google_project_iam_member" "bind_custom_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.a3_custom_role.name
  member  = "serviceAccount:${google_service_account.a3_sa.email}"
}

resource "google_service_account_key" "a3_key" {
  service_account_id = google_service_account.a3_sa.name
}

resource "local_file" "service_account_key_file" {
  content  = base64decode(google_service_account_key.a3_key.private_key)
  filename = "${path.root}/start/a3-access.json"
}

resource "local_file" "bucket_name_file" {
  content  = google_storage_bucket.secret_bucket.name
  filename = "${path.root}/start/a3_bucket_name.txt"
}

# Function bucket & deployment
resource "google_storage_bucket" "function_bucket" {
  name          = "a3-func-code-${random_id.nonce.hex}"
  location      = "US"
  project       = var.project_id
  force_destroy = true
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "function.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = "${path.module}/function.zip"
  depends_on = [null_resource.a3_provision]
}

data "local_file" "xor_password" {
  filename   = "${path.module}/generated/xor_password.txt"
  depends_on = [null_resource.a3_provision]
}

resource "google_cloudfunctions_function" "a3_func" {
  name        = "a3-func-${random_id.nonce.hex}"
  project     = var.project_id
  region      = var.region
  runtime     = "python312"
  entry_point = "main"

  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.function_zip.name
  trigger_http          = true
  service_account_email = google_service_account.a3_sa.email

  environment_variables = {
    XOR_PASSWORD  = data.local_file.xor_password.content
    SECRET_BUCKET = google_storage_bucket.secret_bucket.name
  }
}

resource "google_cloudfunctions_function_iam_member" "invoker" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.a3_func.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.a3_sa.email}"
}

# Mark this as the active level
resource "null_resource" "track_active_level" {
  provisioner "local-exec" {
    command = "mkdir -p config && echo a3password > config/a3password_active.txt"
  }

  triggers = {
    always_run = timestamp()
  }
}

resource "null_resource" "cleanup" {
  depends_on = [google_cloudfunctions_function.a3_func]

  provisioner "local-exec" {
    command = <<EOT
      rm -rf ${path.module}/function
      rm -rf ${path.module}/generated
      rm -f ${path.module}/function.zip
    EOT
  }

  triggers = {
    always_run = timestamp()
  }
}