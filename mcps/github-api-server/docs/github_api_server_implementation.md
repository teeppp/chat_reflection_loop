# GitHub API MCPサーバーの実装メモ

## 実装内容

### 1. 基本構成
- MCPサーバーとして`@modelcontextprotocol/sdk`を使用
- GitHub APIとの通信に`@octokit/graphql`を使用
- ESModuleとして実装（`type: "module"`を使用）

### 2. 提供するツール

#### 2.1 基本機能
- `get_repo_info`: リポジトリの基本情報を取得するツール
  - 入力パラメータ:
    - owner: リポジトリのオーナー名（必須）
    - repo: リポジトリ名（必須）
  - 取得情報:
    - リポジトリ名
    - 説明
    - URL
    - スター数
    - フォーク数
    - イシュー数
    - プルリクエスト数

#### 2.2 Scrum開発管理機能
- `create_project`: プロジェクトの作成
  - 入力パラメータ:
    - owner: オーナー名（必須）
    - title: プロジェクトタイトル（必須）
  - 注意点:
    - ownerIdの取得が必要（別途クエリを実行）

- `get_project`: プロジェクトの取得
  - 入力パラメータ:
    - owner: オーナー名（必須）
    - number: プロジェクト番号（必須）

- `create_project_field`: カスタムフィールドの作成
  - 入力パラメータ:
    - projectId: プロジェクトID（必須）
    - name: フィールド名（必須）
    - dataType: データ型（必須）
    - options: SINGLE_SELECT用のオプション
      - name: オプション名（必須）
      - color: 色（必須）
      - description: 説明（必須）

- `create_issue`: タスクの作成
  - 入力パラメータ:
    - owner: オーナー名（必須）
    - repo: リポジトリ名（必須）
    - title: タイトル（必須）
    - body: 本文
    - labels: ラベル配列

- `update_issue`: タスクの更新
  - 入力パラメータ:
    - owner: オーナー名（必須）
    - repo: リポジトリ名（必須）
    - number: イシュー番号（必須）
    - title: 新しいタイトル
    - body: 新しい本文
    - state: 状態（OPEN/CLOSED）

- `get_issue`: タスクの取得
  - 入力パラメータ:
    - owner: オーナー名（必須）
    - repo: リポジトリ名（必須）
    - number: イシュー番号（必須）

- `list_project_items`: プロジェクト内のタスク一覧取得
  - 入力パラメータ:
    - projectId: プロジェクトID（必須）

### 3. エラーハンドリング
- 不正なツール名のチェック
- 必須パラメータの存在チェック
- GitHub APIエラーのハンドリング
- エラーメッセージのログ出力

### 4. ログ機能
- ログディレクトリ: `logs/`
- ログファイル: `mcp-server.log`
- タイムスタンプ付きでログを記録
- 主要な操作とエラーをログに記録

## 実装時の注意点

### 1. 環境変数
- 環境変数は`cline_mcp_settings.json`から自動的に渡される
- dotenvは不要（削除）

### 2. モジュール解決
- ESModuleのパス解決に注意
- `tsconfig.json`の設定:
  - `"module": "ESNext"`
  - `"moduleResolution": "node"`
  - `"type": "module"`をpackage.jsonに設定

### 3. MCPサーバーの起動
- `StdioServerTransport`を使用してサーバーを起動
- 標準入出力を使用してClineとの通信を行う

### 4. 型定義
- `CallToolRequest`インターフェースの適切な定義
- リクエストパラメータの型チェック
- GraphQLのフラグメントと型定義の注意点:
  ```typescript
  // 基本インターフェース
  interface ProjectV2FieldBase {
    id: string;
    name: string;
  }

  // 通常フィールド
  interface ProjectV2Field extends ProjectV2FieldBase {
    dataType: string;
  }

  // 選択フィールド
  interface ProjectV2SingleSelectField extends ProjectV2FieldBase {
    options: Array<{
      id: string;
      name: string;
    }>;
  }
  ```

