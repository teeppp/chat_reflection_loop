# Cloud Run デプロイ手順

このドキュメントでは、FastAPI アプリケーションを Google Cloud Run にデプロイする手順を説明します。

## デプロイ方法の変更について

当初、Google Cloud Deployment Manager を使用してデプロイを試みましたが、以下の問題が発生したため、Terraform に移行しました：

1.  **Cloud Run のデプロイ失敗**
    -   Deployment Manager のテンプレート（`cloudrun.jinja`）を使用したデプロイが失敗
    -   Cloud Run サービスの設定が複雑で、Jinja2 テンプレートでの管理が困難

2.  **デバッグの容易さ**
    -   Terraform は詳細なエラーメッセージとログを提供
    -   デプロイの各ステップが明確で、問題の特定と修正が容易

この移行により、より安定したデプロイプロセスを実現できました。

## Terraform でデプロイされるリソース

Terraform を使用して、以下の Google Cloud リソースがデプロイされます。

1.  **Cloud Run サービス (`google_cloud_run_service`)**
    -   FastAPI アプリケーションを実行する Cloud Run サービス。
    -   コンテナイメージ、環境変数、ポート設定などを定義します。
        - コンテナの並行実行数: 80
        - メモリ制限: 512Mi
        - CPU制限: 1 core
        - 最大スケール: 100インスタンス
        - タイムアウト: 300秒

2.  **サービスアカウント (`google_service_account`)**
    -   Cloud Run サービスが Google Cloud リソースにアクセスするためのサービスアカウント。
    -   最小限の権限を持つように設定されています。
        - サービス固有のサービスアカウントを作成

3.  **IAM メンバー (`google_cloud_run_service_iam_member`)**
    -   Cloud Run サービスへのアクセスを許可する IAM ポリシー。
    -   `allUsers` に `roles/run.invoker` ロールを付与し、一般公開します。

## デプロイ手順

### 1. Terraform の設定

1. `terraform.tfvars.example` を `terraform.tfvars` にコピーします。

```bash
cp iac/terraform/terraform.tfvars.example iac/terraform/terraform.tfvars
```

2. `terraform.tfvars` を編集し、以下の値を設定します：
   - `project_id`: Google Cloud プロジェクト ID
   - `region`: デプロイするリージョン（例：`asia-northeast1`）
   - `service_name`: Cloud Run サービス名

### 2. Docker イメージのビルドとプッシュ

1. Docker を Google Cloud に認証します。

```bash
gcloud auth configure-docker
```

2. `backend` ディレクトリで Docker イメージをビルドします。

```bash
cd backend && docker compose build
```

3. ビルドしたイメージに Container Registry のタグを付けます。

```bash
docker tag docker.io/library/scrum_agent-backend gcr.io/[PROJECT_ID]/[SERVICE_NAME]
```

4. イメージを Container Registry にプッシュします。

```bash
docker push gcr.io/[PROJECT_ID]/[SERVICE_NAME]
```

### 3. Terraform によるデプロイ

1. Terraform を初期化します。

```bash
cd iac/terraform && terraform init
```

2. デプロイを実行します。

```bash
terraform apply -auto-approve
```

## トラブルシューティング

デプロイ中に以下の問題が発生し、それぞれ対応を行いました：

1. **環境変数 `PORT` の問題**
   - 症状：Cloud Run が環境変数 `PORT` で指定されたポートでリッスンできない
   - 対応：`backend/Dockerfile` の `CMD` の引数で `--port` を `8080` に固定

2. **ポートの公開**
   - 症状：コンテナのポートが正しく公開されていない
   - 対応：`backend/Dockerfile` に `EXPOSE 8080` を追加

3. **FastAPI の起動ファイル**
   - 症状：`main.py` が見つからないエラー
   - 対応：`backend/Dockerfile` の `CMD` で指定するファイルを `main.py` から `api.py` に変更

## デプロイ後の確認

デプロイが完了すると、以下の URL でアプリケーションにアクセスできます：
```
https://[SERVICE_NAME]-[PROJECT_NUMBER].[REGION].run.app
```

## Terraform でデプロイされるリソース

Terraform を使用して、以下の Google Cloud リソースがデプロイされます。

1.  **Cloud Run サービス (`google_cloud_run_service`)**
    -   FastAPI アプリケーションを実行する Cloud Run サービス。
    -   コンテナイメージ、環境変数、ポート設定などを定義します。

2.  **サービスアカウント (`google_service_account`)**
    -   Cloud Run サービスが Google Cloud リソースにアクセスするためのサービスアカウント。
    -   最小限の権限を持つように設定されています。

