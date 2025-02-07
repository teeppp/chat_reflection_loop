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
OPENAI_API_KEY=<your_openai_api_key>
GOOGLE_API_KEY=<your_google_api_key>
ANTHROPIC_API_KEY=<your_anthropic_api_key>
DEEPSEEK_API_KEY=<your_deepseek_api_key>
GITHUB_TOKEN=<your_github_token>
TAVILY_API_KEY=<your_tavily_key>
LOGFIRE_TOKEN=<your_logfire_token>
SONNET35V2_DEPLOYMENTNAME=anthropic.claude-3-5-sonnet-20241022-v2:0
HAIKU35_DEPLOYMENTNAME=anthropic.claude-3-5-haiku-20241022-v1:0

# Google Cloud Service Account
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/<your_google_cloud_service_account_key>.json
```

2. Google Cloud Consoleからサービスアカウントキー（JSON形式）をダウンロードし、`credentials`ディレクトリに配置します。

## データモデル

### Message
```python
{
    "role": str,          # メッセージの役割（user/assistant/system）
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
    "raw_messages": bytes,    # PydanticAI用の生の履歴
    "created_at": datetime,   # 作成日時
    "updated_at": datetime,   # 更新日時
    "title": Optional[str],   # チャットのタイトル(オプション)
    "reflection": Optional[dict] # 振り返り情報
}
```

### Pattern
```python
{
    "pattern": str,       # パターン名
    "category": str,      # カテゴリ
    "confidence": float,  # 確信度(0.0-1.0)
    "context": Union[PatternContext, List[str]], # パターンの検出コンテキスト
    "detected_at": datetime,  # 検出日時
    "detection_method": str,  # 検出方法
    "related_patterns": List[str], # 関連パターン
    "suggested_labels": List[str], # 提案ラベル
    "metadata": Dict[str, Any]  # メタデータ
}
```

### DynamicLabel
```python
{
    "text": str,         # ラベルテキスト
    "confidence": float, # 確信度(0.0-1.0)
    "context": List[str], # 検出コンテキスト
    "first_seen": datetime, # 初回検出日時
    "last_seen": datetime,  # 最終検出日時
    "occurrence_count": int, # 出現回数
    "related_labels": List[str], # 関連ラベル
    "source_patterns": List[str], # 元となったパターン
    "metadata": Dict[str, Any],   # メタデータ
    "clusters": List[str]  # 所属クラスター
}
```

### LabelCluster
```python
{
    "cluster_id": str,   # クラスターID
    "theme": str,        # クラスターのテーマ
    "labels": List[str], # 含まれるラベル
    "strength": float,   # クラスターの強度(0.0-1.0)
    "center_point": Dict[str, float], # 中心点座標
    "radius": float,     # クラスターの半径
    "last_updated": datetime, # 最終更新日時
    "metadata": Dict[str, Any], # メタデータ
    "parent_cluster": Optional[str], # 親クラスター
    "subclusters": List[str]  # サブクラスター
}
```

### UserProfile
```python
{
    "user_id": str,      # ユーザーID
    "patterns": List[Pattern], # 検出されたパターン
    "labels": List[DynamicLabel], # 動的ラベル
    "clusters": List[LabelCluster], # ラベルクラスター
    "categories": List[DynamicCategory], # 動的カテゴリー
    "base_instructions": List[AgentInstruction], # 基本指示
    "personalized_instructions": Optional[str], # カスタマイズ指示
    "insights": Optional[ProfileInsightResult], # プロファイル分析結果
    "metadata": Dict[str, Any], # メタデータ
    "updated_at": datetime, # 更新日時
    "tendencies": List[UserTendency] # ユーザーの傾向
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

### 振り返り管理

#### 振り返りの生成
```http
POST /api/v1/reflections/generate
Content-Type: application/json

{
    "session_id": str,
    "user_id": Optional[str]
}

Response: {
    "reflection": {
        "content": str,
        "session_id": str,
        "created_at": datetime
    },
    "patterns": [Pattern],
    "updated_at": datetime
}
```

#### セッションの振り返り取得
```http
GET /api/v1/reflections/session/{session_id}

Response: {
    "reflection": {
        "content": str,
        "session_id": str,
        "created_at": datetime
    }
}
```

#### ユーザーの全振り返り取得
```http
GET /api/v1/reflections/user

Response: {
    "reflections": [
        {
            "content": str,
            "session_id": str,
            "created_at": datetime
        }
    ]
}
```

### プロファイル管理

#### プロファイル分析の実行
```http
POST /api/v1/profiles/{user_id}/analyze
Content-Type: application/json

{
    "content": Optional[str],  # 単一の振り返り内容
    "force_update": bool      # 全履歴の再分析フラグ
}

Response: {
    "status": "success",
    "message": str,
    "analyzed_count": int
}
```

#### プロファイル分析結果の取得
```http
GET /api/v1/profiles/{user_id}/analysis

Response: {
    "patterns": [Pattern],
    "labels": [{"text": str}],
    "clusters": [LabelCluster],
    "categorized": {
        "category": [Pattern]
    }
}
```

### エージェント操作

#### エージェントの実行(同期)
```http
POST /baseagent/invoke
Content-Type: application/json

{
    "message": "ユーザーメッセージ",
    "thread_id": Optional[str]
}

Response: {
    "response": "エージェントからの応答",
    "thread_id": str,
    "status": "success"
}
```

#### エージェントの実行(ストリーミング)
```http
POST /baseagent/stream
Content-Type: application/json

{
    "message": "ユーザーメッセージ",
    "thread_id": Optional[str]
}

Response: Server-Sent Events (SSE)
Event: message
Data: {"text": "ストリーミングテキスト"}

Event: history
Data: {"messages": [Message]}
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