import asyncio
import pytest
import pytest_asyncio
import httpx
from datetime import datetime
import json

BASE_URL = "http://dev_backend:8080"

# タイムアウトを延長(LLMの処理時間を考慮)
TIMEOUT = httpx.Timeout(30.0, connect=60.0)

@pytest_asyncio.fixture
async def session_id(auth_headers):
    """テスト用のチャットセッションを作成"""
    print("\nDebug - Creating test session")  # デバッグログ追加
    print(f"Debug - Using auth headers: {auth_headers}")  # デバッグログ追加
    
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
        print(f"Debug - Create session response: {response.status_code}")  # デバッグログ追加
        if response.status_code != 200:
            print(f"Debug - Response content: {response.content}")  # デバッグログ追加
            print(f"Debug - Response headers: {response.headers}")  # デバッグログ追加
        
        assert response.status_code == 200
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Debug - Created session: {session_id}")  # デバッグログ追加

        # メッセージを追加
        messages = [
            {"role": "assistant", "content": "はい、以下の手順で進めていきましょう..."},
            {"role": "user", "content": "具体的な技術スタックを決めましょう"}
        ]
        for msg in messages:
            response = await client.put(
                f"{BASE_URL}/api/v1/chat-histories/{session_id}",
                headers=auth_headers,
                json=msg
            )
            print(f"Debug - Add message response: {response.status_code}")  # デバッグログ追加
            if response.status_code != 200:
                print(f"Debug - Response content: {response.content}")  # デバッグログ追加
            assert response.status_code == 200

        return session_id

@pytest.mark.asyncio
async def test_unauthorized_access():
    """未認証アクセスのテスト"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/api/v1/reflections/user")
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_generate_reflection(auth_headers, session_id):
    """振り返りメモ生成APIのテスト"""
    print(f"\nDebug - Starting generate_reflection test")  # デバッグログ追加
    print(f"Debug - Session ID: {session_id}")  # デバッグログ追加
    print(f"Debug - Auth headers: {auth_headers}")  # デバッグログ追加
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/reflections/generate",
            headers=auth_headers,
            json={"session_id": session_id}
        )
        
        print(f"Debug - Generate reflection response: {response.status_code}")  # デバッグログ追加
        data = response.json()
        print(f"Debug - Response data: {json.dumps(data, indent=2)}")  # デバッグログ追加
        
        assert response.status_code == 200
        assert "taskName" in data  # キー名を修正
        assert "content" in data

@pytest.mark.asyncio
async def test_get_session_reflection(auth_headers, session_id):
    """セッション別の振り返りメモ取得テスト"""
    print(f"\nDebug - Starting get_session_reflection test")  # デバッグログ追加
    print(f"Debug - Session ID: {session_id}")  # デバッグログ追加
    print(f"Debug - Auth headers: {auth_headers}")  # デバッグログ追加
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 振り返りメモを生成
        response = await client.post(
            f"{BASE_URL}/api/v1/reflections/generate",
            headers=auth_headers,
            json={"session_id": session_id}
        )
        print(f"Debug - Generate reflection response: {response.status_code}")  # デバッグログ追加
        if response.status_code != 200:
            print(f"Debug - Response content: {response.content}")  # デバッグログ追加

        # 振り返りメモを取得
        response = await client.get(
            f"{BASE_URL}/api/v1/reflections/session/{session_id}",
            headers=auth_headers
        )
        
        print(f"Debug - Get reflection response: {response.status_code}")  # デバッグログ追加
        data = response.json()
        print(f"Debug - Response data: {json.dumps(data, indent=2)}")  # デバッグログ追加
        
        assert response.status_code == 200
        assert "reflection" in data
        reflection = data["reflection"]
        assert "taskName" in reflection  # キー名を修正
        assert "content" in reflection

@pytest.mark.asyncio
async def test_get_user_reflections(auth_headers):
    """ユーザーの全振り返りメモ取得テスト"""
    print("\nDebug - Starting get_user_reflections test")  # デバッグログ追加
    print(f"Debug - Auth headers: {auth_headers}")  # デバッグログ追加
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/reflections/user",
            headers=auth_headers
        )
        
        print(f"Debug - Get user reflections response: {response.status_code}")  # デバッグログ追加
        data = response.json()
        print(f"Debug - Response data: {json.dumps(data, indent=2)}")  # デバッグログ追加
        
        assert response.status_code == 200
        assert "reflections" in data
        assert isinstance(data["reflections"], list)