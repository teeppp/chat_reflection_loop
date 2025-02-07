# Vertex AI 権限設定の実装手順

## 概要
Cloud RunからVertex AI Gemini APIを利用するために必要な権限設定をTerraformで実装する手順です。

## 必要な変更

### 1. APIの有効化
`google_project_service.default`のfor_eachに以下のAPIを追加：

```hcl
"aiplatform.googleapis.com"
```

### 2. サービスアカウントの権限追加
`google_project_iam_member.service_account_roles`と`google_project_iam_member.service_account_roles_original`のfor_eachに以下のロールを追加：

```hcl
"roles/aiplatform.user"
```

## 実装手順

1. `main.tf`を開き、`google_project_service.default`リソースを探します
2. for_eachブロック内に`"aiplatform.googleapis.com"`を追加します
3. `google_project_iam_member.service_account_roles`と`google_project_iam_member.service_account_roles_original`を探します
4. 両方のfor_eachブロック内に`"roles/aiplatform.user"`を追加します

## 期待される結果

- Cloud Run上のアプリケーションがVertex AI APIを呼び出せるようになります
- サービスアカウントが適切な権限を持ち、Gemini APIにアクセスできるようになります

## 注意点

- 変更後は`terraform plan`を実行して変更内容を確認してください
- その後`terraform apply`を実行して変更を適用してください
- 権限が反映されるまで数分かかる場合があります