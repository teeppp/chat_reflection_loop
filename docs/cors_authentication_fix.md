# CORS認証の問題解決策

## 現状の問題

FlutterアプリケーションからのPreFlight（OPTIONS）リクエストが401エラーで失敗する問題が発生しています。

### 問題の原因

1. **ミドルウェアの実行順序の問題**
   - 認証ミドルウェア（`authenticate_requests`）がCORSミドルウェアより先に実行される
   - PreFlightリクエストも認証チェックの対象となってしまう

2. **OPTIONSハンドラーの位置**
   - OPTIONSハンドラーが認証チェックの後に実行される
   - PreFlightリクエストが認証チェックで失敗する

## 解決策

### 1. PreFlightリクエストの認証除外

`authenticate_requests`ミドルウェアを以下のように修正します：

```python
@app.middleware("http")
async def authenticate_requests(request: Request, call_next):
    # PreFlightリクエストと、docsへのアクセスは認証をスキップ
    if request.method == "OPTIONS" or request.url.path == "/docs" or request.url.path == "/openapi.json":
        return await call_next(request)
    
    try:
        await verify_firebase_token(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    
    return await call_next(request)
```

この修正により：
- OPTIONSメソッドのリクエストが認証をバイパス
- CORS PreFlightリクエストが正常に処理される
- セキュリティは維持される（実際のAPIリクエストは認証必須）

### 実装の注意点

1. コードの修正はCode modeで行う必要があります
2. 修正後、以下の動作を確認してください：
   - PreFlightリクエストが204を返すこと
   - 実際のAPIリクエストが正常に認証されること
   - CORSヘッダーが正しく設定されること

### セキュリティ上の考慮事項

- PreFlightリクエストの認証スキップは一般的なCORS実装として安全です
- 実際のAPIリクエストは引き続き認証が必要
- この修正により、APIのセキュリティレベルは低下しません