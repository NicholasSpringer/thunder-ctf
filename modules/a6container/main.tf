resource "random_id" "nonce" {
  byte_length = 4
}

# ───── GCS Bucket ─────
resource "google_storage_bucket" "a6_bucket" {
  name                        = "a6-bucket-${random_id.nonce.hex}"
  location                    = "US"
  force_destroy               = true
  uniform_bucket_level_access = true
  project                     = var.project_id
}

resource "local_file" "bucket_name_file" {
  content  = google_storage_bucket.a6_bucket.name
  filename = "${path.module}/generated/bucket_name.txt"
}

# ───── Service Account ─────
resource "google_service_account" "a6_access" {
  account_id   = "a6-access"
  display_name = "Compromised Developer SA"
}

# ───── IAM Bindings ─────
resource "google_project_iam_custom_role" "a6_custom_role" {
  role_id     = "a6CustomRole_${random_id.nonce.hex}"
  title       = "A6 Container Role"
  project     = var.project_id
  permissions = [
    "compute.instances.get",
    "compute.instances.list",
    "compute.instances.setMetadata",
    "compute.zones.list",
    "storage.objects.get",
    "storage.objects.list",
    "storage.buckets.get",
    "storage.buckets.list"
  ]
}

resource "google_project_iam_member" "a6_role_binding" {
  project = var.project_id
  role    = google_project_iam_custom_role.a6_custom_role.name
  member  = "serviceAccount:${google_service_account.a6_access.email}"
}

resource "google_project_iam_member" "a6_logging_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.a6_access.email}"
}

# ───── Container Declaration ─────
resource "local_file" "container_declaration" {
  filename = "${path.module}/gce-container-declaration.yaml"
  content = <<EOT
apiVersion: v1
kind: Pod
metadata:
  name: a6
spec:
  containers:
    - name: a6
      image: docker.io/wuchangfeng/thunder-ctf-a6:latest
      imagePullPolicy: Always
      ports:
        - containerPort: 80
          hostPort: 80
EOT
}

# ───── VM ─────
resource "google_compute_instance" "container_vm" {
  name         = "a6-container-vm"
  zone         = "us-west1-b"
  machine_type = "e2-medium"
  project      = var.project_id

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
    }
  }

  metadata = {
    gce-container-declaration = local_file.container_declaration.content
  }

  network_interface {
    network       = "default"
    access_config {}
  }

  tags = ["http-server"]

  service_account {
    email  = google_service_account.a6_access.email
    scopes = ["cloud-platform"]
  }
}

# ───── Provisioning ─────
resource "null_resource" "provision" {
  provisioner "local-exec" {
    command = "python3 ${path.module}/a6container_provision.py"
  }

  triggers = {
    always_run = timestamp()
  }

  depends_on = [
    google_storage_bucket.a6_bucket,
    google_compute_instance.container_vm,
    google_service_account.a6_access
  ]
}

resource "null_resource" "track_active_level" {
  provisioner "local-exec" {
    command = "mkdir -p config && echo a6container > config/a6container_active.txt"
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
      rm -f ${path.module}/gce-container-declaration.yaml
      echo "[INFO] Cleanup complete."
EOT
  }

  triggers = {
    always_run = timestamp()
  }
}
