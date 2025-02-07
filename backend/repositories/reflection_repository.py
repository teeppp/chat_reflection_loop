from typing import List, Optional
from datetime import datetime
from google.cloud import firestore
from agents.reflection import ReflectionDocument

class ReflectionRepository:
    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()
        self.collection = self.db.collection('reflections')

    async def save_reflection(self, reflection: ReflectionDocument) -> str:
        """振り返りメモをFirestoreに保存"""
        try:
            # ドキュメントIDを自動生成
            doc_ref = self.collection.document()
            doc_ref.set(reflection.to_dict())
            return doc_ref.id
        except Exception as e:
            # エラーログを出力（実際の実装ではより詳細なログ処理が必要）
            print(f"Error saving reflection: {str(e)}")
            raise

    async def get_reflection(self, reflection_id: str) -> Optional[ReflectionDocument]:
        """振り返りメモをIDで取得"""
        try:
            doc = self.collection.document(reflection_id).get()
            if doc.exists:
                return ReflectionDocument.from_dict(doc.to_dict())
            return None
        except Exception as e:
            print(f"Error getting reflection: {str(e)}")
            raise

    async def get_reflections_by_session(self, session_id: str) -> List[ReflectionDocument]:
        """セッションIDに紐づく振り返りメモを取得"""
        try:
            docs = self.collection\
                .where('sessionId', '==', session_id)\
                .order_by('createdAt', direction=firestore.Query.DESCENDING)\
                .stream()
            return [ReflectionDocument.from_dict(doc.to_dict()) for doc in docs]
        except Exception as e:
            print(f"Error getting reflections by session: {str(e)}")
            raise

    async def get_reflections_by_user(self, user_id: str) -> List[ReflectionDocument]:
        """ユーザーIDに紐づく振り返りメモを取得"""
        try:
            docs = self.collection\
                .where('userId', '==', user_id)\
                .order_by('createdAt', direction=firestore.Query.DESCENDING)\
                .stream()
            return [ReflectionDocument.from_dict(doc.to_dict()) for doc in docs]
        except Exception as e:
            print(f"Error getting reflections by user: {str(e)}")
            raise

    async def delete_reflection(self, reflection_id: str) -> bool:
        """振り返りメモを削除"""
        try:
            self.collection.document(reflection_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting reflection: {str(e)}")
            raise

    async def update_reflection(self, reflection_id: str, reflection: ReflectionDocument) -> bool:
        """振り返りメモを更新"""
        try:
            self.collection.document(reflection_id).set(reflection.to_dict())
            return True
        except Exception as e:
            print(f"Error updating reflection: {str(e)}")
            raise

if __name__ == "__main__":
    # テストコード
    import asyncio
    
    async def test_repository():
        # テスト用のデータ
        test_reflection = ReflectionDocument(
            task_name="テストタスク",
            content="# テスト振り返りメモ\n\nこれはテストです。\n\n## ユーザーの傾向\n- テストパターン1\n- テストパターン2",
            created_at=datetime.utcnow(),
            session_id="test-session",
            user_id="test-user"
        )

        # リポジトリのインスタンス化
        repo = ReflectionRepository()

        try:
            # 保存テスト
            doc_id = await repo.save_reflection(test_reflection)
            print(f"Saved reflection with ID: {doc_id}")

            # 取得テスト
            retrieved = await repo.get_reflection(doc_id)
            if retrieved:
                print("Retrieved reflection:", retrieved.to_dict())

            # 削除テスト
            deleted = await repo.delete_reflection(doc_id)
            print(f"Deletion {'successful' if deleted else 'failed'}")

        except Exception as e:
            print(f"Test failed: {str(e)}")

    # テストの実行
    asyncio.run(test_repository())