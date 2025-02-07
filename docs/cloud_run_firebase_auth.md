# Cloud RunでFirebase Authenticationを利用するための設定手順

## 概要

このドキュメントでは、Cloud RunでFirebase Authenticationを利用するための設定手順について説明します。Firebase Authenticationを使用することで、Cloud Runサービスへのアクセスを認証されたユーザーのみに制限することができます。

また、API Gateway を使用することで、認証・認可の処理を一元化し、バックエンドサービスをよりセキュアに保護することができます。API Gateway は、Firebase Authentication の JWT トークンを検証し、認証されたリクエストのみを Cloud Run サービスに転送します。

## 前提条件

*   Google Cloud Platform (GCP) プロジェクトが作成済みであること
*   Firebaseプロジェクトが作成済みであること
*   Cloud Runサービスがデプロイ済みであること
*   Terraformまたはgcloud CLIがインストール済みであること

## 設定手順

### 0. Firebaseプロジェクトの作成 (CLI)

1.  Google Cloud Platformプロジェクトを作成します。
    ```bash
    gcloud projects create PROJECT_ID --name="Project Display Name"
    ```
    *   `PROJECT_ID` は、作成するプロジェクトのIDを指定します。
    *   `Project Display Name` は、プロジェクトの表示名を指定します。
2.  Firebaseプロジェクトを有効にします。
    ```bash
    gcloud firebase projects:add PROJECT_ID
    ```
    *   `PROJECT_ID` は、作成したプロジェクトのIDを指定します。
3.  Firebase Authenticationを有効にします。
    ```bash
    gcloud services enable identitytoolkit.googleapis.com --project=PROJECT_ID
    ```
    *   `PROJECT_ID` は、作成したプロジェクトのIDを指定します。

### 1. Firebase Authenticationの設定 (Terraform)

1.  Terraformの設定ファイル (`main.tf` など) に、以下の内容を追加します。
    ```terraform
    terraform {
      required_providers {
        google-beta = {
          source  = "hashicorp/google-beta"
          version = "~> 5.0"
        }
      }
    }

    provider "google-beta" {
      user_project_override = true
    }

    provider "google-beta" {
      alias = "no_user_project_override"
      user_project_override = false
    }

    resource "google_project" "default" {
      provider   = google-beta.no_user_project_override
      name       = "Project Display Name"
      project_id = "project-id-for-new-project"
      billing_account = "000000-000000-000000"
      labels = {
        "firebase" = "enabled"
      }
    }

    resource "google_project_service" "default" {
      provider = google-beta.no_user_project_override
      project  = google_project.default.project_id
      for_each = toset([
        "cloudbilling.googleapis.com",
        "cloudresourcemanager.googleapis.com",
        "firebase.googleapis.com",
        "identitytoolkit.googleapis.com",
        "serviceusage.googleapis.com",
      ])
      service = each.key
      disable_on_destroy = false
    }

    resource "google_firebase_project" "default" {
      provider = google-beta
      project  = google_project.default.project_id
      depends_on = [
        google_project_service.default
      ]
    }

    resource "google_identity_platform_config" "default" {
      provider = google-beta
      project  = google_project.default.project_id

      sign_in {
        email {
          enabled = true
        }
        anonymous {
          enabled = true
        }
      }
      depends_on = [
        google_firebase_project.default
      ]
    }
    ```
    *   `YOUR_PROJECT_ID` は、Firebaseコンソールで確認できる値を設定してください。
    *   `YOUR_BILLING_ACCOUNT` は、Google Cloud Platformの課金アカウントIDを設定してください。
2.  Terraformコマンドを実行し、Firebase Authenticationを有効にします。
    ```bash
    terraform init
    terraform apply
    ```

### 2. Cloud Runサービスの設定

1.  Cloud Runサービスで、Firebase Authentication SDKをインストールします。
    ```bash
    npm install firebase
    ```
2.  Cloud Runサービスのコードで、Firebase Authentication SDKを初期化します。
    ```javascript
    import { initializeApp } from 'firebase/app';
    import { getAuth } from 'firebase/auth';

    const firebaseConfig = {
      apiKey: "YOUR_API_KEY",
      authDomain: "YOUR_AUTH_DOMAIN",
      projectId: "YOUR_PROJECT_ID",
      storageBucket: "YOUR_STORAGE_BUCKET",
      messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
      appId: "YOUR_APP_ID"
    };

    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    ```
    *   `YOUR_API_KEY`, `YOUR_AUTH_DOMAIN`, `YOUR_PROJECT_ID`, `YOUR_STORAGE_BUCKET`, `YOUR_MESSAGING_SENDER_ID`, `YOUR_APP_ID` は、Firebaseコンソールで確認できる値を設定してください。
3.  Cloud Runサービスで、ユーザーを認証する処理を実装します。
    ```javascript
    import { signInWithEmailAndPassword } from "firebase/auth";

    signInWithEmailAndPassword(auth, email, password)
      .then((userCredential) => {
        // Signed in
        const user = userCredential.user;
        // ...
      })
      .catch((error) => {
        const errorCode = error.code;
        const errorMessage = error.message;
      });
    ```
4.  Cloud Runサービスで、認証されたユーザーのIDトークンを検証する処理を実装します。
    ```javascript
    import { getAuth, onAuthStateChanged } from "firebase/auth";

    onAuthStateChanged(auth, (user) => {
      if (user) {
        user.getIdToken().then((idToken) => {
          // Send idToken to your backend
        });
      } else {
        // User is signed out
      }
    });
    ```
5.  Cloud Runサービスで、認証されたユーザーのアクセスを制御する処理を実装します。
    *   例えば、認証されたユーザーのみが特定のAPIエンドポイントにアクセスできるように設定します。

