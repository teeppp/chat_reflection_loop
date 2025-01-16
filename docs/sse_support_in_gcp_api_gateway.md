# Google Cloud API Gateway における SSE サポートと代替案

## Google Cloud API Gateway の SSE サポート

Google Cloud API Gateway は、Server-Sent Events (SSE) を直接サポートしていません。API Gateway は、クライアントからのリクエストをバックエンドサービスにルーティングする役割に特化しており、SSE のようなサーバープッシュ型のストリーミングには対応していません。

## 代替技術の検討

SSE がサポートされていないため、代替技術として以下のものが考えられます。

### Apigee

Apigee は、Google Cloud が提供する API 管理プラットフォームであり、より高度な機能を提供します。Apigee は、Firebase Auth による認証、Cloud IAM に委任したリソースベースの認証、およびストリーミング処理をサポートしています。

#### Apigee と Firebase Auth の連携

Apigee は、Firebase Auth で認証されたユーザーの ID トークンを検証し、それに基づいて Apigee のアクセストークンを発行する API プロキシを実装できます。これにより、Firebase Auth を利用した認証を Apigee で統合的に管理できます。

#### Apigee と Cloud IAM の連携

Apigee は、Cloud IAM のリソースベースのアクセス制御をサポートしており、特定の Google Cloud リソースへのアクセスを IAM ポリシーに基づいて制御できます。これにより、Apigee を介した API アクセスを Cloud IAM で一元的に管理できます。

#### Apigee のストリーミング処理

Apigee は、リクエストとレスポンスのストリーミング処理をサポートしています。ただし、ストリーミング処理には以下の制限事項があります。

*   ペイロードサイズは 10MB に制限されます。
*   ストリーミングを有効にすると、リクエストまたはレスポンスのペイロードにアクセスするポリシーはエラーを引き起こす可能性があります。

#### Apigee のストリーミング設定

Apigee でストリーミングを有効にするには、ProxyEndpoint および TargetEndpoint の定義に以下のプロパティを追加します。

```xml
<TargetEndpoint name="default">
  <HTTPTargetConnection>
    <URL>http://mocktarget.apigee.net</URL>
    <Properties>
      <Property name="response.streaming.enabled">true</Property>
      <Property name="request.streaming.enabled">true</Property>
      <Property name="supports.http10">true</Property>
      <Property name="request.retain.headers">User-Agent,Referer,Accept-Language</Property>
      <Property name="retain.queryparams">apikey</Property>
    </Properties>
  </HTTPTargetConnection>
</TargetEndpoint>
```

```xml
<ProxyEndpoint name="default">
  <HTTPProxyConnection>
    <BasePath>/v1/weather</BasePath>
    <Properties>
      <Property name="allow.http10">true</Property>
      <Property name="response.streaming.enabled">true</Property>
      <Property name="request.streaming.enabled">true</Property>
    </Properties>
  </HTTPProxyConnection>
</ProxyEndpoint>
```

### Cloud Run との連携

Apigee は、Cloud Run で実行されているサービスと連携できます。Apigee を使用して、Cloud Run サービスへのリクエストをルーティングし、認証や認可などのセキュリティ機能を提供できます。

#### 連携方法

1.  Apigee で API プロキシを作成します。
2.  API プロキシの TargetEndpoint で、Cloud Run サービスの URL を指定します。
3.  必要に応じて、Firebase Auth や Cloud IAM を使用して認証を設定します。

#### 設定手順

具体的な設定手順は、以下のドキュメントを参照してください。

*   [Connecting to cloud run from Apigee x using PSC - Google Cloud](https://cloud.google.com/blog/products/serverless/connecting-to-cloud-run-from-apigee-x-using-psc)

このドキュメントでは、Private Service Connect (PSC) を使用して、Apigee から Cloud Run サービスにアクセスする方法について説明しています。PSC を使用すると、VPC ネットワークを介してプライベートにサービスに接続できます。

#### 制限事項

*   Cloud Run サービスの URL は、Apigee からアクセス可能である必要があります。
*   Apigee と Cloud Run の間の通信は、HTTP または HTTPS で行われます。

### WebSocket

WebSocket は、双方向のストリーミング通信をサポートするプロトコルであり、SSE の代替として利用できます。WebSocket は、クライアントとサーバー間で持続的な接続を確立し、リアルタイムなデータ交換を可能にします。

## Terraform を用いた IaC

Apigee, Cloud IAM, Firebase Authentication, Cloud Run の連携は、Terraform を用いて Infrastructure as Code (IaC) で構築できます。

### Terraform リソース

以下の Terraform リソースを使用して、各サービスを構成できます。

*   `google_apigee_environment`: Apigee 環境を構成します。
*   `google_cloud_run_service`: Cloud Run サービスを構成します。
*   `google_cloud_run_service_iam`: Cloud Run サービスの IAM ポリシーを構成します。
*   `google_project_iam_member`: Cloud IAM のメンバーを構成します。

`google_cloud_run_service_iam` モジュールは、Cloud Run サービスの IAM ロールを管理するために使用されます。このモジュールを使用すると、Cloud Run サービスを呼び出すことができるユーザーを構成できます。

### Terraform コード例

具体的な Terraform コード例は、以下のドキュメントを参照してください。

*   [google_cloud_run_service_iam | Resources - Terraform Registry](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_service_iam)
*   [A complete Terraform setup of a serverless application on Google Cloud ...](https://threedots.tech/post/complete-setup-of-serverless-application/)

これらのドキュメントには、Cloud Run サービスと IAM ポリシーを Terraform で構成する方法が記載されています。

### ベストプラクティス

*   Terraform モジュールを使用して、構成を再利用可能にします。
*   変数を使用して、環境固有の設定を管理します。
*   Terraform の状態をリモートで保存します。

## まとめ

Google Cloud API Gateway は SSE を直接サポートしていませんが、Apigee を利用することで、Firebase Auth や Cloud IAM と連携したストリーミング処理を実現できます。また、WebSocket を利用することで、双方向のストリーミング通信を実装することも可能です。さらに、Apigee と Cloud Run の連携は、Terraform を用いて IaC で構築できます。