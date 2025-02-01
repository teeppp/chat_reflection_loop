# Backend API Documentation

## 概要

このバックエンドAPIは、Firebase AuthenticationとFirestore を利用したチャットアプリケーションのバックエンドサービスです。FastAPIフレームワークを使用して実装されています。

## 認証

すべてのAPIエンドポイントは、Firebase Authenticationを使用して保護されています。
クライアントは、リクエストヘッダーに以下の形式でFirebase IDトークンを含める必要があります：

```
Authorization: Bearer <firebase_id_token>
```

## 環境設定

1. 必要な環境変数を`.env`ファイルに設定します（`.env.sample`を参照）：

```bash
COMPOSE_PROJECT_NAME=<project_name>

# Backend
TAVILY_API_KEY=<your_tavily_key>
LOGFIRE_TOKEN=<your_logfire_token>

# Google Cloud Service Account
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/<your_google_cloud_service_account_key>.json
```

2. Google Cloud Consoleからサービスアカウントキー（JSON形式）をダウンロードし、`credentials`ディレクトリに配置します。

## データモデル

### Message
```python
{
    "role": str,          # メッセージの役割（user/assistant）
    "content": str,       # メッセージ内容
    "timestamp": datetime # メッセージのタイムスタンプ
}
```

### ChatHistory
```python
{
    "user_id": str,       # ユーザーID
    "session_id": str,    # セッションID
    "messages": List[Message], # メッセージリスト
    "created_at": datetime,    # 作成日時
    "updated_at": datetime,    # 更新日時
    "title": Optional[str]     # チャットのタイトル（オプション）
}
```

## APIエンドポイント

### チャット履歴管理

#### チャットセッションの作成
```http
POST /api/v1/chat-histories
Content-Type: application/json

{
    "initial_message": {  // オプション
        "role": "user",
        "content": "初期メッセージ"
    }
}

Response: {
    "session_id": "<session_id>"
}
```

#### メッセージの追加
```http
PUT /api/v1/chat-histories/{session_id}
Content-Type: application/json

{
    "role": "user",
    "content": "新しいメッセージ"
}

Response: {
    "success": true
}
```

#### チャット履歴の取得
```http
GET /api/v1/chat-histories?page=1&per_page=10

Response: {
    "histories": [ChatHistory],
    "total": int
}
```

#### 特定のチャットセッションの取得
```http
GET /api/v1/chat-histories/{session_id}

Response: {
    "history": ChatHistory
}
```

#### チャットセッションの削除
```http
DELETE /api/v1/chat-histories/{session_id}

Response: {
    "success": true
}
```

### エージェント操作

#### エージェントの実行（同期）
```http
POST /baseagent/invoke
Content-Type: application/json

{
    "message": "ユーザーメッセージ"
}

Response: {
    "response": "エージェントからの応答",
    "status": "success"
}
```

#### エージェントの実行（ストリーミング）
```http
POST /baseagent/stream
Content-Type: application/json

{
    "message": "ユーザーメッセージ"
}

Response: Server-Sent Events (SSE)
Event: message
Data: {"text": "ストリーミングテキスト"}
```

## ヘルスチェック

```http
GET /health

Response: {
    "status": "healthy"
}
```

## 開発用ドキュメント

API仕様の詳細については、サーバー起動後に以下のURLでSwagger UIを確認できます：

```
http://your-server/docs