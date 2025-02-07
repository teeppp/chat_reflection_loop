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

Terraform を使用して、以下の Google Cloud リソースがデプロイされます：

1.  **Cloud Run サービス (`google_cloud_run_service`)**
    -   FastAPI アプリケーションを実行する Cloud Run サービス
    -   コンテナイメージ、環境変数、ポート設定などを定義します
        - コンテナの並行実行数: 80
        - メモリ制限: 512Mi
        - CPU制限: 1000m (1 core)
        - 最大スケール: 100インスタンス
        - タイムアウト: 300秒

2.  **Firebase プロジェクト**
    -   `google_firebase_project` と `google_identity_platform_config` を設定
    -   Email と Anonymous 認証を有効化

3.  **サービスアカウント (`google_service_account`)**
    -   Cloud Run サービスが Google Cloud リソースにアクセスするためのサービスアカウント
    -   以下の権限を付与：
        - roles/secretmanager.secretAccessor
        - roles/run.invoker
        - roles/firebase.admin

4.  **Secret Manager シークレット**
    -   以下のAPIキーとトークンを安全に管理：
        - OpenAI API Key
        - Google API Key
        - Anthropic API Key
        - Deepseek API Key
        - GitHub Token
        - Tavily API Key

## デプロイ手順

### 1. Terraform の設定

1. `terraform.tfvars.example` を `terraform.tfvars` にコピーします。

```bash
cp iac/terraform/terraform.tfvars.example iac/terraform/terraform.tfvars
```

2. `terraform.tfvars` を編集し、以下の値を設定します：
   - `project_id`: Google Cloud プロジェクト ID
   - `region`: デプロイするリージョン（デフォルト: `asia-northeast1`）
   - `service_name`: Cloud Run サービス名
   - `billing_account`: 課金アカウントID
   - APIキーとトークン（シークレット値）：
     - `openai_api_key`
     - `google_api_key`
     - `anthropic_api_key`
     - `deepseek_api_key`
     - `github_token`
     - `tavily_api_key`

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

### APIエンドポイントの確認

Cloud Runサービスへのアクセスをテストします。すべてのエンドポイントにはFirebase認証が必要です：

1. エンドポイントのURLを取得：

```bash
ENDPOINT=$(gcloud run services describe backend --platform managed --region asia-northeast1 --format 'value(status.url)')
```

2. Firebase認証トークン（JWT）を取得：

```bash
# scriptsディレクトリに移動
cd scripts

# 必要なパッケージをインストール
npm install

# JWTトークンを取得
JWT=$(node get-firebase-jwt.js | grep "JWT:" | cut -d' ' -f2)
```

3. ヘルスチェックエンドポイントをテスト：

```bash
curl -H "Authorization: Bearer $JWT" $ENDPOINT/health
```

4. invokeエンドポイントをテスト：

```bash
curl -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT" \
  -d '{"message": "hello"}' \
  $ENDPOINT/baseagent/invoke
```

5. streamエンドポイントをテスト：

```bash
curl -N -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT" \
  -d '{"message": "hello"}' \
  $ENDPOINT/baseagent/stream
```

### シークレットの更新

Secret Managerのシークレットを更新する場合：

1. `terraform.tfvars` の値を更新します。
2. `terraform apply` を実行します。
3. 必要に応じてCloud Runサービスを再デプロイします：
   ```bash
   gcloud run services update backend \
     --platform managed \
     --region asia-northeast1 \
     --update-labels force-update=$(date +%s)
   ```

## リソースの削除

デプロイした Cloud Run サービスと関連リソースを削除するには：

```bash
cd iac/terraform
terraform destroy -auto-approve
```

## 注意点

- Cloud Run は環境変数 `PORT` を自動的に設定します
- コンテナは指定されたポート（8080）でリッスンする必要があります
- デプロイ時は必ず最新のイメージを Container Registry にプッシュしてください
- Secret Manager のシークレットは適切に管理し、定期的な更新を推奨します
- Cloud Run サービスは一般公開（allUsers）設定になっています