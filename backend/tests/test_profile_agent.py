"""ユーザープロファイルエージェントのAPIテスト"""
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, UTC
import json
import jwt

# テスト設定
BASE_URL = "http://dev_backend:8080"
TIMEOUT = httpx.Timeout(30.0, connect=60.0)

@pytest_asyncio.fixture
async def test_user_id(auth_headers):
    """トークンからユーザーIDを取得"""
    token = auth_headers["Authorization"].split(" ")[1]
    # JWTをデコードしてユーザーIDを取得
    decoded = jwt.decode(token, options={"verify_signature": False})
    return decoded["user_id"]

@pytest_asyncio.fixture
async def session_id(auth_headers):
    """テスト用のチャットセッションを作成"""
    print("\nDebug - Creating test session")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/chat-histories",
            headers=auth_headers,
            json={
                "initial_message": {
                    "role": "user",
                    "content": "新しいWebアプリケーションの開発計画を立ててください"
                }
            }
        )
        
        assert response.status_code == 200
        return response.json()["session_id"]

@pytest.mark.asyncio
async def test_analyze_reflection_with_llm(auth_headers, session_id, test_user_id):
    """LLMを使用したパターン分析のAPIテスト"""
    print("\nDebug - Testing pattern analysis with LLM")
    print(f"Debug - Session ID: {session_id}")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 振り返りデータを作成
        reflection_data = {
            "task_name": "システム設計タスク",
            "content": """
            アーキテクチャの設計に重点を置き、以下の点を考慮しました：
            1. システムの拡張性を重視
            2. コンポーネントの疎結合化
            3. デバッグのしやすさを考慮したログ設計
            4. エラーハンドリングの明確化
            """,
            "session_id": session_id,
            "created_at": datetime.now(UTC).isoformat()
        }

        # パターン分析を実行
        response = await client.post(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/analyze-reflection",
            headers=auth_headers,
            json=reflection_data
        )
        
        print(f"Debug - Analyze response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        print(f"Debug - Analysis data: {json.dumps(data, indent=2)}")
        
        assert "patterns" in data
        patterns = data["patterns"]
        assert len(patterns) > 0
        pattern = patterns[0]
        assert "pattern" in pattern
        assert "category" in pattern
        assert "confidence" in pattern
        assert float(pattern["confidence"]) > 0

@pytest.mark.asyncio
async def test_unauthorized_profile_access():
    """未認証アクセスのテスト"""
    print("\nDebug - Testing unauthorized access")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/profiles/test_user/instructions/code"
        )
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_profile_instructions_code_role(auth_headers, test_user_id):
    """code役割の指示取得テスト"""
    print("\nDebug - Testing get code role instructions")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # まずパターンを作成
        reflection_data = {
            "task_name": "コード実装タスク",
            "content": """
            シンプルな実装を心がけ、以下の点に注意しました：
            1. 複雑な構造を避ける
            2. デバッグ情報の出力
            3. 明確なエラーハンドリング
            """,
            "session_id": "dummy_session",
            "created_at": datetime.now(UTC).isoformat()
        }

        response = await client.post(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/analyze-reflection",
            headers=auth_headers,
            json=reflection_data
        )
        assert response.status_code == 200

        # 次に指示を取得
        response = await client.get(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/instructions/code",
            headers=auth_headers
        )
        
        print(f"Debug - Get instructions response: {response.status_code}")
        assert response.status_code in [200, 404]  # 初回は404を許容
        
        if response.status_code == 200:
            data = response.json()
            print(f"Debug - Instructions data: {json.dumps(data, indent=2)}")
            assert "instructions" in data

@pytest.mark.asyncio
async def test_update_profile_with_reflection(auth_headers, session_id, test_user_id):
    """振り返りからのプロファイル更新テスト"""
    print("\nDebug - Testing profile update with reflection")
    print(f"Debug - Session ID: {session_id}")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 1. パターン分析を実行
        reflection_data = {
            "task_name": "システム実装タスク",
            "content": """
            シンプルな実装を心がけ、以下の点に注意しました：
            1. コードの可読性を重視
            2. デバッグ情報の充実
            3. エラーハンドリングの明確化
            """,
            "session_id": session_id,
            "created_at": datetime.now(UTC).isoformat()
        }

        response = await client.post(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/analyze-reflection",
            headers=auth_headers,
            json=reflection_data
        )
        
        print(f"Debug - Analyze response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        print(f"Debug - Analysis data: {json.dumps(data, indent=2)}")
        
        assert "patterns" in data
        assert len(data["patterns"]) > 0

@pytest.mark.asyncio
async def test_get_invalid_role_instructions(auth_headers, test_user_id):
    """無効な役割の指示取得テスト"""
    print("\nDebug - Testing invalid role instructions")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/instructions/invalid_role",
            headers=auth_headers
        )
        
        print(f"Debug - Get instructions response: {response.status_code}")
        assert response.status_code == 404
        
@pytest.mark.asyncio
async def test_error_handling(auth_headers, test_user_id):
    """エラーハンドリングのテスト"""
    print("\nDebug - Testing error handling")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 不正なデータでリクエスト
        invalid_data = {
            "invalid_field": "invalid_value"
        }

        response = await client.post(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/analyze-reflection",
            headers=auth_headers,
            json=invalid_data
        )
        
        print(f"Debug - Error response: {response.status_code}")
        assert response.status_code in [400, 422]  # 不正なリクエストまたはバリデーションエラー