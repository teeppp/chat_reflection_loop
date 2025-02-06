#!/bin/bash

# デプロイ用ビルドスクリプト
echo "Starting deployment build process..."

# Flutter webビルドを実行
echo "Building Flutter web app for deployment..."
flutter clean
flutter pub get
flutter build web --release

# Firebase Hostingにデプロイ
echo "Deploying to Firebase Hosting..."
firebase deploy --only hosting

echo "Deployment complete! Check the Firebase console for details."