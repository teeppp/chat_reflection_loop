terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud Run service
resource "google_cloud_run_service" "default" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/${var.service_name}"
        
        ports {
          container_port = 8080
        }

        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }

      }

      container_concurrency = 80
      timeout_seconds      = 300
      service_account_name = google_service_account.service_account.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "100"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Service Account
resource "google_service_account" "service_account" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name}"
}

# IAM policy to allow unauthenticated access
resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_service.default.name
  location = google_cloud_run_service.default.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}