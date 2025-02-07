#!/bin/bash

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Flutter Web App Test Script ===${NC}\n"

# 現在のディレクトリをチェック
if [ ! -f "pubspec.yaml" ]; then
    echo -e "${RED}Error: pubspec.yaml not found.${NC}"
    echo "Please run this script from the flutter_web_app directory."
    exit 1
fi

# 環境変数の設定
echo -e "${YELLOW}Setting up test environment...${NC}"
if [ ! -f ".env.test" ]; then
    echo -e "${RED}Error: .env.test file not found.${NC}"
    exit 1
fi

cp .env.test .env
echo -e "${GREEN}Test environment configured.${NC}\n"

# 依存関係のクリーンアップとインストール
echo -e "${YELLOW}Cleaning up and installing dependencies...${NC}"
flutter clean
flutter pub cache repair
flutter pub get

echo -e "${GREEN}Dependencies installed.${NC}\n"

# Webアプリの起動
echo -e "${YELLOW}Starting Web application...${NC}"
echo -e "The application will be available at ${GREEN}http://localhost:3000${NC}\n"

echo -e "${YELLOW}Test Scenarios:${NC}"
echo -e "1. User Registration Test
   - Click 'アカウントをお持ちでない方はこちら'
   - Enter email: test@example.com
   - Enter password: testpass123
   - Click 'アカウント作成'
   - Expected: Redirect to home screen

2. Login Test
   - Enter email: test@example.com
   - Enter password: testpass123
   - Click 'ログイン'
   - Expected: Redirect to home screen

3. JWT Token Test
   - After login, check token display on home screen
   - Compare with token from scripts/get-firebase-jwt.js

4. Logout Test
   - Click logout button
   - Expected: Redirect to login screen
   - Refresh browser
   - Expected: Stay on login screen

5. Error Cases
   - Try invalid email format
   - Try short password
   - Try non-matching passwords
   - Try non-existent user
   - Try wrong password\n"

echo -e "${YELLOW}Starting server...${NC}"
flutter run -d web-server --web-port=3000

# Clean up
echo -e "\n${YELLOW}Cleaning up...${NC}"
rm .env
cp .env.sample .env

echo -e "${GREEN}Test complete.${NC}"