#!/bin/bash

# デプロイ用ビルドスクリプト
echo "Starting deployment build process..."

# プロジェクトのルートディレクトリに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit

# 環境変数が設定されているか確認
required_vars=(
    "FIREBASE_API_KEY"
    "FIREBASE_AUTH_DOMAIN"
    "FIREBASE_PROJECT_ID"
    "FIREBASE_APP_ID"
    "API_BASE_URL"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set"
        exit 1
    fi
done

# 設定ファイルを生成
echo "Generating runtime configuration..."
cat > web/config.js << EOF
window.runtimeConfig = {
    firebase: {
        apiKey: "${FIREBASE_API_KEY}",
        authDomain: "${FIREBASE_AUTH_DOMAIN}",
        projectId: "${FIREBASE_PROJECT_ID}",
        storageBucket: "${FIREBASE_PROJECT_ID}.appspot.com",
        messagingSenderId: "${FIREBASE_MESSAGING_SENDER_ID:-}",
        appId: "${FIREBASE_APP_ID}",
        measurementId: "${FIREBASE_MEASUREMENT_ID:-}"
    },
    api: {
        baseUrl: "${API_BASE_URL}"
    }
};
EOF

# Flutter webビルドを実行
echo "Building Flutter web app for deployment..."
flutter clean
flutter pub get
flutter build web --release

# 生成した設定ファイルをビルドディレクトリにコピー
cp web/config.js build/web/

# Firebase Hostingにデプロイ
echo "Deploying to Firebase Hosting..."
firebase deploy --only hosting

echo "Deployment complete! Check the Firebase console for details."