### 5. 実行パス
- ~/.vscode-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.jsonコマンドをnodeのフルパスに指定しないと起動エラー

```json
{
  "mcpServers": {
    "github": {
      "command": "/root/.nvm/versions/node/v22.13.0/bin/node",
      "args": [
        "/home/ubuntu/workspace/google_cloud_llm_hackathons/mcps/github-api-server/build/index.js"
      ],
      "env": {
        "GITHUB_TOKEN": "${GITHIB_TOKEN}"
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```


### 6. GraphQL APIの注意点
1. プロジェクト作成時のownerIdの取得
   ```graphql
   query($login: String!) {
     user(login: $login) {
       id
     }
   }
   ```

2. SINGLE_SELECTフィールドのオプション設定
   - 必須項目:
     - name: オプション名
     - color: 色（例：GREEN, BLUE, RED）
     - description: 説明文
   - すべての項目が必須（1つでも欠けるとエラー）

3. フィールドの型に応じたフラグメントの使用
   ```graphql
   ... on ProjectV2Field {
     id
     name
     dataType
   }
   ... on ProjectV2SingleSelectField {
     id
     name
     options {
       id
       name
     }
   }
   ```

## デバッグ方法

1. MCPインスペクターを使用
   ```bash
   npx @modelcontextprotocol/inspector build/index.js
   ```

2. ログファイルの確認
   ```bash
   cat logs/mcp-server.log
   ```

## 動作確認のポイント

1. サーバーの起動確認
   - 正常に起動されているか
   - エラーメッセージがないか

2. ツールの実行確認
   - パラメータの受け渡しが正しく行われているか
   - レスポンスが期待通りの形式で返ってくるか

3. エラーケースの確認
   - 不正なパラメータでのエラーハンドリング
   - GitHub API認証エラーの処理

4. Scrum開発機能の確認
   - プロジェクトの作成と設定
   - カスタムフィールドの追加
   - タスクの作成と更新
   - プロジェクトボードの表示

## Scrum開発用フィールド設定

### 1. デフォルトフィールド
- Title（タイトル）
- Assignees（担当者）
- Status（ステータス）
  - Todo
  - In Progress
  - Done
- Labels（ラベル）
- Linked pull requests（関連PR）
- Milestone（マイルストーン）
- Repository（リポジトリ）
- Reviewers（レビュアー）

### 2. カスタムフィールド
- Story Points（ストーリーポイント）
  - 型: NUMBER
  - 用途: タスクの規模を数値で表現

- Sprint（スプリント）
  - 型: SINGLE_SELECT
  - オプション:
    ```typescript
    [
      {
        name: "Sprint 1",
        color: "GREEN",
        description: "First sprint"
      },
      {
        name: "Sprint 2",
        color: "BLUE",
        description: "Second sprint"
      },
      {
        name: "Sprint 3",
        color: "PURPLE",
        description: "Third sprint"
      },
      {
        name: "Backlog",
        color: "GRAY",
        description: "Product backlog items"
      }
    ]
    ```

## 改善点

1. エラーメッセージの詳細化
2. レスポンスデータの型定義の強化
3. ユニットテストの追加
4. より多くのGitHub API機能のサポート
5. プロジェクトフィールドの更新機能の追加
6. バッチ処理による複数タスクの一括更新
7. カスタムフィールドのバリデーション強化

## 今回の実装で苦労した点

### 1. GraphQL APIの型定義
- `convertProjectV2DraftIssueItemToIssue` のレスポンスの型定義が複雑で、何度も修正が必要でした。
- `projectItem` フィールドが存在しない、`contentId` が存在しないなど、GraphQLのスキーマと型定義のずれが原因でした。
- https://docs.github.com/ja/graphql/reference/mutationsにGraphQLの仕様が書かれているので参照するとよい

### 2. `convert_project_item_to_issue` ツールの利用
- すでにIssueに変換されたアイテムを再度変換しようとするとエラーが発生することがわかりました。
- アイテムがIssueかどうかを事前に確認する必要がありました。

