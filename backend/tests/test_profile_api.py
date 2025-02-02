import pytest
import pytest_asyncio
import httpx
from datetime import datetime
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
    print(f"Debug - Using auth headers: {auth_headers}")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # チャットセッションを作成
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
        
        print(f"Debug - Create session response: {response.status_code}")
        assert response.status_code == 200
        session_data = response.json()
        return session_data["session_id"]

@pytest.mark.asyncio
async def test_unauthorized_profile_access():
    """未認証アクセスのテスト"""
    print("\nDebug - Testing unauthorized profile access")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/profiles/test_user/instructions/code"
        )
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_reflection_with_profile_update(auth_headers, session_id, test_user_id):
    """振り返り生成時のプロファイル更新テスト"""
    print("\nDebug - Testing reflection generation with profile update")
    print(f"Debug - Session ID: {session_id}")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 1. 振り返りを生成(このとき自動的にプロファイルも更新される)
        response = await client.post(
            f"{BASE_URL}/api/v1/reflections/generate",
            headers=auth_headers,
            json={"session_id": session_id}
        )
        
        print(f"Debug - Generate reflection response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        print(f"Debug - Response data: {json.dumps(data, indent=2)}")
        
        assert "reflection" in data
        assert isinstance(data["patterns"], list)

@pytest.mark.asyncio
async def test_get_profile_instructions_unknown_role(auth_headers, test_user_id):
    """存在しない役割の指示取得テスト"""
    print("\nDebug - Testing unknown role instructions")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/instructions/unknown_role",
            headers=auth_headers
        )
        
        print(f"Debug - Get instructions response: {response.status_code}")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_profile_instructions_code_role(auth_headers, test_user_id):
    """code役割の指示取得テスト"""
    print("\nDebug - Testing code role instructions")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/instructions/code",
            headers=auth_headers
        )
        
        print(f"Debug - Get instructions response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Debug - Instructions data: {json.dumps(data, indent=2)}")
            assert "instructions" in data
        else:
            # 初回アクセス時は404を許容
            assert response.status_code == 404

@pytest.mark.asyncio
async def test_personalized_instructions_update(auth_headers, session_id, test_user_id):
    """パーソナライズされた指示の更新テスト"""
    print("\nDebug - Testing personalized instructions update")
    print(f"Debug - User ID: {test_user_id}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 1. シンプル志向のパターンを含む振り返りを分析
        reflection_data = {
            "task_name": "コード実装テスト",
            "content": """
            シンプルな実装を心がけ、複雑な構造を避けました。
            デバッグのしやすさを考慮して、ログ出力も追加しています。
            """,
            "created_at": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "user_id": test_user_id
        }

        response = await client.post(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/analyze-reflection",
            headers=auth_headers,
            json=reflection_data
        )
        
        print(f"Debug - Analyze reflection response: {response.status_code}")
        if response.status_code != 200:
            print(f"Debug - Error response: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        print(f"Debug - Analysis data: {json.dumps(data, indent=2)}")
        
        # 2. パターンが検出されたことを確認
        assert "patterns" in data
        patterns = data["patterns"]
        assert len(patterns) > 0
        pattern_types = [p["pattern"] for p in patterns]
        assert "シンプル志向" in pattern_types
        
        # 3. 指示が更新されたことを確認
        response = await client.get(
            f"{BASE_URL}/api/v1/profiles/{test_user_id}/instructions/code",
            headers=auth_headers
        )
        
        print(f"Debug - Get updated instructions response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        print(f"Debug - Updated instructions: {json.dumps(data, indent=2)}")
        
        # 4. パーソナライズされた指示が含まれていることを確認
        assert "instructions" in data
        # instructions = data["instructions"]
        # assert "シンプル" in instructions or "simple" in instructions.lower()
        # assert "デバッグ" in instructions or "debug" in instructions.lower()