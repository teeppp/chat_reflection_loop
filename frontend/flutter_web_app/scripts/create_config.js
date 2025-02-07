#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

// .envファイルの読み込み
const envPath = path.resolve(__dirname, '../.env');
const result = dotenv.config({ path: envPath });

if (result.error) {
    console.error('Error loading .env file:', result.error);
    process.exit(1);
}

// 設定オブジェクトの作成
const config = {
    firebase: {
        apiKey: process.env.FIREBASE_API_KEY,
        authDomain: process.env.FIREBASE_AUTH_DOMAIN,
        projectId: process.env.FIREBASE_PROJECT_ID,
        storageBucket: `${process.env.FIREBASE_PROJECT_ID}.appspot.com`,
        messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
        appId: process.env.FIREBASE_APP_ID,
        measurementId: process.env.FIREBASE_MEASUREMENT_ID
    },
    api: {
        baseUrl: process.env.API_BASE_URL
    }
};

// 必須パラメータの確認
const requiredParams = [
    'FIREBASE_API_KEY',
    'FIREBASE_AUTH_DOMAIN',
    'FIREBASE_PROJECT_ID',
    'FIREBASE_APP_ID',
    'API_BASE_URL'
];

const missingParams = requiredParams.filter(param => !process.env[param]);
if (missingParams.length > 0) {
    console.error('Missing required environment variables:', missingParams.join(', '));
    process.exit(1);
}

// 設定ファイルの保存先ディレクトリの確認と作成
const configDir = path.resolve(__dirname, '../assets/config');
if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
}

// 開発環境用の設定ファイルを作成
const configPath = path.join(configDir, 'config_dev.json');
fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

console.log(`Configuration file created at: ${configPath}`);

// settings.jsonにファイルパスを追加（Flutterのassets設定用）
const settingsPath = path.resolve(__dirname, '../assets/config/settings.json');
const settings = {
    configPath: 'assets/config/config_dev.json'
};

fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
console.log(`Settings file created at: ${settingsPath}`);