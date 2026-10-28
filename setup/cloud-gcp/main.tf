terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

variable "project_id" {
  type        = string
  description = "Project GCP dùng riêng cho lab, đã có billing và budget."
}

provider "google" {
  project = var.project_id
  region  = "us-central1"
}

resource "google_project_service" "apis" {
  for_each           = toset(["bigquery.googleapis.com", "storage.googleapis.com", "iam.googleapis.com"])
  service            = each.value
  disable_on_destroy = false
}

resource "google_service_account" "pipeline" {
  account_id   = "olist-lab-pipeline"
  display_name = "Olist lab pipeline"
  depends_on   = [google_project_service.apis]
}

resource "google_service_account" "bi" {
  account_id   = "olist-lab-bi"
  display_name = "Olist lab BI reader"
  depends_on   = [google_project_service.apis]
}

resource "google_storage_bucket" "lake" {
  for_each                    = toset(["raw", "curated"])
  name                        = "${var.project_id}-olist-lab-${each.value}"
  location                    = "US"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true # Chỉ dùng bucket do lab tạo, chứa dữ liệu giả.
  labels                      = { project = "olist", env = "learn" }
  versioning { enabled = true }
  # Lab cần dọn ngay; production phải chọn retention/soft-delete theo yêu cầu phục hồi.
  soft_delete_policy { retention_duration_seconds = 0 }
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
  depends_on = [google_project_service.apis]
}

resource "google_bigquery_dataset" "datasets" {
  for_each                    = toset(["olist_staging", "olist_analytics"])
  dataset_id                  = each.value
  location                    = "US"
  delete_contents_on_destroy  = true # Datasets dùng riêng cho lab.
  labels                      = { project = "olist", env = "learn" }
  default_table_expiration_ms = 86400000
  depends_on                  = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "pipeline_raw" {
  bucket = google_storage_bucket.lake["raw"].name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.pipeline.email}"
}

resource "google_storage_bucket_iam_member" "pipeline_curated" {
  bucket = google_storage_bucket.lake["curated"].name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.pipeline.email}"
}

resource "google_bigquery_dataset_iam_member" "pipeline" {
  for_each   = google_bigquery_dataset.datasets
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pipeline.email}"
}

resource "google_bigquery_dataset_iam_member" "bi" {
  dataset_id = google_bigquery_dataset.datasets["olist_analytics"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.bi.email}"
}

resource "google_project_iam_member" "jobs" {
  for_each = {
    pipeline = google_service_account.pipeline.email
    bi       = google_service_account.bi.email
  }
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${each.value}"
}

output "raw_bucket" { value = google_storage_bucket.lake["raw"].name }
output "curated_bucket" { value = google_storage_bucket.lake["curated"].name }
output "pipeline_email" { value = google_service_account.pipeline.email }
output "bi_email" { value = google_service_account.bi.email }
