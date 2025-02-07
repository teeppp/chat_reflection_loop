import pytest
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import firebase_admin
from firebase_admin import credentials
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

# プロジェクトルートの.envファイルを読み込む
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / "scripts/.env")

async def get_firebase_token():
    """既存のテストユーザーでFirebase認証を行い、IDトークンを取得"""
    API_KEY = os.getenv("FIREBASE_API_KEY")  # Firebase Web API Key
    if not API_KEY:
        raise ValueError("FIREBASE_API_KEY is not set in environment variables")

    auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    
    email = os.getenv("FIREBASE_USER_EMAIL")
    password = os.getenv("FIREBASE_USER_PASSWORD")
    if not email or not password:
        raise ValueError("FIREBASE_USER_EMAIL or FIREBASE_USER_PASSWORD is not set")

    print(f"Debug - Authenticating with email: {email}")  # デバッグログ追加

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                auth_url,
                json={
                    "email": email,
                    "password": password,
                    "returnSecureToken": True
                }
            )
            response.raise_for_status()
            token = response.json()["idToken"]
            print(f"Debug - Got new token: {token[:50]}...")  # デバッグログ追加
            return token
    except Exception as e:
        print(f"Error getting Firebase token: {str(e)}")
        if isinstance(e, httpx.HTTPError):
            print(f"Response content: {e.response.content if hasattr(e, 'response') else 'No response'}")
        raise

@pytest.fixture(scope="session")
def firebase_token():
    """テストセッション全体で使用するFirebase IDトークン"""
    # 非同期関数を同期的に実行
    token = asyncio.run(get_firebase_token())
    print(f"Debug - Firebase token fixture (session): {token[:50]}...")  # デバッグログ追加
    return token

@pytest.fixture(scope="session")
def auth_headers(firebase_token):
    """認証ヘッダーを生成"""
    headers = {"Authorization": f"Bearer {firebase_token}"}
    print(f"Debug - Created auth headers with token: {firebase_token[:50]}...")  # デバッグログ追加
    return headers

# プロファイルテスト用のフィクスチャ
@pytest.fixture
def mock_profile_repository():
    """モックリポジトリを提供"""
    repository = MagicMock()
    repository.get_profile = AsyncMock()
    repository.add_pattern = AsyncMock()
    repository.update_instructions = AsyncMock()
    repository.update_personalized_instructions = AsyncMock()
    repository.update_preferred_role = AsyncMock()
    return repository

@pytest.fixture
def mock_pattern_agent():
    """パターン分析エージェントのモック"""
    agent = MagicMock()
    agent.run = AsyncMock()
    return agent

@pytest.fixture
def mock_role_agent():
    """役割分析エージェントのモック"""
    agent = MagicMock()
    agent.run = AsyncMock()
    return agent

@pytest.fixture
def mock_profile_agent(mock_profile_repository, mock_pattern_agent, mock_role_agent):
    """プロファイルエージェントのモック"""
    agent = MagicMock()
    agent.repository = mock_profile_repository
    agent.pattern_agent = mock_pattern_agent
    agent.role_agent = mock_role_agent
    agent.analyze_reflection = AsyncMock()
    agent.update_preferred_role = AsyncMock()
    agent.generate_personalized_instructions = AsyncMock()
    agent.update_from_reflection = AsyncMock()
    return agent

@pytest.fixture
def sample_user_pattern():
    """サンプルユーザーパターン"""
    return {
        "pattern": "シンプル志向",
        "category": "coding_style",
        "confidence": 0.8,
        "last_updated": datetime.now(UTC),
        "examples": ["複雑な構造を避ける"]
    }

@pytest.fixture
def sample_agent_instruction():
    """サンプルエージェント指示"""
    return {
        "role": "code",
        "instructions": "基本的なコーディング指示",
        "priority": 1
    }

@pytest.fixture
def sample_profile_data(sample_user_pattern, sample_agent_instruction):
    """サンプルプロファイルデータ"""
    return {
        "user_id": "test_user",
        "patterns": [sample_user_pattern],
        "base_instructions": [sample_agent_instruction],
        "personalized_instructions": "カスタマイズされた指示",
        "preferred_role": "code",
        "updated_at": datetime.now(UTC)
    }