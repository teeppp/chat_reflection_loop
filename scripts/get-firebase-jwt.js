#!/usr/bin/env node
// Firebase v9+ のモジュラーSDKを使用する例
const dotenv = require('dotenv');
dotenv.config({ path: './.env' });
const { initializeApp } = require("firebase/app");
const { getAuth, signInWithEmailAndPassword } = require("firebase/auth");

const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY,
  authDomain: process.env.FIREBASE_AUTH_DOMAIN,
  projectId: process.env.FIREBASE_PROJECT_ID,
};

// アプリを初期化
const app = initializeApp(firebaseConfig);

// 認証を取得
const auth = getAuth(app);

async function getFirebaseJWT(email, password) {
  try {
    // メールアドレスとパスワードでサインイン
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;
    // JWT(IDトークン)を取得
    const idToken = await user.getIdToken(true);
    console.log("JWT:", idToken);
  } catch (error) {
    console.error("Error signing in:", error);
  }
}

const email = process.env.FIREBASE_USER_EMAIL;
const password = process.env.FIREBASE_USER_PASSWORD;

if (!email || !password) {
  console.error("Please set FIREBASE_USER_EMAIL and FIREBASE_USER_PASSWORD environment variables.");
  process.exit(1);
}

getFirebaseJWT(email, password);
