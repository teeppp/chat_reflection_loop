# Apigee の新規デプロイ手順

## 目的
API Gateway を Apigee に置き換えて新規デプロイする。

## 前提条件
- Apigee組織および環境がプロビジョニング済みであること。
- ApigeeでAPIプロキシのベースとなる設定が完了していること。

## 影響範囲

- APIのエンドポイントが変更されるため、APIを利用しているクライアントは、新しいエンドポイントを指すように構成を更新する必要がある。(ただし、今回は新規作成のため影響なし)
- DNSの切り替え時に、一時的にAPIにアクセスできない時間が発生する可能性がある。

**より詳細な影響範囲:**

1.  **APIエンドポイントの変更:**
    *   現在のAPIGatewayのエンドポイント (`google_api_gateway_gateway.default.default_hostname`) から、Apigeeのエンドポイントに変わります。
    *   APIを利用するクライアントは、新しいエンドポイントを使用するように更新が必要です。
    *   クライアント側の設定変更が必要となるため、事前に通知と移行期間を設ける必要があります。

2.  **認証・認可の方式:**
    *   現在のAPIGatewayで使用している認証・認可の方式 (例えば、Firebase Authentication) が、Apigeeでも同等に機能するように設定する必要があります。
    *   Apigeeのポリシー設定を確認し、必要に応じて調整します。

3.  **リクエスト・レスポンスの形式:**
    *   APIGatewayとApigeeで、リクエストヘッダー、レスポンスヘッダー、リクエストボディ、レスポンスボディの形式に差異がないか確認します。
    *   必要に応じて、Apigeeで変換ポリシーを設定します。

4.  **エラーハンドリング:**
    *   APIGatewayとApigeeで、エラーコードやエラーメッセージの形式に差異がないか確認します。
    *   クライアント側でエラーハンドリングのロジック変更が必要になる場合があります。

5.  **レート制限とクォータ:**
    *   現在APIGatewayで設定しているレート制限やクォータが、Apigeeでも同等に機能するように設定する必要があります。

6.  **ロギングとモニタリング:**
    *   Apigeeでのロギングとモニタリングの設定を行い、切り替え後にAPIの状況を監視できるように準備します。

## Terraform による Apigee の実装例

Apigee の基本的な構成は、以下の Terraform リソースを使用して実装できます。

```terraform
# Apigee 環境
resource "google_apigee_environment" "default" {
  org_id      = "your-apigee-org-id"
  name        = "your-apigee-env-name"
  display_name = "Your Apigee Environment"
}

# Apigee インスタンス
resource "google_apigee_instance" "default" {
  org_id      = "your-apigee-org-id"
  name        = "your-apigee-instance-name"
  location    = "your-gcp-region"
  disk_encryption_key_name = "your-disk-encryption-key"
}

# Apigee API プロキシ
resource "google_apigee_proxy" "default" {
  org_id      = "your-apigee-org-id"
  name        = "your-api-proxy-name"
  bundle      = "path/to/your/api-proxy-bundle.zip" # APIプロキシのバンドルファイル
  depends_on = [google_apigee_environment.default, google_apigee_instance.default]
}

# Apigee ターゲットサーバー
resource "google_apigee_target_server" "default" {
  org_id      = "your-apigee-org-id"
  name        = "your-target-server-name"
  host        = "your-backend-service-url" # バックエンドサービスのURL
  port        = 443
  protocol    = "https"
  depends_on = [google_apigee_environment.default, google_apigee_instance.default]
}
```

**注意点:**

*   上記の例は基本的な構成であり、実際の環境に合わせて調整が必要です。
*   `org_id`、`name`、`location`、`disk_encryption_key_name`、`bundle`、`host` などの変数は、実際の値に置き換える必要があります。
*   APIプロキシのバンドルファイル (`.zip`) は、事前に作成し、Terraformからアクセスできる場所に配置する必要があります。
*   Apigeeの詳細な設定 (ポリシー、ルーティングなど) は、Apigeeの管理画面で設定する必要があります。
*   SSL証明書の設定は、`google_apigee_keystore` と `google_apigee_alias` リソースを使用して行うことができますが、ここでは省略します。

## Terraform で実装できない設定

以下の設定は、Terraformだけでは実装できません。

*   APIプロキシの詳細なポリシー設定 (認証、認可、変換など)
*   APIプロキシの詳細なルーティング設定
*   Apigeeの環境設定 (キャッシュ、ロギングなど)
*   SSL証明書のアップロードと設定
*   Apigeeのユーザーと権限管理

これらの設定は、Apigeeの管理画面またはAPIを使用して行う必要があります。