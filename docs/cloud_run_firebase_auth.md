# Cloud RunでFirebase Authenticationを利用するための設定手順

## 概要

このドキュメントでは、Cloud RunでFirebase Authenticationを利用するための設定手順について説明します。Firebase Authenticationを使用することで、Cloud Runサービスへのアクセスを認証されたユーザーのみに制限することができます。

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

### 3. Cloud Runサービスのデプロイ

1.  Cloud Runサービスをデプロイします。
2.  Cloud Runサービスにアクセスし、Firebase Authenticationが正しく機能することを確認します。

## 注意事項

*   Firebase Authentication with Identity Platformにアップグレードすると、追加機能が利用可能になりますが、料金体系が変更されるため、注意が必要です。
*   Cloud RunサービスでFirebase Authentication SDKを使用する際には、セキュリティに注意し、APIキーなどの機密情報を適切に管理してください。

## 参考資料

*   [Cloud Runのドキュメント](https://cloud.google.com/run/docs)
*   [Firebase Authenticationのドキュメント](https://firebase.google.com/docs/auth)
*   [TerraformとFirebaseのドキュメント](https://firebase.google.com/docs/projects/terraform/get-started)