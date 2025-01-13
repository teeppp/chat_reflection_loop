terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  user_project_override = true
}

provider "google-beta" {
  alias = "no_user_project_override"
  user_project_override = false
}

resource "google_project_service" "default" {
  provider = google-beta.no_user_project_override
  project  = var.project_id
  for_each = toset([
    "cloudbilling.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "firebase.googleapis.com",
    "identitytoolkit.googleapis.com",
    "serviceusage.googleapis.com",
  ])
  service = each.key
  disable_on_destroy = false
}

resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id
  depends_on = [
    google_project_service.default
  ]
}

resource "google_identity_platform_config" "default" {
  provider = google-beta
  project  = var.project_id

  sign_in {
    email {
      enabled = true
    }
    anonymous {
      enabled = true
    }
  }
  depends_on = [
    google_firebase_project.default
  ]
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

# IAM policy to allow authenticated access
resource "google_cloud_run_service_iam_binding" "authenticated" {
  service  = google_cloud_run_service.default.name
  location = google_cloud_run_service.default.location
  role     = "roles/run.invoker"
  members = [
    "serviceAccount:${google_service_account.service_account.email}"
  ]
}

# API Gateway API
resource "google_api_gateway_api" "default" {
  provider = google-beta
  api_id   = "backend-api"
  display_name = "Backend API"
  project = var.project_id
}

# API Gateway API Config
resource "google_api_gateway_api_config" "default" {
  provider = google-beta
  api      = google_api_gateway_api.default.api_id
  api_config_id = "backend-api-config"
  project = var.project_id
  gateway_config {
    backend_config {
      google_service_account = google_service_account.service_account.email
    }
  }
  openapi_documents {
    document {
      path = "openapi.yaml"
      contents = base64encode(templatefile("${path.module}/openapi.yaml", {
        project_id = var.project_id
        backend_url = google_cloud_run_service.default.status[0].url
      }))
    }
  }
}

# API Gateway Gateway
resource "google_api_gateway_gateway" "default" {
  provider = google-beta
  gateway_id = "backend-gateway"
  api_config = google_api_gateway_api_config.default.id
  region = var.region
  project = var.project_id
}

output "google_api_gateway_gateway_default_default_hostname" {
  value = google_api_gateway_gateway.default.default_hostname
}
