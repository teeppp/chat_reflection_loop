"""ユーザープロファイル管理のリポジトリクラス"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class UserPattern(BaseModel):
    """ユーザーの行動パターンを表すデータモデル"""
    pattern: str
    category: str
    confidence: float
    last_updated: datetime
    examples: List[str]

    @classmethod
    def from_llm_response(cls, llm_data: dict) -> 'UserPattern':
        """LLMの分析結果からパターンを生成"""
        return cls(
            pattern=llm_data["pattern"],
            category=llm_data["category"],
            confidence=float(llm_data["confidence"]),
            last_updated=datetime.utcnow(),
            examples=[llm_data["context"]]
        )

class AgentInstruction(BaseModel):
    """エージェントへの指示を表すデータモデル"""
    role: str
    instructions: str
    priority: int

class PersonalizedAgentInstruction(BaseModel):
    """ユーザー固有のエージェント指示を表すデータモデル"""
    user_id: str
    patterns: List[UserPattern]
    base_instructions: List[AgentInstruction]
    personalized_instructions: str
    preferred_role: str  # ユーザーに最適な役割
    updated_at: datetime

class UserProfileRepository:
    """ユーザープロファイルのリポジトリクラス"""
    # 役割ごとの基本指示
    DEFAULT_INSTRUCTIONS = {
        "code": [
            AgentInstruction(
                role="code",
                instructions="コードの品質と保守性を重視し、適切なエラーハンドリングを含めてください。",
                priority=1
            )
        ],
        "architect": [
            AgentInstruction(
                role="architect",
                instructions="システム設計の一貫性と拡張性を重視し、詳細な設計ドキュメントを提供してください。",
                priority=1
            )
        ],
        "ask": [
            AgentInstruction(
                role="ask",
                instructions="質問に対して具体的で実用的な回答を提供し、必要に応じて例を含めてください。",
                priority=1
            )
        ]
    }

    def __init__(self, firestore_client):
        self.firestore_client = firestore_client
        self.profiles_collection = "user_profiles"
        self.pattern_history_collection = "pattern_history"

    async def get_profile(self, user_id: str) -> Optional[PersonalizedAgentInstruction]:
        """ユーザープロファイルを取得"""
        doc_ref = self.firestore_client.collection(self.profiles_collection).document(user_id)
        doc = doc_ref.get()  # 同期的な操作
        if not doc.exists:
            # プロファイルが存在しない場合は、基本指示を含む新しいプロファイルを作成
            profile = PersonalizedAgentInstruction(
                user_id=user_id,
                patterns=[],
                base_instructions=[],
                personalized_instructions="",
                preferred_role="code",  # デフォルトはcodeロール
                updated_at=datetime.utcnow()
            )
            # 各役割の基本指示を追加
            for role_instructions in self.DEFAULT_INSTRUCTIONS.values():
                profile.base_instructions.extend(role_instructions)
            
            # 新しいプロファイルを保存
            await self.save_profile(profile)
            return profile

        data = doc.to_dict()
        return PersonalizedAgentInstruction(
            user_id=user_id,
            patterns=[UserPattern(**p) for p in data.get("patterns", [])],
            base_instructions=[AgentInstruction(**i) for i in data.get("base_instructions", [])],
            personalized_instructions=data.get("personalized_instructions", ""),
            preferred_role=data.get("preferred_role", "code"),  # デフォルトはcodeロール
            updated_at=data.get("updated_at", datetime.utcnow())
        )

    async def save_profile(self, profile: PersonalizedAgentInstruction) -> None:
        """ユーザープロファイルを保存"""
        doc_ref = self.firestore_client.collection(self.profiles_collection).document(profile.user_id)
        doc_ref.set({  # 同期的な操作
            "patterns": [p.dict() for p in profile.patterns],
            "base_instructions": [i.dict() for i in profile.base_instructions],
            "personalized_instructions": profile.personalized_instructions,
            "preferred_role": profile.preferred_role,
            "updated_at": profile.updated_at
        })

    async def add_pattern(self, user_id: str, pattern: UserPattern) -> None:
        """新しいパターンを追加"""
        profile = await self.get_profile(user_id)
        if not profile:
            profile = PersonalizedAgentInstruction(
                user_id=user_id,
                patterns=[pattern],
                base_instructions=[],
                personalized_instructions="",
                preferred_role="code",  # デフォルトはcodeロール
                updated_at=datetime.utcnow()
            )
            # 各役割の基本指示を追加
            for role_instructions in self.DEFAULT_INSTRUCTIONS.values():
                profile.base_instructions.extend(role_instructions)
        else:
            # 既存のパターンを更新するか新しいパターンを追加
            pattern_updated = False
            for i, p in enumerate(profile.patterns):
                if p.pattern == pattern.pattern and p.category == pattern.category:
                    profile.patterns[i] = pattern
                    pattern_updated = True
                    break
            if not pattern_updated:
                profile.patterns.append(pattern)
            profile.updated_at = datetime.utcnow()

        await self.save_profile(profile)
        await self._save_pattern_history(user_id, pattern)

    async def _save_pattern_history(self, user_id: str, pattern: UserPattern) -> None:
        """パターン履歴を保存"""
        history_ref = (self.firestore_client
                      .collection(self.pattern_history_collection)
                      .document(user_id)
                      .collection("patterns"))
        
        history_ref.add({  # 同期的な操作
            "pattern": pattern.pattern,
            "category": pattern.category,
            "confidence": pattern.confidence,
            "observed_at": pattern.last_updated,
            "examples": pattern.examples
        })

    async def update_instructions(self, user_id: str, instructions: List[AgentInstruction]) -> None:
        """エージェント指示を更新"""
        profile = await self.get_profile(user_id)
        if not profile:
            profile = PersonalizedAgentInstruction(
                user_id=user_id,
                patterns=[],
                base_instructions=instructions,
                personalized_instructions="",
                preferred_role="code",  # デフォルトはcodeロール
                updated_at=datetime.utcnow()
            )
        else:
            profile.base_instructions = instructions
            profile.updated_at = datetime.utcnow()

        await self.save_profile(profile)

    async def update_personalized_instructions(self, user_id: str, instructions: str) -> None:
        """ユーザー固有の指示を更新"""
        profile = await self.get_profile(user_id)
        if not profile:
            profile = PersonalizedAgentInstruction(
                user_id=user_id,
                patterns=[],
                base_instructions=[],
                personalized_instructions=instructions,
                preferred_role="code",  # デフォルトはcodeロール
                updated_at=datetime.utcnow()
            )
            # 各役割の基本指示を追加
            for role_instructions in self.DEFAULT_INSTRUCTIONS.values():
                profile.base_instructions.extend(role_instructions)
        else:
            profile.personalized_instructions = instructions
            profile.updated_at = datetime.utcnow()

        await self.save_profile(profile)

    async def update_preferred_role(self, user_id: str, role: str) -> None:
        """ユーザーの優先役割を更新"""
        if role not in self.DEFAULT_INSTRUCTIONS:
            raise ValueError(f"Invalid role: {role}")
        
        profile = await self.get_profile(user_id)
        if profile:
            profile.preferred_role = role
            profile.updated_at = datetime.utcnow()
            await self.save_profile(profile)