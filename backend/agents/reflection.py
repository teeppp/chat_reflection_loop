from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pydantic_ai.models.vertexai import VertexAIModel

class ReflectionDocument(BaseModel):
    """チャットセッションの振り返りメモを表すデータモデル"""
    task_name: str
    content: str  # Markdown形式(ユーザーパターンを含む)
    created_at: datetime
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    def to_dict(self) -> dict:
        """FirestoreのDocument形式に変換"""
        return {
            'taskName': self.task_name,
            'content': self.content,
            'createdAt': self.created_at,
            'sessionId': self.session_id,
            'userId': self.user_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ReflectionDocument':
        """Firestoreのドキュメントからインスタンスを生成"""
        return cls(
            task_name=data['taskName'],
            content=data['content'],
            created_at=data['createdAt'].datetime,
            session_id=data.get('sessionId'),
            user_id=data.get('userId')
        )

class ChatMessage(BaseModel):
    role: str
    content: str

class ReflectionGenerator:
    def __init__(self):
        # Gemini-2.0-flash-expモデルを使用
        model = VertexAIModel('gemini-2.0-flash-exp')
        self.agent = Agent(model, deps_type=bool)
        
    async def generate_reflection(self, chat_history: List[ChatMessage]) -> ReflectionDocument:
        """チャット履歴から振り返りメモを生成"""
        task_name = await self._extract_task_name(chat_history)
        content = await self._generate_reflection_content(chat_history)
        
        return ReflectionDocument(
            task_name=task_name,
            content=content,
            created_at=datetime.utcnow()
        )

    async def _extract_task_name(self, chat_history: List[ChatMessage]) -> str:
        """チャット履歴からタスク名を抽出"""
        prompt = """
        以下のチャット履歴から、このセッションで実行されたタスクの名前を1行で抽出してください。
        タスク名は具体的で、かつ簡潔に表現してください。

        チャット履歴:
        {chat_history}

        タスク名:
        """
        
        result = await self.agent.run(
            prompt.format(chat_history=self._format_chat_history(chat_history))
        )
        return result.data.strip()

    async def _generate_reflection_content(self, chat_history: List[ChatMessage]) -> str:
        """振り返りメモの内容を生成"""
        prompt = """
        以下のチャット履歴を分析し、以下の形式でMarkdownドキュメントを生成してください:

        1. 目的
           - タスクの目的と背景
           - 期待される成果

        2. 成果
           - 実装した機能や改善点
           - 達成された目標
           - 技術的な詳細

        3. 課題
           - 発生した問題点
           - 解決に時間を要した箇所
           - 未解決の課題

        4. ユーザーの傾向
           - コーディングスタイルの特徴
           - 技術的な選好
           - コミュニケーションパターン
           - 重視する品質属性

        5. 改善案
           - 今後の改善点
           - 追加で必要な機能
           - プロセスの改善提案

        チャット履歴:
        {chat_history}
        """
        
        result = await self.agent.run(
            prompt.format(chat_history=self._format_chat_history(chat_history))
        )
        return result.data.strip()

    def _format_chat_history(self, chat_history: List[ChatMessage]) -> str:
        """チャット履歴を文字列形式に変換"""
        formatted = []
        for msg in chat_history:
            formatted.append(f"{msg.role}: {msg.content}")
        return '\n\n'.join(formatted)

if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()

    # テスト用のチャット履歴
    test_history = [
        ChatMessage(role="user", content="新しいWebアプリケーションの開発計画を立ててください"),
        ChatMessage(role="assistant", content="はい、以下の手順で進めていきましょう..."),
        ChatMessage(role="user", content="ありがとうございます。具体的な技術スタックを決めましょう")
    ]

    async def test():
        generator = ReflectionGenerator()
        reflection = await generator.generate_reflection(test_history)
        print(reflection.content)

    asyncio.run(test())