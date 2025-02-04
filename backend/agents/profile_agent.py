"""ユーザープロファイル管理のエージェントクラス"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
import logging

from pydantic_ai.agent import Agent
from pydantic_ai.agent import RunContext
from pydantic_ai.models.vertexai import VertexAIModel  # 修正: vertex_ai → vertexai
import google.auth

from agents.pattern_analysis_engine import PatternAnalysisEngine
from agents.models import (
    Pattern,
    DynamicLabel,
    LabelCluster,
    DynamicCategory,
    DynamicPatternEngine,
    PatternAnalysisResult,
    ProfileInsightResult  # ProfileInsightResultをmodelsから直接インポート
)

from repositories.user_profile_repository import (
    UserPattern,
    AgentInstruction,
    UserProfileRepository
)

logger = logging.getLogger(__name__)

class ProfileUpdateRequest(BaseModel):
    """プロファイル更新リクエスト"""
    patterns: Optional[List[UserPattern]] = None
    instructions: Optional[List[AgentInstruction]] = None
    personalized_instructions: Optional[str] = None
    labels: Optional[List[DynamicLabel]] = None
    categories: Optional[List[DynamicCategory]] = None

class ProfileAgent:
    """ユーザープロファイル管理エージェント"""

    def __init__(self, repository: UserProfileRepository):
        self.repository = repository
        credentials, project = google.auth.default()
        model = VertexAIModel('gemini-2.0-flash-exp')
        self.insight_agent = Agent(model, deps_type=bool)
        self.instruction_agent = Agent(model, deps_type=bool)
        
        # 動的パターン分析エンジンを初期化
        self.pattern_engine = PatternAnalysisEngine(
            config=DynamicPatternEngine(
                min_confidence=0.6,
                max_labels_per_pattern=10,
                clustering_threshold=0.7,
                label_similarity_threshold=0.6
            )
        )

        # プロファイル分析ツールを設定
        @self.insight_agent.tool()
        async def analyze_profile_insights(
            ctx: RunContext[ProfileInsightResult]
        ) -> ProfileInsightResult:
            """プロファイルから主要な特徴を分析"""
            ctx.add_system_message("""
            あなたはユーザーのプロファイルから重要な特徴とパターンを分析する専門家です。
            ラベルとクラスター情報から、ユーザーの主要な特徴を抽出し、その理由を説明してください。
            回答は具体的で、ユーザーの行動パターンに基づいた分析を含める必要があります。
            """)
            result = await ctx.model.run_model(ctx.messages)
            return ProfileInsightResult.model_validate_json(result.data)

    def _convert_to_user_pattern(self, pattern: Pattern) -> UserPattern:
        """PatternをUserPatternに変換"""
        return UserPattern(
            pattern=pattern.pattern,
            category=pattern.category,
            confidence=pattern.confidence,
            last_updated=pattern.detected_at,
            examples=pattern.context
        )

    async def analyze_reflection(
        self,
        user_id: str,
        reflection_content: str
    ) -> PatternAnalysisResult:
        """振り返りからパターンを分析"""
        try:
            # 動的パターン分析を実行
            analysis_result = await self.pattern_engine.analyze_pattern(reflection_content)
            
            if analysis_result.error_occurred:
                logger.warning(f"Pattern analysis error: {analysis_result.error_message}")
                return analysis_result
            
            # プロファイルを更新
            await self._update_profile_with_analysis(user_id, analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in analyze_reflection: {str(e)}")
            return PatternAnalysisResult(
                patterns=[],
                error_occurred=True,
                error_message=str(e)
            )

    async def _update_profile_with_analysis(
        self,
        user_id: str,
        analysis: PatternAnalysisResult
    ) -> None:
        """分析結果でプロファイルを更新"""
        try:
            # パターンを更新
            for pattern in analysis.patterns:
                user_pattern = self._convert_to_user_pattern(pattern)
                await self.repository.add_pattern(user_id, user_pattern)
            
            # ラベルを更新
            for label in analysis.labels:
                await self.repository.add_label(user_id, label)
            
            # クラスターを更新
            for cluster in analysis.clusters:
                await self.repository.update_cluster(user_id, cluster)
            
            # プロファイルの分析を実行
            insights = await self._analyze_profile_insights(user_id)
            if insights:
                await self.repository.update_profile_insights(user_id, insights)
                
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")

    async def _analyze_profile_insights(
        self,
        user_id: str
    ) -> Optional[ProfileInsightResult]:
        """プロファイルの主要な特徴を分析"""
        try:
            profile = await self.repository.get_profile(user_id)
            if not profile:
                return None

            # プロファイル情報を文字列化
            profile_info = {
                "labels": [label.text for label in profile.labels],
                "clusters": [
                    {"theme": c.theme, "labels": c.labels}
                    for c in profile.clusters
                ],
                "patterns": [p.pattern for p in profile.patterns]
            }
            
            result = await self.insight_agent.run(
                f"""
                あなたは、ユーザーの行動パターンや特徴を深く分析する専門家です。
                以下のプロファイル情報から、この人独自の特徴やパターンを抽出し、洞察を提供してください。

                現在のプロファイル情報：
                {json.dumps(profile_info, indent=2, ensure_ascii=False)}

                分析の際の重要なポイント：
                1. 表面的な分類ではなく、ユーザー固有の行動や思考のパターンを見つけ出す
                2. ラベル間の関連性から、より深い洞察を導き出す
                3. 時間の経過による変化や一貫性のあるパターンを識別する
                4. 特に以下の観点での分析を重視：
                   - 問題解決アプローチの特徴
                   - 学習・理解の好みのパターン
                   - コミュニケーションスタイルの独自性
                   - 意思決定プロセスの特徴
                   - モチベーションの源泉

                以下の形式でJSONを出力してください：
                {{
                    "primary_labels": [
                        "最も特徴的なラベル（ユーザー固有の表現で）",
                        "次に特徴的なラベル"
                    ],
                    "clusters": [
                        {{
                            "theme": "発見されたパターンの本質",
                            "labels": [
                                "関連する具体的な行動や特徴",
                                "それを裏付ける別の特徴"
                            ]
                        }}
                    ],
                    "confidence": 0.0-1.0,
                    "reasoning": "なぜそのような特徴が見られるのか、どのような文脈で現れているのかの詳細な説明"
                }}
                """,
                deps=True
            )

            return result.data

        except Exception as e:
            logger.error(f"Error in profile insights analysis: {str(e)}")
            return None

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
            
        if request.labels:
            for label in request.labels:
                await self.repository.add_label(user_id, label)
                
        if request.categories:
            for category in request.categories:
                await self.repository.add_category(user_id, category)

    async def generate_personalized_instructions(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """ユーザー固有の指示を生成"""
        try:
            profile = await self.repository.get_profile(user_id)
            if not profile:
                return None

            # プロファイル情報を収集
            profile_info = {
                "labels": [label.text for label in profile.labels],
                "clusters": [
                    {"theme": c.theme, "labels": c.labels}
                    for c in profile.clusters
                ],
                "patterns": [p.pattern for p in profile.patterns]
            }
            
            if context:
                profile_info["context"] = context

            # LLMに指示を生成させる
            result = await self.instruction_agent.run(
                f"""
                以下のユーザープロファイル情報に基づいて、
                ユーザーに合わせた具体的な指示を生成してください：

                {json.dumps(profile_info, indent=2, ensure_ascii=False)}

                以下の点を考慮してください：
                1. ユーザーの主要なラベルとパターン
                2. クラスター分析から見られる傾向
                3. コンテキスト情報（提供されている場合）

                出力形式：
                [
                    "具体的な指示1",
                    "具体的な指示2",
                    "具体的な指示3"
                ]
                """,
                deps=True
            )

            try:
                instructions = json.loads(result.data)
                if isinstance(instructions, list):
                    final_instructions = "\n".join(instructions)
                    await self.repository.update_personalized_instructions(
                        user_id,
                        final_instructions
                    )
                    return final_instructions
            except json.JSONDecodeError:
                logger.error("Failed to parse generated instructions")
                return None

        except Exception as e:
            logger.error(f"Error in generate_personalized_instructions: {str(e)}")
            return None

    async def update_from_reflection(
        self,
        user_id: str,
        reflection_content: str
    ) -> PatternAnalysisResult:
        """振り返りからプロファイルを更新"""
        try:
            # パターンを分析
            analysis_result = await self.analyze_reflection(user_id, reflection_content)
            
            # プロファイルを更新
            await self._update_profile_with_analysis(user_id, analysis_result)
            
            # 指示を更新
            instructions = await self.generate_personalized_instructions(user_id)
            if instructions:
                await self.repository.update_personalized_instructions(
                    user_id,
                    instructions
                )

            return analysis_result
        except Exception as e:
            logger.error(f"Error in update_from_reflection: {str(e)}")
            return PatternAnalysisResult(
                patterns=[],
                error_occurred=True,
                error_message=str(e)
            )