### 3. API Gateway の設定

1.  API Gateway の設定を Terraform に追加します。
    ```terraform
    resource "google_api_gateway_api" "default" {
      provider = google-beta
      api_id   = "backend-api"
      project  = var.project_id
    }

    resource "google_api_gateway_api_config" "default" {
      provider = google-beta
      api      = google_api_gateway_api.default.api_id
      api_config_id = "backend-api-config"

      gateway_config {
        backend_config {
          google_service_account = google_service_account.service_account.email
        }
      }

      openapi_documents {
        document {
          path = "openapi.yaml"
          contents = base64encode(templatefile("${path.module}/openapi.yaml", {
            backend_url = google_cloud_run_service.default.status[0].url
          }))
        }
      }
    }

    resource "google_api_gateway_gateway" "default" {
      provider   = google-beta
      region     = var.region
      project    = var.project_id
      api_config = google_api_gateway_api_config.default.id
      gateway_id = "backend-gateway"
    }
    ```

2.  OpenAPI 仕様を定義します（`openapi.yaml`）。
    ```yaml
    swagger: "2.0"
    info:
      title: Backend API
      version: v1
    securityDefinitions:
      firebaseAuth:
        type: oauth2
        flow: implicit
        authorizationUrl: ""
        x-google-issuer: "https://securetoken.google.com/${project_id}"
        x-google-jwks_uri: "https://www.googleapis.com/service_accounts/v1/metadata/x509/securetoken@system.gserviceaccount.com"
        x-google-audiences: "${project_id}"
    paths:
      /:
        get:
          summary: Root endpoint
          operationId: getRoot
          security:
            - firebaseAuth: []
          x-google-backend:
            address: "${backend_url}"
          responses:
            200:
              description: Successful response
      /health:
        get:
          summary: Health check endpoint
          operationId: getHealth
          security:
            - firebaseAuth: []
          x-google-backend:
            address: "${backend_url}"
          responses:
            200:
              description: Successful response
    ```

3.  Terraform を適用して API Gateway をデプロイします。
    ```bash
    terraform init
    terraform apply
    ```

### 4. JWT トークンの取得と動作確認

1.  Firebase Authentication の JWT トークンを取得するスクリプトを作成します。
    ```javascript
    const firebase = require("firebase/app");
    const { getAuth, signInWithEmailAndPassword } = require("firebase/auth");

    const firebaseConfig = {
      apiKey: process.env.FIREBASE_API_KEY,
      authDomain: process.env.FIREBASE_AUTH_DOMAIN,
      projectId: process.env.FIREBASE_PROJECT_ID,
    };

    firebase.initializeApp(firebaseConfig);
    const auth = getAuth();

    async function getFirebaseJWT(email, password) {
      try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
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
    ```

2.  JWT トークンを取得し、API Gateway の動作を確認します。
    ```bash
    # .env ファイルを作成し、必要な環境変数を設定します
    # 例:
    # FIREBASE_API_KEY=your_api_key
    # FIREBASE_AUTH_DOMAIN=your_auth_domain
    # FIREBASE_PROJECT_ID=your_project_id
    # FIREBASE_USER_EMAIL=your_email
    # FIREBASE_USER_PASSWORD=your_password

    # JWT トークンを取得
    node scripts/get-firebase-jwt.js

    # API Gateway の動作確認
    curl -H "Authorization: Bearer <JWT>" https://<API_GATEWAY_URL>
    ```

### 5. Cloud Runサービスのデプロイ

1.  Cloud Runサービスをデプロイします。
2.  API Gateway を経由して Cloud Run サービスにアクセスし、Firebase Authentication が正しく機能することを確認します。

## 注意事項

### Firebase Authentication

*   Firebase Authentication with Identity Platformにアップグレードすると、追加機能が利用可能になりますが、料金体系が変更されるため、注意が必要です。
*   Cloud RunサービスでFirebase Authentication SDKを使用する際には、セキュリティに注意し、APIキーなどの機密情報を適切に管理してください。

### API Gateway

*   OpenAPI 仕様での注意点
    - `operationId` は必須であり、各エンドポイントで一意である必要があります。
    - `x-google-backend.address` には、Cloud Run サービスの URL を指定する必要があります。
    - Firebase Authentication の設定では、`x-google-issuer` と `x-google-jwks_uri` が正しく設定されていることを確認してください。

*   JWT トークンの検証
    - API Gateway は、リクエストヘッダーの `Authorization: Bearer <JWT>` を検証します。
    - JWT トークンは、Firebase Authentication が発行したものである必要があります。
    - JWT トークンの有効期限が切れていないことを確認してください。

*   エラーハンドリング
    - JWT トークンが不正な場合、API Gateway は 401 エラーを返します。
    - JWT トークンが期限切れの場合、新しいトークンを取得する必要があります。
    - バックエンドサービスが利用できない場合、適切なエラーメッセージを返すように設定してください。

*   パフォーマンス
    - API Gateway は、リクエストごとに JWT トークンを検証するため、若干のオーバーヘッドが発生します。
    - 必要に応じて、キャッシュやレート制限を設定することを検討してください。

*   セキュリティ
    - API Gateway の URL は公開されるため、適切なセキュリティ対策を講じてください。
    - Firebase Authentication の設定で、許可するドメインを適切に制限してください。
    - サービスアカウントの権限は、必要最小限に設定してください。

## 参考資料

*   [Cloud Runのドキュメント](https://cloud.google.com/run/docs)
*   [Firebase Authenticationのドキュメント](https://firebase.google.com/docs/auth)
*   [TerraformとFirebaseのドキュメント](https://firebase.google.com/docs/projects/terraform/get-started)