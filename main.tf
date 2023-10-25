terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.51.0"
    }
  }
}

provider "google" {
  credentials = file(var.credentials_file)

  project = var.project
  region  = var.region
  zone    = var.zone
}

# Cloud SQL

resource "google_sql_database_instance" "db_instance" {
  name                = "sample-db-instance"
  database_version    = "MYSQL_8_0"
  region              = var.region
  deletion_protection = false

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled    = true
      authorized_networks {
        name = "public_ip"
        value = "0.0.0.0/0"
      }
    }
  }
}

resource "google_sql_database" "sql_db" {
  name      = "sample_database"
  instance  = google_sql_database_instance.db_instance.name
  charset   = "utf8"
  collation = "utf8_general_ci"
}

resource "google_sql_user" "users" {
  name     = var.db_user
  password = var.db_password
  instance = google_sql_database_instance.db_instance.name
  host     = "%"
}

# Cloud Storage Bucket

resource "google_storage_bucket" "export_bucket" {
  name                        = var.bucket_name
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket_object" "sample_bucket_object" {
  name         = reverse(split("/", var.bucket_file))[0]
  bucket       = google_storage_bucket.export_bucket.id
  source       = var.bucket_file
  content_type = "text/plain"
}

# Workflows

resource "google_project_service" "workflows" {
  service            = "workflows.googleapis.com"
  disable_on_destroy = false
}

resource "google_workflows_workflow" "export_workflow" {
  count = length(var.workflow_names)

  name   = var.workflow_names[count.index]
  region = var.region
  # description     = "A sample workflow"
  # crypto_key_name = "projects/PROJECT_NAME/locations/LOCATION/keyRings/KEY_RING/cryptoKeys/KEY_NAME"
  # service_account = google_service_account.workflows_service_account.id
  source_contents = file("workflow/${var.workflow_names[count.index]}.yaml")
  depends_on      = [google_project_service.workflows]
}