3.  **IAM メンバー (`google_cloud_run_service_iam_member`)**
    -   Cloud Run サービスへのアクセスを許可する IAM ポリシー。
    -   `allUsers` に `roles/run.invoker` ロールを付与し、一般公開します。

## リソースの削除

デプロイした Cloud Run サービスと関連リソースを削除するには、以下の手順を実行します。

1. `iac/terraform` ディレクトリに移動します。

```bash
cd iac/terraform
```

2. Terraform を使用してリソースを削除します。

```bash
terraform destroy -auto-approve
```

## 注意点

- Cloud Run は環境変数 `PORT` を自動的に設定します
- コンテナは指定されたポートでリッスンする必要があります
- デプロイ時は必ず最新のイメージを Container Registry にプッシュしてください

## Firebase Authentication と API Gateway の設定

このデプロイ手順では、Firebase Authentication を使用して Cloud Run サービスへのアクセスを制限し、API Gateway を使用して認証・認可を処理します。

### Firebase Authentication の設定

1.  Firebase プロジェクトを作成し、Firebase Authentication を有効にします。
2.  Terraform を使用して、Firebase Authentication の設定をデプロイします。
    -   `google_firebase_project` リソースと `google_identity_platform_config` リソースを使用します。

### API Gateway の設定

1.  API Gateway の設定を Terraform に追加します。
    -   `google_api_gateway_api`, `google_api_gateway_api_config`, `google_api_gateway_gateway` リソースを使用します。
2.  OpenAPI 仕様 (`openapi.yaml`) を定義し、API Gateway のエンドポイントと認証設定を記述します。
    -   `securityDefinitions` で Firebase Authentication を設定します。
    -   `x-google-backend` で Cloud Run サービスの URL を指定します。

### JWT トークンの取得

1.  `scripts/get-firebase-jwt.js` を使用して、Firebase Authentication の JWT トークンを取得します。
2.  `.env` ファイルに Firebase の認証情報を設定します。
3.  以下のコマンドを実行して JWT トークンを取得します。
    ```bash
    node scripts/get-firebase-jwt.js
    ```
4.  取得した JWT トークンを `Authorization` ヘッダーに含めて、API Gateway にアクセスします。
    ```bash
    curl -H "Authorization: Bearer <JWT>" https://<API_GATEWAY_URL>
    ```

これらの設定により、Cloud Run サービスは API Gateway を経由してアクセスできるようになり、Firebase Authentication で認証されたユーザーのみがアクセスできるようになります。

## Secret Manager の設定とAPIエンドポイントの確認

今回の変更で、Secret Managerを使用してAPIキーを管理するように変更しました。

### Secret Manager の設定
1.  `terraform.tfvars` にAPIキーとトークンを設定します。
    ```hcl
    # API Keys and Tokens
    openai_api_key     = "your-openai-api-key"
    google_api_key     = "your-google-api-key"
    anthropic_api_key  = "your-anthropic-api-key"
    deepseek_api_key   = "your-deepseek-api-key"
    github_token       = "your-github-token"
    tavily_api_key     = "your-tavily-api-key"
    ```
2.  `terraform apply` を実行して、Secret Managerにシークレットを登録します。
3.  Cloud Runサービスは環境変数を通してシークレットにアクセスします。
4.  サービスアカウントには `secretmanager.secretAccessor` ロールが必要です。

### APIエンドポイントの確認
Cloud Runサービスへの直接アクセスをテストします。
```bash
# 認証トークンを取得
TOKEN=$(gcloud auth print-identity-token)

# ヘルスチェックエンドポイントをテスト
curl -H "Authorization: Bearer $TOKEN" \
  $(gcloud run services describe backend --platform managed --region asia-northeast1 --format 'value(status.url)')/health

# invokeエンドポイントをテスト
curl -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}' \
  $(gcloud run services describe backend --platform managed --region asia-northeast1 --format 'value(status.url)')/baseagent/invoke

# streamエンドポイントをテスト
curl -N -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}' \
  $(gcloud run services describe backend --platform managed --region asia-northeast1 --format 'value(status.url)')/baseagent/stream
```

### シークレットの更新
1.  `terraform.tfvars` の値を更新します。
2.  `terraform apply` を実行します。
3.  必要に応じてCloud Runサービスを強制的に再デプロイします。
    ```bash
    gcloud run services update backend \
      --platform managed \
      --region asia-northeast1 \
      --update-labels force-update=$(date +%s)