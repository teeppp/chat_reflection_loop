# github-api-server MCP サーバー

GitHub APIと対話するためのModel Context Protocolサーバーです。

これは、GitHub APIとのさまざまなインタラクションを実装するTypeScriptベースのMCPサーバーで、特にプロジェクトとイシューに焦点を当てています。

## 機能

### ツール

- `create_project`: 新しいGitHubプロジェクトを作成します
  - `owner`（組織またはユーザー名）と`title`（プロジェクトタイトル）を必須パラメータとして受け取ります。
- `get_project`: GitHubプロジェクトの情報を取得します
  - `owner`（組織またはユーザー名）と`number`（プロジェクト番号）を必須パラメータとして受け取ります。
- `create_project_field`: GitHubプロジェクトにカスタムフィールドを作成します
  - `projectId`（プロジェクトノードID）、`name`（フィールド名）、`dataType`（フィールドデータ型：TEXT、NUMBER、DATE、SINGLE_SELECT）を必須パラメータとして受け取ります。
  - `SINGLE_SELECT`フィールドの場合、`options`（`name`、`color`、`description`を持つオプションオブジェクトの配列）も必須です。
- `create_issue`: リポジトリに新しいイシューを作成します
  - `owner`（リポジトリの所有者）、`repo`（リポジトリ名）、`title`（イシューのタイトル）を必須パラメータとして受け取ります。
  - `body`（イシューの本文）と`labels`（イシューラベルの配列）はオプションパラメータです。
- `update_issue`: 既存のイシューを更新します
  - `owner`（リポジトリの所有者）、`repo`（リポジトリ名）、`number`（イシュー番号）を必須パラメータとして受け取ります。
  - `title`（新しいイシューのタイトル）、`body`（新しいイシューの本文）、`state`（イシューの状態：OPENまたはCLOSED）はオプションパラメータです。
- `get_issue`: イシューの情報を取得します
  - `owner`（リポジトリの所有者）、`repo`（リポジトリ名）、`number`（イシュー番号）を必須パラメータとして受け取ります。
- `list_project_items`: プロジェクト内のすべてのアイテムをリストします
  - `projectId`（プロジェクトノードID）を必須パラメータとして受け取ります。
- `create_project_item`: GitHubプロジェクトに新しいアイテムを作成します
  - `projectId`（プロジェクトノードID）を必須パラメータとして受け取ります。
  - `contentId`（イシューノードID）はオプションパラメータです。提供されない場合、`title`（アイテムタイトル）が必須です。
- `convert_project_item_to_issue`: プロジェクトアイテムをイシューに変換します
  - `projectId`（プロジェクトノードID）、`itemId`（プロジェクトアイテムノードID）、`owner`（リポジトリの所有者）、`repo`（リポジトリ名）を必須パラメータとして受け取ります。

## 開発

依存関係をインストールします。
```bash
npm install
```

サーバーをビルドします。
```bash
npm run build
```

自動リビルドで開発するには:
```bash
npm run watch
```

## インストール

Claudeデスクトップで使用するには、サーバー構成を追加します。

macOSの場合: `~/Library/Application Support/Claude/claude_desktop_config.json`
Windowsの場合: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "github-api-server": {
      "command": "/path/to/github-api-server/build/index.js",
       "env": {
          "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN"
      }
    }
  }
}
```
**重要**: `GITHUB_TOKEN` を環境変数に設定してください。

### デバッグ

MCPサーバーはstdioを介して通信するため、デバッグは難しい場合があります。 [MCP Inspector](https://github.com/modelcontextprotocol/inspector)を使用することをお勧めします。これは、パッケージスクリプトとして利用できます。

```bash
npm run inspector
```

Inspectorは、ブラウザでデバッグツールにアクセスするためのURLを提供します。
