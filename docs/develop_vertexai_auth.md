# 開発環境でのVertex AI認証設定

## 問題

開発環境（docker compose）でVertex AIのAPIにアクセスできない問題が発生しています。

### 現状確認

1. 開発環境
   - `GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/firebase-credentials.json` を使用
   - 現在のfirebase-credentials.jsonはVertexAIの権限を持っていない可能性がある

2. 本番環境（Cloud Run）
   - Cloud Runのデフォルトの認証情報（Workload Identity）を使用
   - すでにVertexAIの権限は付与済み（`roles/aiplatform.user`）

## サービスアカウントキーの取得手順

### 1. Google Cloud Consoleにアクセス
1. [Google Cloud Console](https://console.cloud.google.com/)を開く
2. プロジェクトを選択（ringed-codex-447303-q3）

### 2. サービスアカウント画面に移動
1. 左側のナビゲーションメニューを開く
2. [IAMと管理] を選択
3. [サービスアカウント] をクリック

### 3. 既存のサービスアカウントを選択
1. リストから `backend-sa@ringed-codex-447303-q3.iam.gserviceaccount.com` を探す
2. サービスアカウント名をクリックして詳細画面を開く

### 4. 新しいキーを作成
1. 上部の [キー] タブをクリック
2. [キーを追加] ボタンをクリック
3. [新しいキーを作成] を選択
4. キーのタイプで [JSON] を選択
5. [作成] をクリック
   - JSONファイルが自動的にダウンロードされます
   - このファイルは慎重に扱ってください。これがサービスアカウントの認証情報です

### 5. キーファイルの配置
1. ダウンロードしたJSONファイルの名前を `firebase-credentials.json` に変更
2. このファイルを `backend/credentials/` ディレクトリに移動
   ```bash
   mv ~/Downloads/[ダウンロードされたJSONファイル名] backend/credentials/firebase-credentials.json
   ```

### 6. 開発環境での動作確認
1. 開発環境を起動：
   ```bash
   docker compose up dev_backend
   ```
2. APIのリクエストでVertex AIが正常に動作することを確認

## セキュリティに関する重要な注意事項

### キーの保護
- サービスアカウントキーは機密情報です
- GitHubにはアップロードしないでください（.gitignoreに含まれていることを確認）
- 安全な場所にバックアップを保管

### キーのローテーション
- キーは定期的に更新することを推奨
- 古いキーは不要になったら削除
- 新しいキーを作成する前に古いキーを削除することで、アクティブなキーの数を制限

### トラブルシューティング

キーを設定しても認証エラーが発生する場合：

1. 環境変数の確認
   ```bash
   docker compose config
   ```
   - `GOOGLE_APPLICATION_CREDENTIALS` が正しく設定されているか確認

2. ファイルのパーミッション確認
   ```bash
   ls -l backend/credentials/firebase-credentials.json
   ```
   - ファイルが読み取り可能か確認

3. サービスアカウントの権限確認
   - Google Cloud Console > IAMと管理 > IAM で以下の権限があることを確認：
     - `roles/aiplatform.user`
     - `roles/firebase.admin`