# 初期APIエンドポイント定義書 (優先度付き)
## 概要
- 有名なエージェントフレームワークLangGraphのAPIに合わせた形
- 不要と思うものは削除していく想定

## 優先度決定基準
- **高**: アプリケーションの基本的な機能を提供するエンドポイント。
- **中**: アプリケーションの主要な機能に関連するが、必須ではないエンドポイント。
- **低**: アプリケーションの補助的な機能を提供するエンドポイント。

## アシスタント関連

### POST /assistants
- 説明: アシスタントの作成
- リクエストボディ: `AssistantCreate`
- レスポンスボディ: `Assistant`
- 優先度: 高

### POST /assistants/search
- 説明: アシスタントの検索
- リクエストボディ: `SearchRequest`
- レスポンスボディ: `Assistant` の配列
- 優先度: 中

### GET /assistants/{assistant_id}
- 説明: 特定のアシスタントの取得
- レスポンスボディ: `Assistant`
- 優先度: 高

### PUT /assistants/{assistant_id}
- 説明: 特定のアシスタントの更新 (または作成)
- リクエストボディ: `AssistantCreate`
- レスポンスボディ: `Assistant`
- 優先度: 中

### GET /assistants/{assistant_id}/graph
- 説明: 特定のアシスタントのグラフ構造の取得
- レスポンスボディ: オブジェクトの配列
- 優先度: 低

### GET /assistants/{assistant_id}/schemas
- 説明: 特定のアシスタントのスキーマの取得
- レスポンスボディ: `GraphSchema`
- 優先度: 低

## スレッド関連

### POST /threads
- 説明: スレッドの作成
- リクエストボディ: `ThreadCreate`
- レスポンスボディ: `Thread`
- 優先度: 高

### POST /threads/search
- 説明: スレッドの検索
- リクエストボディ: `SearchRequest`
- レスポンスボディ: `Thread` の配列
- 優先度: 中

### GET /threads/{thread_id}
- 説明: 特定のスレッドの取得
- レスポンスボディ: `Thread`
- 優先度: 高

### PUT /threads/{thread_id}
- 説明: 特定のスレッドの更新
- リクエストボディ: `ThreadCreate`
- レスポンスボディ: `Thread`
- 優先度: 中

### DELETE /threads/{thread_id}
- 説明: 特定のスレッドの削除
- レスポンスボディ: (空)
- 優先度: 低

### GET /threads/{thread_id}/state
- 説明: 特定のスレッドの現在の状態の取得
- レスポンスボディ: `ThreadState`
- 優先度: 高

### POST /threads/{thread_id}/state
- 説明: 特定のスレッドに状態を追加
- リクエストボディ: `ThreadStateUpdate`
- レスポンスボディ: `Config`
- 優先度: 中

### GET /threads/{thread_id}/history
- 説明: 特定のスレッドの過去の状態の取得 (中間処理の取得)
- レスポンスボディ: `ThreadState` の配列
- 優先度: 中

## 実行関連

### GET /threads/{thread_id}/runs
- 説明: 特定のスレッドの実行履歴の取得
- レスポンスボディ: `Run` の配列
- 優先度: 中

### POST /threads/{thread_id}/runs
- 説明: 特定のスレッドの実行
- リクエストボディ: `RunCreate`
- レスポンスボディ: `Run`
- 優先度: 高

### POST /threads/{thread_id}/runs/stream
- 説明: 特定のスレッドのストリーミング実行
- リクエストボディ: `RunStream`
- レスポンスボディ: ストリーミングレスポンス (SSE, JSON形式のイベント)
- 優先度: 高

### GET /threads/{thread_id}/runs/{run_id}
- 説明: 特定の実行の取得
- レスポンスボディ: `Run`
- 優先度: 中

### GET /threads/{thread_id}/runs/{run_id}/events
- 説明: 特定の実行のイベントの取得 (より詳細な中間処理の取得)
- レスポンスボディ: `RunEvent` の配列
- 優先度: 低


---
# 参考
- [LangGraphの定義](https://langchain-ai.github.io/langgraph-example/)