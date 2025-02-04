"""ユーザープロファイル管理のリポジトリクラス"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import json
import logging
from google.cloud import firestore

from agents.models import (
    DynamicLabel,
    LabelCluster,
    DynamicCategory,
    ProfileInsightResult,
    Pattern,
    AgentInstruction,
    UserProfile
)

logger = logging.getLogger(__name__)

class UserPattern(BaseModel):
    """ユーザーの行動パターン"""
    pattern: str
    category: str
    confidence: float
    last_updated: datetime
    examples: List[str]

class UserProfileRepository:
    """ユーザープロファイル管理リポジトリ"""
    
    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()
        self._profiles_ref = self.db.collection('user_profiles')
        self._patterns_ref = self.db.collection('pattern_history')

    def _to_dict(self, obj: BaseModel) -> dict:
        """BaseModelをdictに変換"""
        return json.loads(obj.model_dump_json())

    def _from_dict(self, data: dict, model_class: type) -> BaseModel:
        """dictからBaseModelを生成"""
        return model_class.model_validate(data)

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """プロファイルを取得"""
        try:
            doc = self._profiles_ref.document(user_id).get()
            if not doc.exists:
                # プロファイルが存在しない場合は新規作成
                new_profile = UserProfile(
                    user_id=user_id,
                    patterns=[],
                    labels=[],
                    clusters=[],
                    categories=[],
                    base_instructions=[],
                    updated_at=datetime.utcnow()
                )
                self._profiles_ref.document(user_id).set(self._to_dict(new_profile))
                return new_profile
            
            # 既存のプロファイルを取得
            profile_data = doc.to_dict()
            # user_idを追加
            profile_data['user_id'] = user_id
            return self._from_dict(profile_data, UserProfile)
        except Exception as e:
            logger.error(f"Error getting profile for user {user_id}: {str(e)}")
            return None

    async def add_pattern(self, user_id: str, pattern: UserPattern) -> None:
        """パターンを追加"""
        try:
            # プロファイルドキュメントを更新
            profile_ref = self._profiles_ref.document(user_id)
            
            # トランザクションで更新
            @firestore.transactional
            def update_in_transaction(transaction, prof_ref):
                prof_doc = prof_ref.get(transaction=transaction)
                if not prof_doc.exists:
                    # 新規プロファイル作成
                    new_profile = UserProfile(
                        user_id=user_id,
                        patterns=[pattern],
                        labels=[],
                        clusters=[],
                        categories=[],
                        base_instructions=[],
                        updated_at=datetime.utcnow()
                    )
                    transaction.set(prof_ref, self._to_dict(new_profile))
                else:
                    # 既存パターンを更新または追加
                    profile_data = prof_doc.to_dict()
                    patterns = profile_data.get('patterns', [])
                    pattern_exists = False
                    
                    for i, p in enumerate(patterns):
                        if p['pattern'] == pattern.pattern:
                            patterns[i] = self._to_dict(pattern)
                            pattern_exists = True
                            break
                    
                    if not pattern_exists:
                        patterns.append(self._to_dict(pattern))
                    
                    transaction.update(prof_ref, {
                        'patterns': patterns,
                        'updated_at': datetime.utcnow()
                    })

            # トランザクションを実行
            transaction = self.db.transaction()
            update_in_transaction(transaction, profile_ref)
            
            # パターン履歴に追加
            self._patterns_ref.document(user_id).collection('patterns').add({
                'pattern': pattern.pattern,
                'category': pattern.category,
                'confidence': pattern.confidence,
                'observed_at': datetime.utcnow(),
                'examples': pattern.examples
            })

        except Exception as e:
            logger.error(f"Error adding pattern for user {user_id}: {str(e)}")
            raise

    async def add_label(self, user_id: str, label: DynamicLabel) -> None:
        """ラベルを追加"""
        try:
            profile_ref = self._profiles_ref.document(user_id)
            
            @firestore.transactional
            def update_in_transaction(transaction, prof_ref):
                prof_doc = prof_ref.get(transaction=transaction)
                if not prof_doc.exists:
                    new_profile = UserProfile(
                        user_id=user_id,
                        patterns=[],
                        labels=[label],
                        clusters=[],
                        categories=[],
                        base_instructions=[],
                        updated_at=datetime.utcnow()
                    )
                    transaction.set(prof_ref, self._to_dict(new_profile))
                else:
                    profile_data = prof_doc.to_dict()
                    labels = profile_data.get('labels', [])
                    label_exists = False
                    
                    for i, l in enumerate(labels):
                        if l['text'] == label.text:
                            # 既存ラベルを更新
                            l['occurrence_count'] += 1
                            l['last_seen'] = datetime.utcnow()
                            l['context'].extend(label.context)
                            l['confidence'] = max(l['confidence'], label.confidence)
                            labels[i] = self._to_dict(label)
                            label_exists = True
                            break
                    
                    if not label_exists:
                        labels.append(self._to_dict(label))
                    
                    transaction.update(prof_ref, {
                        'labels': labels,
                        'updated_at': datetime.utcnow()
                    })

            transaction = self.db.transaction()
            update_in_transaction(transaction, profile_ref)

        except Exception as e:
            logger.error(f"Error adding label for user {user_id}: {str(e)}")
            raise

    async def update_cluster(self, user_id: str, cluster: LabelCluster) -> None:
        """クラスターを更新"""
        try:
            profile_ref = self._profiles_ref.document(user_id)
            
            @firestore.transactional
            def update_in_transaction(transaction, prof_ref):
                prof_doc = prof_ref.get(transaction=transaction)
                if not prof_doc.exists:
                    new_profile = UserProfile(
                        user_id=user_id,
                        patterns=[],
                        labels=[],
                        clusters=[cluster],
                        categories=[],
                        base_instructions=[],
                        updated_at=datetime.utcnow()
                    )
                    transaction.set(prof_ref, self._to_dict(new_profile))
                else:
                    profile_data = prof_doc.to_dict()
                    clusters = profile_data.get('clusters', [])
                    cluster_exists = False
                    
                    for i, c in enumerate(clusters):
                        if c['cluster_id'] == cluster.cluster_id:
                            clusters[i] = self._to_dict(cluster)
                            cluster_exists = True
                            break
                    
                    if not cluster_exists:
                        clusters.append(self._to_dict(cluster))
                    
                    transaction.update(prof_ref, {
                        'clusters': clusters,
                        'updated_at': datetime.utcnow()
                    })

            transaction = self.db.transaction()
            update_in_transaction(transaction, profile_ref)

        except Exception as e:
            logger.error(f"Error updating cluster for user {user_id}: {str(e)}")
            raise

    async def add_category(self, user_id: str, category: DynamicCategory) -> None:
        """カテゴリーを追加"""
        try:
            profile_ref = self._profiles_ref.document(user_id)
            
            @firestore.transactional
            def update_in_transaction(transaction, prof_ref):
                prof_doc = prof_ref.get(transaction=transaction)
                if not prof_doc.exists:
                    new_profile = UserProfile(
                        user_id=user_id,
                        patterns=[],
                        labels=[],
                        clusters=[],
                        categories=[category],
                        base_instructions=[],
                        updated_at=datetime.utcnow()
                    )
                    transaction.set(prof_ref, self._to_dict(new_profile))
                else:
                    profile_data = prof_doc.to_dict()
                    categories = profile_data.get('categories', [])
                    category_exists = False
                    
                    for i, c in enumerate(categories):
                        if c['name'] == category.name:
                            categories[i] = self._to_dict(category)
                            category_exists = True
                            break
                    
                    if not category_exists:
                        categories.append(self._to_dict(category))
                    
                    transaction.update(prof_ref, {
                        'categories': categories,
                        'updated_at': datetime.utcnow()
                    })

            transaction = self.db.transaction()
            update_in_transaction(transaction, profile_ref)

        except Exception as e:
            logger.error(f"Error adding category for user {user_id}: {str(e)}")
            raise

    async def update_profile_insights(
        self,
        user_id: str,
        insights: ProfileInsightResult
    ) -> None:
        """プロファイルの分析結果を更新"""
        try:
            await self._profiles_ref.document(user_id).update({
                'insights': self._to_dict(insights),
                'updated_at': datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error updating insights for user {user_id}: {str(e)}")
            raise

    async def update_instructions(
        self,
        user_id: str,
        instructions: List[AgentInstruction]
    ) -> None:
        """基本指示を更新"""
        try:
            await self._profiles_ref.document(user_id).update({
                'base_instructions': [self._to_dict(i) for i in instructions],
                'updated_at': datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error updating instructions for user {user_id}: {str(e)}")
            raise

    async def update_personalized_instructions(
        self,
        user_id: str,
        instructions: str
    ) -> None:
        """個別化された指示を更新"""
        try:
            await self._profiles_ref.document(user_id).update({
                'personalized_instructions': instructions,
                'updated_at': datetime.utcnow()
            })
        except Exception as e:
            logger.error(
                f"Error updating personalized instructions for user {user_id}: {str(e)}"
            )
            raise