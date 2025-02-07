"""プロファイルAPIのテスト"""
import os
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, UTC
import json
import jwt
from typing import Optional


# テスト設定
BASE_URL = "http://dev_backend:8080"
TIMEOUT = httpx.Timeout(30.0, connect=60.0)

def check_env_vars() -> Optional[str]:
    """必要な環境変数が設定されているか確認"""
    required_vars = [
        "FIREBASE_API_KEY",
        "FIREBASE_USER_EMAIL",
        "FIREBASE_USER_PASSWORD"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        return f"Missing environment variables: {', '.join(missing)}"
    return None

def skip_if_env_not_setup():
    """環境変数が設定されていない場合はテストをスキップ"""
    missing = check_env_vars()
    if missing:
        pytest.skip(missing)

@pytest_asyncio.fixture(scope="function")
async def test_user_id(auth_headers):
    """トークンからユーザーIDを取得"""
    token = auth_headers["Authorization"].split(" ")[1]
    decoded = jwt.decode(token, options={"verify_signature": False})
    return decoded["user_id"]

@pytest_asyncio.fixture(scope="function")
async def session_id(auth_headers):
    """テスト用のチャットセッションを作成"""
    print("\nDebug - Creating test session")
    print(f"Debug - Auth headers: {auth_headers}")
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        try:
            # 1. まずbaseagent/invokeを使用してLLMの応答を得る
            invoke_response = await client.post(
                "/baseagent/invoke",
                headers=auth_headers,
                json={
                    "message": "新しいWebアプリケーションの開発計画を立ててください",
                    "thread_id": None
                }
            )
            
            print(f"Debug - Invoke response: {invoke_response.status_code}")
            print(f"Debug - Response headers: {dict(invoke_response.headers)}")
            print(f"Debug - Response body: {invoke_response.text}")
            
            assert invoke_response.status_code == 200, \
                f"Failed to invoke agent. Status: {invoke_response.status_code}, Body: {invoke_response.text}"
            
            invoke_data = invoke_response.json()
            assert "response" in invoke_data, "Missing response in invoke data"
            
            # 2. 質問と回答のペアでチャット履歴を作成
            response = await client.post(
                "/api/v1/chat-histories",
                headers=auth_headers,
                json={
                    "initial_message": [
                        {
                            "role": "user",
                            "content": "新しいWebアプリケーションの開発計画を立ててください"
                        },
                        {
                            "role": "assistant",
                            "content": invoke_data["response"]
                        }
                    ]
                }
            )
            
            print(f"Debug - Create session response: {response.status_code}")
            print(f"Debug - Response headers: {dict(response.headers)}")
            print(f"Debug - Response body: {response.text}")
            
            assert response.status_code == 200, \
                f"Failed to create session. Status: {response.status_code}, Body: {response.text}"
            
            session_data = response.json()
            return session_data["session_id"]
            
        except httpx.RequestError as e:
            print(f"Debug - Request error: {str(e)}")
            raise

@pytest.mark.asyncio
@pytest.mark.dependency(name="auth_setup")
async def test_auth_setup():
    """認証設定のテスト"""
    skip_if_env_not_setup()
    env_vars = {
        "FIREBASE_API_KEY": os.getenv("FIREBASE_API_KEY", "")[:10] + "...",
        "FIREBASE_USER_EMAIL": os.getenv("FIREBASE_USER_EMAIL", ""),
        "BASE_URL": BASE_URL,
    }
    print("\nDebug - Environment setup:")
    for key, value in env_vars.items():
        print(f"  {key}: {value}")
    
    assert all(os.getenv(var) for var in ["FIREBASE_API_KEY", "FIREBASE_USER_EMAIL", "FIREBASE_USER_PASSWORD"])

@pytest.mark.asyncio
@pytest.mark.dependency(depends=["auth_setup"])
async def test_unauthorized_profile_access():
    """未認証アクセスのテスト"""
    print("\nDebug - Testing unauthorized profile access")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        response = await client.get(
            "/api/v1/profiles/test_user/instructions/code"
        )
        assert response.status_code == 401

@pytest.mark.asyncio
@pytest.mark.dependency(depends=["auth_setup"])
async def test_reflection_with_profile_update(auth_headers, session_id, test_user_id):
    """振り返り生成時のプロファイル更新テスト"""
    skip_if_env_not_setup()
    print("\nDebug - Testing reflection generation with profile update")
    print(f"Debug - Auth headers: {auth_headers}")
    print(f"Debug - Session ID: {session_id}")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                "/api/v1/reflections/generate",
                headers=auth_headers,
                json={"session_id": session_id}
            )
            
            print(f"Debug - Generate reflection response: {response.status_code}")
            print(f"Debug - Response headers: {dict(response.headers)}")
            print(f"Debug - Response body: {response.text}")
            
            assert response.status_code == 200, \
                f"Failed to generate reflection. Status: {response.status_code}, Body: {response.text}"
            
            data = response.json()
            print(f"Debug - Response data: {json.dumps(data, indent=2)}")
            
            assert "reflection" in data, "Missing 'reflection' in response"
            assert isinstance(data["patterns"], list), "Patterns should be a list"
            
        except httpx.RequestError as e:
            print(f"Debug - Request error: {str(e)}")
            raise

