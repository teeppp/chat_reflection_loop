## タスク概要

backendを再デプロイするために、Terraformの設定を変更し、APIキーをSecret Managerに登録するようにしました。

## 実施内容

1.  `iac/terraform/main.tf` に、Secret ManagerのSecretとSecret Versionを作成するためのリソースを追加しました。
    -   `google_secret_manager_secret` リソースと `google_secret_manager_secret_version` リソースを追加しました。
2.  Cloud RunからSecretにアクセスできるようにIAMを設定しました。
    -   `google_project_iam_member` リソースを追加し、Cloud RunのサービスアカウントにSecret Managerのアクセス権限を付与しました。
3.  Cloud Runの環境変数からSecretを参照するように設定しました。
    -   `google_cloud_run_service` リソースの `env` ブロックを修正し、Secret ManagerからAPIキーを取得するように設定しました。
4.  `backend/.env.sample` を読み込み、必要なAPIキーの名前を取得しました。
    -   `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `GITHUB_TOKEN`, `TAVILY_API_KEY` を取得しました。
5.  これらのAPIキーに対応するSecret ManagerのSecretとSecret Versionを作成し、Cloud Runの環境変数から参照するように設定しました。
6.  `google_secret_manager_secret` リソースに `project = var.project_id` を追加しました。

## 変更後の `iac/terraform/main.tf`

```terraform
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
  secret_data = "dummy-openai-api-key" # 後でユーザーに設定してもらう
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
  secret_data = "dummy-google-api-key" # 後でユーザーに設定してもらう
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
  secret_data = "dummy-anthropic-api-key" # 後でユーザーに設定してもらう
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
  secret_data = "dummy-deepseek-api-key" # 後でユーザーに設定してもらう
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
  secret_data = "dummy-github-token" # 後でユーザーに設定してもらう
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
  secret_data = "dummy-tavily-api-key" # 後でユーザーに設定してもらう
}

# IAM policy to allow Cloud Run access to Secret Manager
resource "google_project_iam_member" "secret_manager_access" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.service_account.email}"
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
        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.openai_api_key.id
              key  = "latest"
            }
          }
        }
        env {
          name = "GOOGLE_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.google_api_key.id
              key  = "latest"
            }
          }
        }
        env {
          name = "ANTHROPIC_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.anthropic_api_key.id
              key  = "latest"
            }
          }
        }
        env {
          name = "DEEPSEEK_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.deepseek_api_key.id
              key  = "latest"
            }
          }
        }
        env {
          name = "GITHUB_TOKEN"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.github_token.id
              key  = "latest"
            }
          }
        }
        env {
          name = "TAVILY_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.tavily_api_key.id
              key  = "latest"
            }
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

## 変更内容の説明

1. Secret Managerのリソース
   - 各APIキーに対応するSecretを作成
   - Secretの自動レプリケーションを設定
   - 初期値として"dummy-xxx-api-key"を設定（後でユーザーが更新）

2. Cloud RunのIAM設定
   - サービスアカウントにSecret Managerのアクセス権限を付与
   - `roles/secretmanager.secretAccessor`ロールを使用

3. Cloud Run環境変数の設定
   - 各環境変数をSecret Managerから参照するように変更
   - `value_from.secret_key_ref`を使用して最新バージョンを参照

## デプロイ手順

1. Terraformの初期化と適用:
```bash
cd iac/terraform
terraform init
terraform plan
terraform apply
```

2. バックエンドイメージのビルドとプッシュ:
```bash
cd backend
docker build -t gcr.io/${PROJECT_ID}/${SERVICE_NAME} .
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}
```

## ユーザーへの指示

1. Secret Managerでの実際のAPIキーの設定:
```bash
# OpenAI API Key
gcloud secrets versions add openai-api-key --data-file=- <<< "your-openai-api-key"

# Google API Key
gcloud secrets versions add google-api-key --data-file=- <<< "your-google-api-key"

# Anthropic API Key
gcloud secrets versions add anthropic-api-key --data-file=- <<< "your-anthropic-api-key"

# Deepseek API Key
gcloud secrets versions add deepseek-api-key --data-file=- <<< "your-deepseek-api-key"

# GitHub Token
gcloud secrets versions add github-token --data-file=- <<< "your-github-token"

# Tavily API Key
gcloud secrets versions add tavily-api-key --data-file=- <<< "your-tavily-api-key"
```

2. 設定の確認:
```bash
# 各Secretの一覧を確認
gcloud secrets list

# 特定のSecretの最新バージョンを確認
gcloud secrets versions access latest --secret="openai-api-key"
```

## 課題と改善案

1. セキュリティ
   - 課題: 初期デプロイ時にダミーの値を使用している
   - 改善案: Terraformの外部でAPIキーを設定し、そのあとでTerraformを適用する手順を推奨

2. メンテナンス性
   - 課題: APIキーの数が増えるとSecret定義が冗長になる
   - 改善案: for_eachを使用してリソース定義をDRYに保つ

3. 運用
   - 課題: APIキーのローテーションが手動操作になる
   - 改善案: キーローテーションを自動化するスクリプトの作成を検討
