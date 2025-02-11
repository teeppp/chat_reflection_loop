# フロントエンドアプリケーション

Flutter Webで実装されたフロントエンドアプリケーションです。Firebase Authenticationを使用したユーザー認証と、バックエンドAPIとの連携機能を提供します。

## 構成

- `flutter_web_app/`: メインのFlutterアプリケーション
  - `lib/`: アプリケーションのソースコード
  - `web/`: Web固有の設定とアセット
  - `scripts/`: 開発・デプロイ用スクリプト

## 開発環境のセットアップ

### 1. 環境変数の設定

```bash
# .envファイルの作成
cd flutter_web_app
cp .env.sample .env

# .envファイルを編集して必要な設定を追加
vi .env
```

必要な環境変数：
- `FIREBASE_API_KEY`: Firebase Web APIキー
- `FIREBASE_AUTH_DOMAIN`: Firebase認証ドメイン
- `FIREBASE_PROJECT_ID`: Firebaseプロジェクトのプロジェクトグループ
- `FIREBASE_APP_ID`: FirebaseアプリケーションID
- `API_BASE_URL`: バックエンドAPIのベースURL

### 2. ローカル開発サーバーの起動

```bash
cd flutter_web_app/scripts
chmod +x serve_local.sh
./serve_local.sh
```

アプリケーションは http://localhost:12345 で利用可能になります。

## Firebase Hostingへのデプロイ

### 1. デプロイの準備

```bash
cd flutter_web_app/scripts
chmod +x build_web.sh
```

### 2. デプロイの実行

```bash
# ビルドとデプロイの実行
./build_web.sh
```

デプロイが成功すると、以下のURLでアプリケーションにアクセスできます：
https://ringed-codex-447303-q3.web.app

## Androidアプリのビルド

### 1. ビルドの準備

```bash
cd flutter_web_app/scripts
chmod +x build_android.sh
```

### 2. ビルドの実行

```bash
# Androidビルドの実行
./build_android.sh
```

ビルドが成功すると、以下の場所にAPKファイルが生成されます：
```
build/app/outputs/flutter-apk/app-release.apk
```

## 設定ファイルの管理

アプリケーションの設定は、Web版とAndroid版で異なる方法で管理されています：

### Web版（開発環境・本番環境）
1. 環境変数（.envファイル）
   - 機密情報（APIキーなど）は.envファイルで管理
   - Gitリポジトリにはコミットせず、.env.sampleで例を提供
   - .envファイルは.gitignoreに含まれており、Gitで追跡されません
2. 設定ファイル
   - 各スクリプトが.envから自動的に設定ファイルを生成
   - パス: `assets/config/config.json`

### Android版
1. 設定ファイル
   - パス: `android/app/src/main/assets/config.json`
   - サンプル: `android/app/src/main/assets/config.json.sample`
   - Web版とは別の設定ファイルを使用（Firebase Consoleで異なるアプリとして登録）
   - 直接config.jsonを編集して使用

### 開発時の注意点

1. Web開発
   - 新しい環境変数を追加する場合は、.env.sampleも更新してください
   - ローカル開発時は`serve_local.sh`を使用（.envから設定を生成）
   - デプロイ時は`build_web.sh`を使用（.envから設定を生成）

2. Android開発
   - config.json.sampleをコピーしてconfig.jsonを作成
   - 必要な設定値を直接config.jsonに記述
   - ビルド時は`build_android.sh`を使用

## トラブルシューティング

### よくある問題と解決方法

1. 「環境変数が設定されていない」エラー
   - .envファイルが正しく配置されているか確認
   - 必要な環境変数がすべて設定されているか確認

2. ビルドエラー
   - `flutter clean`を実行してから再度ビルド
   - パッケージの依存関係を更新（`flutter pub get`）

3. デプロイエラー
   - Firebase CLIが正しく設定されているか確認
   - 環境変数が正しくエクスポートされているか確認

4. Androidビルドエラー
   - Android SDKが正しく設定されているか確認
   - `flutter doctor`でAndroid開発環境を確認
   - google-services.jsonが正しく配置されているか確認