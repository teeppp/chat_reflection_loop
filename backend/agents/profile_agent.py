"""ユーザープロファイル管理のエージェントクラス"""
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel
import json

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.vertexai import VertexAIModel
import google.auth

from repositories.user_profile_repository import (
    UserPattern,
    AgentInstruction,
    PersonalizedAgentInstruction,
    UserProfileRepository
)

class ProfileUpdateRequest(BaseModel):
    """プロファイル更新リクエスト"""
    patterns: Optional[List[UserPattern]] = None
    instructions: Optional[List[AgentInstruction]] = None
    personalized_instructions: Optional[str] = None

class PatternAnalysisResult(BaseModel):
    """パターン分析結果"""
    patterns: List[Dict[str, str | float | List[str]]]

class RoleAnalysisResult(BaseModel):
    """役割分析結果"""
    role: str
    confidence: float
    reasoning: str

class ProfileAgent:
    """ユーザープロファイル管理エージェント"""
    VALID_ROLES = ["code", "architect", "ask"]  # 有効な役割のリスト

    def __init__(self, repository: UserProfileRepository):
        self.repository = repository
        credentials, project = google.auth.default()
        model = VertexAIModel('gemini-2.0-flash-exp')
        self.pattern_agent = Agent(model, deps_type=bool)
        self.role_agent = Agent(model, deps_type=bool)

        # パターン分析ツールを設定
        @self.pattern_agent.tool()
        async def analyze_patterns(ctx: RunContext[PatternAnalysisResult]) -> PatternAnalysisResult:
            """振り返り内容からユーザーパターンを分析"""
            # システムメッセージを追加
            ctx.add_system_message("""
            あなたはユーザーの振り返りを分析し、行動パターンを特定する専門家です。
            以下のような観点でパターンを抽出してください：
            - コーディングスタイル
            - デバッグ手法
            - アーキテクチャ設計の傾向
            - 問題解決アプローチ
            """)
            result = await ctx.model.run_model(ctx.messages)
            return PatternAnalysisResult.model_validate_json(result.data)

        # 役割分析ツールを設定
        @self.role_agent.tool()
        async def analyze_role(ctx: RunContext[RoleAnalysisResult]) -> RoleAnalysisResult:
            """パターンから最適な役割を分析"""
            # システムメッセージを追加
            ctx.add_system_message("""
            あなたはユーザーの行動パターンから最適な役割を判断する専門家です。
            以下の役割から最適なものを選択してください：
            - code: 実装重視、コーディングスキル
            - architect: 設計重視、システム構造
            - ask: 質問対応、情報提供
            """)
            result = await ctx.model.run_model(ctx.messages)
            return RoleAnalysisResult.model_validate_json(result.data)

    async def analyze_reflection(self, user_id: str, reflection_content: str) -> List[UserPattern]:
        """振り返りからパターンを分析（LLM使用）"""
        try:
            # パターン分析を実行
            result = await self.pattern_agent.run(
                f"""
                以下の振り返り内容からユーザーの行動パターンを分析し、JSONで出力してください：

                {reflection_content}

                出力形式：
                {{
                    "patterns": [
                        {{
                            "pattern": "パターン名",
                            "category": "カテゴリ",
                            "confidence": 0.8,
                            "context": "検出された文脈"
                        }}
                    ]
                }}
                """,
                deps=True
            )

            # 分析結果からUserPatternオブジェクトを生成
            patterns = []
            for p in result.data.patterns:
                pattern = UserPattern(
                    pattern=p["pattern"],
                    category=p["category"],
                    confidence=float(p["confidence"]),
                    last_updated=datetime.utcnow(),
                    examples=[p["context"]]
                )
                patterns.append(pattern)

            # パターンから適切な役割を分析
            await self._update_preferred_role(user_id, patterns)
            
            return patterns
        except Exception as e:
            print(f"Error in analyze_reflection: {str(e)}")
            return self._fallback_pattern_analysis(reflection_content)

    def _fallback_pattern_analysis(self, content: str) -> List[UserPattern]:
        """LLM失敗時のフォールバックパターン分析"""
        patterns = []
        normalized_content = ' '.join(content.split())

        if any(word in normalized_content.lower() for word in ["シンプル", "simple", "簡潔"]):
            patterns.append(UserPattern(
                pattern="シンプル志向",
                category="coding_style",
                confidence=0.8,
                last_updated=datetime.utcnow(),
                examples=[content]
            ))

        if any(word in normalized_content.lower() for word in ["デバッグ", "debug", "ログ", "log"]):
            patterns.append(UserPattern(
                pattern="デバッグ重視",
                category="debugging",
                confidence=0.7,
                last_updated=datetime.utcnow(),
                examples=[content]
            ))

        return patterns

    async def _update_preferred_role(self, user_id: str, patterns: List[UserPattern]) -> None:
        """パターンに基づいて推奨役割を更新"""
        try:
            patterns_str = "\n".join([
                f"パターン: {p.pattern}\n"
                f"カテゴリ: {p.category}\n"
                f"確信度: {p.confidence}\n"
                f"文脈: {p.examples[0] if p.examples else 'なし'}\n"
                for p in patterns
            ])

            result = await self.role_agent.run(
                f"""
                以下のユーザーパターンから最適な役割を判断し、JSONで出力してください：

                {patterns_str}

                出力形式：
                {{
                    "role": "code/architect/ask",
                    "confidence": 0.8,
                    "reasoning": "判断理由"
                }}
                """,
                deps=True
            )

            if result.data.role in self.VALID_ROLES:
                await self.repository.update_preferred_role(user_id, result.data.role)
        except Exception as e:
            print(f"Error in update_preferred_role: {str(e)}")

    async def update_profile(self, user_id: str, request: ProfileUpdateRequest) -> None:
        """プロファイルを更新"""
        if request.patterns:
            for pattern in request.patterns:
                await self.repository.add_pattern(user_id, pattern)

        if request.instructions:
            await self.repository.update_instructions(user_id, request.instructions)

        if request.personalized_instructions is not None:
            await self.repository.update_personalized_instructions(
                user_id,
                request.personalized_instructions
            )

    async def generate_personalized_instructions(
        self,
        user_id: str,
        base_role: Optional[str] = None
    ) -> Optional[str]:
        """ユーザー固有の指示を生成"""
        try:
            profile = await self.repository.get_profile(user_id)
            if not profile:
                return None

            # base_roleが指定されていない場合は、preferred_roleを使用
            role_to_use = base_role if base_role in self.VALID_ROLES else profile.preferred_role

            # 指定された役割の基本指示を取得
            role_instructions = None
            for instruction in profile.base_instructions:
                if instruction.role == role_to_use:
                    role_instructions = instruction.instructions
                    break

            if not role_instructions:
                return None

            # パターンに基づいて指示をカスタマイズ
            customized_instructions = [role_instructions]
            for pattern in profile.patterns:
                if pattern.category == "coding_style":
                    customized_instructions.extend([
                        "- シンプルで読みやすいコードを心がける",
                        "- 複雑な構造を避ける",
                        "- 明確で理解しやすい実装を優先する"
                    ])

                if pattern.category == "debugging":
                    customized_instructions.extend([
                        "- 詳細なログ出力を含める",
                        "- エラーハンドリングを丁寧に実装",
                        "- デバッグ情報の可視性を重視する"
                    ])

            # 指示を結合して保存
            final_instructions = "\n".join(customized_instructions)
            await self.repository.update_personalized_instructions(user_id, final_instructions)
            return final_instructions
        except Exception as e:
            print(f"Error in generate_personalized_instructions: {str(e)}")
            return None

    async def update_from_reflection(
        self,
        user_id: str,
        reflection_content: str
    ) -> List[UserPattern]:
        """振り返りからプロファイルを更新"""
        try:
            # パターンを分析
            new_patterns = await self.analyze_reflection(user_id, reflection_content)

            # プロファイルを更新
            for pattern in new_patterns:
                await self.repository.add_pattern(user_id, pattern)

            # preferred_roleを反映した指示の更新
            profile = await self.repository.get_profile(user_id)
            if profile:
                final_instructions = await self.generate_personalized_instructions(user_id)
                if final_instructions:
                    await self.repository.update_personalized_instructions(
                        user_id,
                        final_instructions
                    )

            return new_patterns
        except Exception as e:
            print(f"Error in update_from_reflection: {str(e)}")
            return []