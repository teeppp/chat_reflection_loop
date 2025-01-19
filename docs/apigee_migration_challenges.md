# APIGEEマイグレーションの課題と対応記録
## 概要
- APIGEEを利用した構成にしようと思い検討したが、元々Google Cloudの外部のサービスだったこともあり、サンプル、制限などが多く難易度が高い
- 今回はあきらめるが、その実施内容を

## 実施内容

1. Terraformを使用してApigeeリソースの作成を試みた
   - 環境（Environment）
   - インスタンス（Instance）
   - ターゲットサーバー（Target Server）

## 発生した問題

### 1. 組織の既存リソース問題
- エラー: `Error creating Organization: googleapi: Error 409: org ringed-codex-447303-q3 already associated with another project`
- 原因: Apigee組織が既に別のプロジェクトに関連付けられていた
  - これは、初回にTerraformで作成されるが、2回目以降も新規作成しようとしてしまうために生じたと考えられる
- 試行: データソース（data source）として既存の組織を参照しようとしたが、`google_apigee_organization`のデータソースは存在しなかった

### 2. VPCピアリングとネットワーク認証の問題
- エラー: `Error creating Instance: googleapi: Error 400: organization must disable VPC peering or have a authorized network before instance creation`
- 試行1: `peering_cidr_range = "NONE"` を指定して、VPCピアリングを無効化
- 試行2: `peering_cidr_range = "SLASH_22"` を指定（Apigeeインスタンスには /22 のCIDRレンジが必要）
- 課題: VPCピアリングと認可されたネットワークの設定が相互に影響し合う
- 原因: 1の原因と関連して既存の組織に対する設定が不足しているものと思われる。新規作成ではなく更新ができないことが要因かもしれない。


## 結論と教訓

1. **Terraformの限界**
   - Apigeeは元々外部サービスとして開発され、後にGCPに統合された経緯がある
   - すべてのリソースをTerraformで管理することは必ずしも効率的ではない

2. **推奨アプローチ**
   - 基本的なリソース（組織、環境など）は手動で設定
   - Terraformは補助的な設定管理ツールとして使用
   - 特に初期設定やネットワーク構成は手動で行うことを検討

3. **今後の課題**
   - Apigee組織の初期設定手順のドキュメント化
   - TerraformとCloud Consoleの使い分けガイドラインの作成
   - ネットワーク設定（VPCピアリング、認可されたネットワーク）の標準化

## 参考資料
- [Apigee Organization API Documentation](https://cloud.google.com/apigee/docs/reference/apis/apigee/rest/v1/organizations)
- [Network sizing documentation](https://cloud.google.com/apigee/docs/api-platform/get-started/install-cli)
- GitHubイシュー: [#10112 google_apigee_instance peering_cidr_range values](https://github.com/hashicorp/terraform-provider-google/issues/10112)
- [Apigee X を利用した OAuth実装と Terraform による IaC管理䛾ノウハウ](https://lp.cloudplatformonline.com/rs/808-GJW-314/images/ApigeeDay_1202_Session4.pdf)
