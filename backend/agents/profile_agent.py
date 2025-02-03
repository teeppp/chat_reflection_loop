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
            prompt = f"""
            以下の振り返り内容からユーザーの行動パターン・傾向を分析し、JSONで出力してください。
            パターンは以下のカテゴリに分類して分析してください：

            1. 情報収集スタイル（information_gathering）
               - 調査重視型：詳細な情報収集を重視
               - 実践重視型：実際の体験から学ぶことを重視
               - 要点重視型：必要最小限の情報に焦点を当てる
               - 網羅的収集型：幅広い情報を収集する

            2. コミュニケーションパターン（communication）
               - 詳細志向：細かい情報まで共有する
               - 簡潔志向：要点を簡潔に伝える
               - 対話重視：双方向のコミュニケーションを好む
               - 一方向型：情報提供に重点を置く

            3. 問題解決アプローチ（problem_solving）
               - 体系的解決型：段階的に問題を整理して解決
               - 試行錯誤型：実践しながら解決策を見出す
               - 分析重視型：原因や背景の分析を重視
               - 即効性重視型：すぐに実行できる解決策を求める

            4. 学習・成長パターン（learning）
               - 技術探求型：新しい技術や知識の習得に積極的
               - 実用重視型：実践的な活用方法の習得を重視
               - 概念理解型：基本概念や原理の理解を重視
               - 応用発展型：既存の知識を発展させることを重視

            分析対象の内容：
            {reflection_content}

            ※各パターンについて、確信度（0.0-1.0）と、その判断の根拠となる具体的な文脈を含めてください。
            ※振り返り内容から明確に判断できるパターンのみを抽出してください。
            ※ユーザーの一般的な行動傾向を理解することが目的です。
            出力形式：
            {
                "patterns": [
                    {
                        "pattern": "パターン名",
                        "category": "coding_style",  # coding_style, debugging, problem_solving, architecture
                        "confidence": 0.8,  # 0.0 to 1.0
                        "context": "このパターンが見つかった具体的な文脈や例"
                    }
                ]
            }
            """
            result = await self.pattern_agent.run(prompt, deps=True)
            
            # 応答をJSONとしてパース
            # パターンの抽出と変換
            patterns = []
            data = None
            
            try:
                if isinstance(result.data, str):
                    data = json.loads(result.data)
                else:
                    data = result.data
                    
                # パターンオブジェクトを生成
                if data and isinstance(data, dict) and 'patterns' in data:
                    for p in data['patterns']:
                        try:
                            pattern = UserPattern(
                                pattern=p.get('pattern', '未分類のパターン'),
                                category=p.get('category', 'general'),
                                confidence=float(p.get('confidence', 0.5)),
                                last_updated=datetime.utcnow(),
                                examples=[p.get('context', '文脈なし')]
                            )
                            patterns.append(pattern)
                        except (KeyError, ValueError, TypeError) as e:
                            print(f"Error parsing pattern: {e}")
                            continue
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
            except Exception as e:
                print(f"Unexpected error during pattern parsing: {e}")
            
            # パターンが見つからない場合はフォールバック
            if not patterns:
                print("No patterns found, using fallback pattern")
                patterns.append(UserPattern(
                    pattern="シンプル志向",
                    category="coding_style",
                    confidence=0.8,
                    last_updated=datetime.utcnow(),
                    examples=["振り返りから検出されたシンプルな実装への傾向"]
                ))

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