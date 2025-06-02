
module "setup" {
  source     = "./modules/setup"
  project_id = var.project_id
  region     = var.region
}


# ─────────────────────────────────────────────────────────────
# Deploy Level Module: a1openbucket
# ─────────────────────────────────────────────────────────────
module "a1openbucket" {
  source     = "./modules/a1openbucket"
  project_id = var.project_id
}


# ─────────────────────────────────────────────────────────────
# Deploy Level Module: a2finance
# ─────────────────────────────────────────────────────────────
module "a2finance" {
  source              = "./modules/a2finance"
  project_id          = var.project_id
  region              = var.region
  zone                = var.zone
  ssh_username        = var.ssh_username
}


module "a3password" {
  source     = "./modules/a3password"
  project_id = var.project_id
  region     = var.region
  zone       = var.zone
}

module "a4error" {
  source       = "./modules/a4error"
  project_id   = var.project_id
  region       = var.region
  zone         = var.zone
}

module "a5power" {
  source       = "./modules/a5power"
  project_id   = var.project_id
  region       = var.region
  zone         = var.zone
}


module "a6container" {
  source     = "./modules/a6container"
  project_id = var.project_id
  region     = var.region
  zone       = var.zone
}

module "auditLogging" {
  source     = "./modules/auditLogging"
  project_id = var.project_id
}

module "audit_intro" {
  source     = "./modules/audit_intro"
  region     = var.region
  project_id = var.project_id
}