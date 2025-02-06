#!/bin/bash

# ローカル開発用サーバー起動スクリプト
echo "Starting local development server..."

# プロジェクトのルートディレクトリに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit

# .envファイルが存在するか確認
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please create one from .env.sample"
    exit 1
fi

# .envファイルから環境変数を読み込む
set -a
source ".env"
set +a

# 設定ファイルを生成
echo "Generating development configuration..."
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

# Flutter開発サーバーを起動
echo "Starting Flutter development server..."
flutter run -d web-server --web-port 12345