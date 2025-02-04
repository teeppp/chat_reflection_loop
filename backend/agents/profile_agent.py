"""ユーザープロファイル管理のエージェントクラス"""
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel
import json
import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.vertexai import VertexAIModel
import google.auth

from repositories.user_profile_repository import (
    UserPattern,
    AgentInstruction,
    PersonalizedAgentInstruction,
    UserProfileRepository
)
from .pattern_analyzer import PatternAnalyzer
from .models import Pattern, PatternCategory, ProfileLabel, ProfileCluster

logger = logging.getLogger(__name__)

class ProfileUpdateRequest(BaseModel):
    """プロファイル更新リクエスト"""
    patterns: Optional[List[UserPattern]] = None
    instructions: Optional[List[AgentInstruction]] = None
    personalized_instructions: Optional[str] = None

class RoleAnalysisResult(BaseModel):
    """役割分析結果"""
    role: str
    confidence: float
    reasoning: str

class ProfileAgent:
    """ユーザープロファイル管理エージェント"""
    VALID_ROLES = ["learn", "create", "assist"]  # 有効な役割のリスト

    def __init__(self, repository: UserProfileRepository):
        self.repository = repository
        credentials, project = google.auth.default()
        model = VertexAIModel('gemini-2.0-flash-exp')
        self.role_agent = Agent(model, deps_type=bool)
        self.instruction_agent = Agent(model, deps_type=bool)
        self.pattern_analyzer = PatternAnalyzer()

        # 役割分析ツールを設定
        @self.role_agent.tool()
        async def analyze_role(ctx: RunContext[RoleAnalysisResult]) -> RoleAnalysisResult:
            """パターンから最適な役割を分析"""
            # システムメッセージを追加
            ctx.add_system_message("""
            あなたはユーザーの行動パターンから最適な役割を判断する専門家です。
            以下の役割から最適なものを選択してください：
            - learn: 新しい知識やスキルの習得を目的とするユーザー
              • 体系的な学習アプローチを好む
              • ステップバイステップの説明を求める
              • 具体例や参考資料を重視する
            
            - create: コンテンツ作成や問題解決を行うユーザー
              • アイデアの具現化を重視
              • 創造的な問題解決アプローチ
              • プロジェクトベースの取り組み
            
            - assist: 日常的なタスクや質問の支援を求めるユーザー
              • 即時的な問題解決を求める
              • 実用的なアドバイスを重視
              • シンプルで直接的な回答を好む
            """)
            result = await ctx.model.run_model(ctx.messages)
            return RoleAnalysisResult.model_validate_json(result.data)

    def _convert_to_user_pattern(self, pattern: Pattern) -> UserPattern:
        """PatternをUserPatternに変換"""
        return UserPattern(
            pattern=pattern.pattern,
            category=pattern.category.value,
            confidence=pattern.confidence,
            last_updated=pattern.detected_at,
            examples=pattern.context
        )

    async def analyze_reflection(self, user_id: str, reflection_content: str) -> List[UserPattern]:
        """振り返りからパターンを分析"""
        try:
            # PatternAnalyzerを使用してパターンを分析
            analysis_result = await self.pattern_analyzer.analyze(reflection_content)
            
            if analysis_result.error_occurred:
                logger.warning(f"Pattern analysis error: {analysis_result.error_message}")
            
            # PatternをUserPatternに変換
            patterns = [self._convert_to_user_pattern(p) for p in analysis_result.patterns]
            
            # パターンから適切な役割を分析
            await self._update_preferred_role(user_id, patterns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error in analyze_reflection: {str(e)}")
            return []

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
                    "role": "learn/create/assist",
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

            # LLMを使用してパターンに基づく指示を生成
            customized_instructions = [role_instructions]
            pattern_groups = {}
            
            # パターンをカテゴリーごとにグループ化
            for pattern in profile.patterns:
                if pattern.confidence > 0.5:  # 一定以上の確信度のパターンのみ考慮
                    if pattern.category not in pattern_groups:
                        pattern_groups[pattern.category] = []
                    pattern_groups[pattern.category].append(pattern)
            
            if pattern_groups:
                # パターンの説明を生成
                patterns_description = "\n".join([
                    f"カテゴリー: {category}\nパターン:\n" + "\n".join([
                        f"- {p.pattern} (確信度: {p.confidence})"
                        for p in patterns
                    ])
                    for category, patterns in pattern_groups.items()
                ])
                
                # LLMに指示を生成させる
                result = await self.instruction_agent.run(
                    f"""
                    以下のユーザーパターンに基づいて、ユーザーに合わせた具体的な指示を3つ生成してください。
                    
                    ユーザーの役割: {role_to_use}
                    
                    パターン情報:
                    {patterns_description}
                    
                    出力形式：
                    [
                        "指示1",
                        "指示2",
                        "指示3"
                    ]
                    """,
                    deps=True
                )
                
                try:
                    generated_instructions = json.loads(result.data)
                    if isinstance(generated_instructions, list):
                        customized_instructions.extend(generated_instructions)
                except json.JSONDecodeError:
                    logger.error("Failed to parse generated instructions")

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