# Google Cloud API Gateway における SSE サポートと代替案

## Google Cloud API Gateway の SSE サポート

Google Cloud API Gateway は、Server-Sent Events (SSE) を直接サポートしていません。API Gateway は、クライアントからのリクエストをバックエンドサービスにルーティングする役割に特化しており、SSE のようなサーバープッシュ型のストリーミングには対応していません。

## 代替技術の検討

SSE がサポートされていないため、代替技術として以下のものが考えられます。

### ~~Apigee~~ （実装困難）

~~Apigee は、Google Cloud が提供する API 管理プラットフォームであり、より高度な機能を提供します。~~

**注意: Apigeeを使用した実装は[困難である](./apigee_migration_challenges.md)ため実施しないことを決めた：**

### Identity-Aware Proxy (IAP)による代替案

Cloud Load BalancerとIdentity-Aware Proxy (IAP)を組み合わせることで、より効果的なソリューションを実現できます。

#### IAPの特徴

1. 認証・認可の機能：
   - Google Identity Serviceとの統合
   - OAuth 2.0認証フロー
   - IAMポリシーベースのアクセス制御

2. SSEサポート：
   - ストリーミング通信の完全サポート
   - ペイロードサイズの制限なし
   - WebSocketsもサポート

3. セキュリティ：
   - TCPフォワーディングの保護
   - HTTPSトラフィックの暗号化
   - セッション管理

#### IAPとCloud Runの連携

1. アーキテクチャ構成：
```
Client → Cloud Load Balancer → Identity-Aware Proxy → Cloud Run
                                     ↓
                              Firebase Auth
                                     ↓
                                IAM Policies
```

2. 主な利点：
   - インフラ層での認証処理
   - スケーラブルな負荷分散
   - 堅牢なセキュリティ
   - SSE/ストリーミングの完全サポート

### WebSocket

WebSocket は、双方向のストリーミング通信をサポートするプロトコルであり、SSE の代替として利用できます。WebSocket は、クライアントとサーバー間で持続的な接続を確立し、リアルタイムなデータ交換を可能にします。

## Terraform を用いた IaC

IAPとCloud Runの連携は、Terraform を用いて Infrastructure as Code (IaC) で構築できます。

### Terraform リソース

以下の Terraform リソースを使用して、各サービスを構成できます：

```hcl
# Cloud Load Balancer + IAP構成
resource "google_compute_backend_service" "default" {
  name        = "llm-agent-backend"
  protocol    = "HTTP"
  timeout_sec = 30

  backend {
    group = google_compute_region_network_endpoint_group.cloudrun_neg.id
  }

  iap {
    oauth2_client_id     = google_iap_client.default.client_id
    oauth2_client_secret = google_iap_client.default.secret
  }
}

# Cloud Run NEG (Network Endpoint Group)
resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  name                  = "llm-agent-neg"
  network_endpoint_type = "SERVERLESS"
  region               = var.region
  cloud_run {
    service = google_cloud_run_service.default.name
  }
}

# IAMポリシー設定
resource "google_iap_web_backend_service_iam_binding" "binding" {
  project = var.project_id
  web_backend_service = google_compute_backend_service.default.name
  role    = "roles/iap.httpsResourceAccessor"
  members = [
    "serviceAccount:${google_service_account.service_account.email}",
    "user:${var.allowed_users}"
  ]
}
```

### ベストプラクティス

* Terraform モジュールを使用して、構成を再利用可能にします。
* 変数を使用して、環境固有の設定を管理します。
* Terraform の状態をリモートで保存します。
* IAPの設定は環境ごとに適切に分離します。

## まとめ

Google Cloud API Gateway は SSE を直接サポートしていません。当初検討したApigeeによる実装は、ストリーミングの制限や実装の複雑さから実用的ではないことが判明しました。代替案として、Cloud Load BalancerとIAP（Identity-Aware Proxy）を組み合わせることで、より効果的なソリューションを実現できます。この方式では、SSEの完全サポート、堅牢なセキュリティ、スケーラビリティを確保しつつ、実装の複雑さを軽減できます。