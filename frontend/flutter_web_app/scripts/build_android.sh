#!/bin/bash

# Android用ビルドスクリプト
echo "Starting Android build process..."

# プロジェクトのルートディレクトリに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit

# Flutterビルドを実行
echo "Building Android app..."
flutter clean
flutter pub get
flutter build apk --release

echo "Android build complete! APK location: build/app/outputs/flutter-apk/app-release.apk"