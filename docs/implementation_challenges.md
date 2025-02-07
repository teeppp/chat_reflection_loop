# 実装上の課題

## Google Cloud API Gateway の SSE サポート調査

### 課題

*   Google Cloud API Gateway が SSE を直接サポートしていないため、代替技術を検討する必要があった。
*   API Gateway のドキュメントが SSE サポートについて明確に言及していなかったため、調査に時間がかかった。

### 根本原因

*   API Gateway は、リクエスト/レスポンスモデルに特化しており、サーバープッシュ型のストリーミングをサポートしていない。
*   ドキュメントが、SSE のような特定の技術のサポート状況について詳細に記述していなかった。

### 解決策

*   Apigee を代替技術として検討し、ストリーミング処理をサポートできることを確認した。
*   WebSocket を代替技術として検討し、双方向通信をサポートできることを確認した。
*   Terraform を用いて、Apigee, Cloud Run, Cloud IAM, Firebase Authentication の連携を IaC で構築できることを確認した。

## ドキュメントの取得

### 課題

*   `web-scraper` ツールで Terraform のドキュメントを取得できなかった。

### 根本原因

*   Terraform のドキュメントが JavaScript を使用して動的に生成されているため、`web-scraper` ツールでは内容を取得できなかった。

### 解決策

*   `tavily` ツールを使用して、Terraform のドキュメントに関する情報を検索し、補完した。

## 今後の改善点

*   API Gateway のドキュメントをより詳細に調査し、SSE のサポート状況を明確にする。
*   `web-scraper` ツールで JavaScript を使用した動的なコンテンツを取得できるように改善する。
*   `tavily` ツールで取得した情報を、より構造化された形式でドキュメントに反映できるようにする。

## Tavily qna_search ツールの実装

### 課題

*   `qna_search` ツールに `raw_content` オプションを追加しようとしたが、Tavily API の `qna_search` メソッドが `include_raw_content` 引数をサポートしていなかった。
*   `taivily_client.py` と `server.py` を修正する際に、Pylance エラーやその他のエラーが発生し、修正に時間がかかった。
*   `apply_diff` ツールが失敗した場合、`read_file` ツールでファイルの内容を再確認し、正しい diff を適用する必要があることを理解するのに時間がかかった。