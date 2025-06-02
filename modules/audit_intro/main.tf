resource "random_id" "nonce" {
  byte_length = 4
}

resource "google_storage_bucket" "bucket1" {
  name                        = "audit-intro-bucket1-${random_id.nonce.hex}"
  location                    = "US"
  project                     = var.project_id
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "bucket2" {
  name                        = "audit-intro-bucket2-${random_id.nonce.hex}"
  location                    = "US"
  project                     = var.project_id
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "local_file" "bucket1_name_file" {
  content  = google_storage_bucket.bucket1.name
  filename = "${path.module}/generated/bucket1.txt"
}

resource "local_file" "bucket2_name_file" {
  content  = google_storage_bucket.bucket2.name
  filename = "${path.module}/generated/bucket2.txt"
}

resource "google_service_account" "npc" {
  account_id   = "audit-npc"
  display_name = "Audit NPC Service Account"
}

resource "google_project_iam_member" "npc_project_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.npc.email}"
}

resource "google_storage_bucket_iam_member" "npc_bucket1_get" {
  bucket = google_storage_bucket.bucket1.name
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:${google_service_account.npc.email}"
}

resource "null_resource" "audit_intro_provision" {
  depends_on = [
    local_file.bucket1_name_file,
    local_file.bucket2_name_file,
    google_service_account.npc,
    google_storage_bucket_iam_member.npc_bucket1_get
  ]

  provisioner "local-exec" {
    command = "python3 ${path.module}/audit_intro_provision.py"
  }

  triggers = {
    always_run = timestamp()
  }
}

resource "local_file" "instructions" {
  content  = "The access key in the start directory has been leaked. Find the bucket accessed through the leaked key and the service account bound to it."
  filename = "${path.module}/../../instructions/audit_intro.txt"
}

resource "null_resource" "track_active_level" {
  provisioner "local-exec" {
    command = "mkdir -p config && echo audit_intro > config/audit_intro_active.txt"
  }

  triggers = {
    always_run = timestamp()
  }
}