@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.dependency(depends=["auth_setup"])
async def test_get_profile_instructions_unknown_role(auth_headers, test_user_id):
    """存在しない役割の指示取得テスト"""
    skip_if_env_not_setup()
    print("\nDebug - Testing unknown role instructions")
    print(f"Debug - Auth headers: {auth_headers}")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        response = await client.get(
            f"/api/v1/profiles/{test_user_id}/instructions/unknown_role",
            headers=auth_headers
        )
        
        print(f"Debug - Get instructions response: {response.status_code}")
        print(f"Debug - Response body: {response.text if response.status_code != 404 else 'Not Found'}")
        assert response.status_code == 404

@pytest.mark.asyncio
@pytest.mark.dependency(depends=["auth_setup"])
async def test_get_profile_instructions_code_role(auth_headers, test_user_id):
    """code役割の指示取得テスト"""
    skip_if_env_not_setup()
    print("\nDebug - Testing code role instructions")
    print(f"Debug - Auth headers: {auth_headers}")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        response = await client.get(
            f"/api/v1/profiles/{test_user_id}/instructions/code",
            headers=auth_headers
        )
        
        print(f"Debug - Get instructions response: {response.status_code}")
        print(f"Debug - Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Debug - Instructions data: {json.dumps(data, indent=2)}")
            assert "instructions" in data
        else:
            # 初回アクセス時は404を許容
            assert response.status_code == 404, \
                f"Unexpected status code: {response.status_code}, body: {response.text}"

@pytest.mark.asyncio
@pytest.mark.dependency(depends=["auth_setup"])
async def test_personalized_instructions_update(auth_headers, session_id, test_user_id):
    """パーソナライズされた指示の更新テスト"""
    skip_if_env_not_setup()
    print("\nDebug - Testing personalized instructions update")
    print(f"Debug - Auth headers: {auth_headers}")
    print(f"Debug - User ID: {test_user_id}")
    print(f"Debug - Session ID: {session_id}")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        try:
            # 1. シンプル志向のパターンを含む振り返りを分析
            reflection_data = {
                "task_name": "総合的な実装テスト",
                "content": """
                ## 目的
                新機能の実装と既存コードの改善を行いました。

                ## 実装アプローチ
                1. まず、システム全体の設計を見直し、モジュール間の依存関係を整理しました。
                2. シンプルで読みやすい実装を心がけ、複雑な構造は避けました。
                3. 各機能にユニットテストを追加し、エッジケースも考慮しました。
                4. デバッグのしやすさを考慮して、詳細なログ出力を実装しています。
                5. APIドキュメントを整備し、チームメンバーとの情報共有を強化しました。
                
                ## 改善点
                - コードレビューからのフィードバックを積極的に取り入れました
                - パフォーマンス改善のために段階的なアプローチを採用
                - 新しい技術の導入は慎重に検討し、必要な場合のみ採用しました
                """,
                "created_at": datetime.now(UTC).isoformat(),
                "session_id": session_id,
                "user_id": test_user_id
            }

            response = await client.post(
                f"/api/v1/profiles/{test_user_id}/analyze-reflection",
                headers=auth_headers,
                json=reflection_data
            )
            
            print(f"Debug - Analyze reflection response: {response.status_code}")
            print(f"Debug - Response headers: {dict(response.headers)}")
            print(f"Debug - Response body: {response.text}")
            
            assert response.status_code == 200, \
                f"Failed to analyze reflection. Status: {response.status_code}, Body: {response.text}"
            
            data = response.json()
            print(f"Debug - Analysis data: {json.dumps(data, indent=2)}")
            
            # 2. パターンの基本検証
            assert "patterns" in data, "Missing 'patterns' in response"
            patterns = data["patterns"]
            assert len(patterns) > 0, "No patterns detected"
            
            # パターンの品質チェック
            for pattern in patterns:
                assert pattern["pattern"], f"Empty pattern found: {pattern}"
                assert 0.0 <= pattern["confidence"] <= 1.0, \
                    f"Invalid confidence value: {pattern['confidence']}"
                assert pattern["category"] in [
                    "CODING_STYLE",
                    "ARCHITECTURE",
                    "TESTING",
                    "DEBUGGING",
                    "DOCUMENTATION"
                ], f"Invalid category: {pattern['category']}"

            # 3. 少なくとも1つのパターンがシンプル志向であることを確認
            assert any(
                p["pattern"] == "シンプル志向" and p["category"] == "CODING_STYLE"
                for p in patterns
            ), "シンプル志向パターンが見つかりません"

            print("\nDebug - Detected patterns:")
            for p in patterns:
                print(f"- {p['category']}: {p['pattern']} (confidence: {p['confidence']})")
            
        except httpx.RequestError as e:
            print(f"Debug - Request error: {str(e)}")
            raise