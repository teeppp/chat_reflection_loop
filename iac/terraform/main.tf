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
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9.0"
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
    "secretmanager.googleapis.com",
    "run.googleapis.com",
    "iap.googleapis.com",
    "aiplatform.googleapis.com",
    "firestore.googleapis.com"
  ])
  service = each.key
  disable_on_destroy = false
}

# Firestoreデータベースの初期化
resource "google_firestore_database" "default" {
  provider = google-beta
  project = var.project_id
  name = "(default)"
  location_id = var.region
  type = "FIRESTORE_NATIVE"

  depends_on = [
    google_project_service.default
  ]
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

# Secret Manager Secret
resource "google_secret_manager_secret" "llm_api_key" {
  provider = google-beta
  project = var.project_id
  secret_id = "llm-api-key"
  replication {
    auto {
    }
  }
}

# Secret Manager Secret Version
resource "google_secret_manager_secret_version" "llm_api_key" {
  provider = google-beta
  secret = google_secret_manager_secret.llm_api_key.id
  enabled = true
  secret_data = "dummy-api-key" # 後でユーザーに設定してもらう
}

# Secret Manager Secrets
resource "google_secret_manager_secret" "openai_api_key" {
  provider = google-beta
  project = var.project_id
  secret_id = "openai-api-key"
  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "openai_api_key" {
  provider = google-beta
  secret = google_secret_manager_secret.openai_api_key.id
  enabled = true
  secret_data = var.openai_api_key
}

resource "google_secret_manager_secret" "google_api_key" {
  provider = google-beta
  project = var.project_id
  secret_id = "google-api-key"
  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "google_api_key" {
  provider = google-beta
  secret = google_secret_manager_secret.google_api_key.id
  enabled = true
  secret_data = var.google_api_key
}

resource "google_secret_manager_secret" "anthropic_api_key" {
  provider = google-beta
  project = var.project_id
  secret_id = "anthropic-api-key"
  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "anthropic_api_key" {
  provider = google-beta
  secret = google_secret_manager_secret.anthropic_api_key.id
  enabled = true
  secret_data = var.anthropic_api_key
}

resource "google_secret_manager_secret" "deepseek_api_key" {
  provider = google-beta
  project = var.project_id
  secret_id = "deepseek-api-key"
  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "deepseek_api_key" {
  provider = google-beta
  secret = google_secret_manager_secret.deepseek_api_key.id
  enabled = true
  secret_data = var.deepseek_api_key
}

resource "google_secret_manager_secret" "github_token" {
  provider = google-beta
  project = var.project_id
  secret_id = "github-token"
  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "github_token" {
  provider = google-beta
  secret = google_secret_manager_secret.github_token.id
  enabled = true
  secret_data = var.github_token
}

resource "google_secret_manager_secret" "tavily_api_key" {
  provider = google-beta
  project = var.project_id
  secret_id = "tavily-api-key"
  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "tavily_api_key" {
  provider = google-beta
  secret = google_secret_manager_secret.tavily_api_key.id
  enabled = true
  secret_data = var.tavily_api_key
}

# Service Account
resource "google_service_account" "service_account" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name}"
}

# IAM policies for service account
resource "google_project_iam_member" "service_account_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/run.invoker",
    "roles/firebase.admin",
    "roles/aiplatform.user"
  ])

  project = "228471500239"  # シークレットが存在するプロジェクト
  role    = each.key
  member  = "serviceAccount:${google_service_account.service_account.email}"
}

# 元のプロジェクトでもIAM権限を設定
resource "google_project_iam_member" "service_account_roles_original" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/run.invoker",
    "roles/firebase.admin",
    "roles/aiplatform.user"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.service_account.email}"
}

# Cloud Run service
resource "google_cloud_run_service" "default" {
  name     = var.service_name
  location = var.region

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "100"
        "run.googleapis.com/client-name" = "terraform"
      }
    }
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
        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = "openai-api-key"
              key  = "latest"
            }
          }
        }
        env {
          name = "GOOGLE_API_KEY"
          value_from {
            secret_key_ref {
              name = "google-api-key"
              key  = "latest"
            }
          }
        }
        env {
          name = "ANTHROPIC_API_KEY"
          value_from {
            secret_key_ref {
              name = "anthropic-api-key"
              key  = "latest"
            }
          }
        }
        env {
          name = "DEEPSEEK_API_KEY"
          value_from {
            secret_key_ref {
              name = "deepseek-api-key"
              key  = "latest"
            }
          }
        }
        env {
          name = "GITHUB_TOKEN"
          value_from {
            secret_key_ref {
              name = "github-token"
              key  = "latest"
            }
          }
        }
        env {
          name = "TAVILY_API_KEY"
          value_from {
            secret_key_ref {
              name = "tavily-api-key"
              key  = "latest"
            }
          }
        }
      }

      container_concurrency = 80
      timeout_seconds      = 300
      service_account_name = google_service_account.service_account.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# IAM policy to allow all access
resource "google_cloud_run_service_iam_binding" "noauth" {
  service  = google_cloud_run_service.default.name
  location = google_cloud_run_service.default.location
  role     = "roles/run.invoker"
  members  = ["allUsers"]
}


# Outputs
output "project_id" {
  value       = var.project_id
  description = "The project ID"
}

output "region" {
  value       = var.region
  description = "The region where resources are deployed"
}

output "service_name" {
  value       = var.service_name
  description = "The name of the Cloud Run service"
}

output "service_account_email" {
  value       = google_service_account.service_account.email
  description = "The email of the service account"
}

output "firebase_project_id" {
  value       = google_firebase_project.default.project
  description = "The Firebase project ID"
}

output "cloud_run_url" {
  value       = google_cloud_run_service.default.status[0].url
  description = "The URL of the deployed Cloud Run service"
}