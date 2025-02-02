# Backend API Documentation

## 概要

このバックエンドAPIは、Firebase AuthenticationとFirestore を利用したチャットアプリケーションのバックエンドサービスです。FastAPIフレームワークを使用して実装されています。

## 認証

すべてのAPIエンドポイントは、Firebase Authenticationを使用して保護されています。
クライアントは、リクエストヘッダーに以下の形式でFirebase IDトークンを含める必要があります:

```
Authorization: Bearer <firebase_id_token>
```

## 環境設定

1. 必要な環境変数を`.env`ファイルに設定します(`.env.sample`を参照):

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
    "title": Optional[str],    # チャットのタイトル(オプション)
    "reflection": Optional[dict] # 振り返り情報
}
```

### UserPattern
```python
{
    "pattern": str,       # パターン名(例: "シンプル志向")
    "category": str,      # カテゴリ(例: "coding_style", "architecture", "debugging")
    "confidence": float,  # 確信度(0.0-1.0)
    "last_updated": datetime, # 最終更新日時
    "examples": List[str], # パターンの例
    "context": str        # LLMによって検出された文脈
}
```

### PersonalizedAgentInstruction
```python
{
    "user_id": str,       # ユーザーID
    "patterns": List[UserPattern], # ユーザーの行動パターン
    "base_instructions": List[AgentInstruction], # 基本指示
    "personalized_instructions": str, # カスタマイズされた指示
    "preferred_role": str, # 推奨される役割（code/architect/ask）
    "updated_at": datetime # 更新日時
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

### プロファイル管理

#### 振り返りからのパターン分析
```http
POST /api/v1/profiles/{user_id}/analyze-reflection
Content-Type: application/json

{
    "taskName": str,       # タスク名
    "content": str,        # 振り返り内容
    "session_id": str,     # セッションID
    "created_at": datetime # 作成日時
}

Response: {
    "patterns": [
        {
            "pattern": str,      # パターン名
            "category": str,     # カテゴリ
            "confidence": float, # 確信度
            "context": str,      # 検出された文脈
            "examples": [str]    # 例
        }
    ]
}
```

#### ユーザー固有の指示取得
```http
GET /api/v1/profiles/{user_id}/instructions/{role}

Response: {
    "instructions": str  # カスタマイズされた指示
}

Error Responses:
- 404: 指定された役割が存在しない場合
- 404: プロファイルが存在しない場合
- 403: 他のユーザーのプロファイルにアクセスしようとした場合
```

### エージェント操作

#### エージェントの実行(同期)
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

#### エージェントの実行(ストリーミング)
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
```

## テスト実行

```bash
# すべてのテストを実行
pytest

# 特定のテストを実行
pytest tests/test_profile_agent.py -v  # プロファイル管理APIテスト
pytest tests/test_reflection_api.py -v  # 振り返り機能テスト

# テストカバレッジレポートの生成
pytest --cov=.