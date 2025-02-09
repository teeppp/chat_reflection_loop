"""パターン分析エンジン"""
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models.vertexai import VertexAIModel
import os

from .models import (
    Pattern,
    PatternCategory,
    PatternAnalysisResult,
    PatternResult,
    PatternAnalysisResponse,
    DynamicLabel
)

logger = logging.getLogger(__name__)

class PatternAnalyzer:
    """振り返り内容からパターンを分析するエンジン"""
    
    def __init__(self):
        model = VertexAIModel(os.getenv('VERTEXAI_LLM_DEPLOYMENT','gemini-2.0-pro-exp-02-05'))
        self.agent = Agent(
            model,
            result_type=PatternAnalysisResponse,
            system_prompt="""
            あなたはユーザーの行動パターンを分析する専門家です。
            振り返り内容から、ユーザーの具体的なパターンを抽出してください。
            必ず以下の形式でJSON応答を返してください：

            {
                "patterns": [
                    {
                        "pattern": "パターン名",
                        "category": "SYSTEMATIC_LEARNING/INTERACTIVE_LEARNING/PRACTICAL_LEARNING/IDEATION/PROJECT_MANAGEMENT/PROBLEM_SOLVING/QUICK_SOLUTION/DETAILED_GUIDANCE/EFFICIENCY_FOCUS/ORGANIZATION/COMMUNICATION/FEEDBACK",
                        "confidence": 0.8,
                        "context": ["このパターンが見つかった具体的な例や文脈"],
                        "related_patterns": ["関連するパターン名"]
                    }
                ]
            }

            各カテゴリの意味：
            # 学習スタイル
            - SYSTEMATIC_LEARNING: 体系的な学習アプローチ
            - INTERACTIVE_LEARNING: 対話的な学習スタイル
            - PRACTICAL_LEARNING: 実践的な学習方法

            # 創造プロセス
            - IDEATION: アイデア創出
            - PROJECT_MANAGEMENT: プロジェクト管理
            - PROBLEM_SOLVING: 問題解決アプローチ

            # 支援ニーズ
            - QUICK_SOLUTION: 即時的な解決策
            - DETAILED_GUIDANCE: 詳細なガイダンス
            - EFFICIENCY_FOCUS: 効率重視

            # 共通スキル
            - ORGANIZATION: 情報整理能力
            - COMMUNICATION: コミュニケーション
            - FEEDBACK: フィードバック活用
            """
        )
        self._initialize_pattern_templates()

    def _initialize_pattern_templates(self):
        """パターン検出用のテンプレートを初期化（フォールバック用）"""
        self.pattern_templates: Dict[PatternCategory, List[Dict[str, Any]]] = {
            PatternCategory.SYSTEMATIC_LEARNING: [
                {
                    "name": "体系的学習",
                    "keywords": ["順序", "体系", "ステップ", "順番", "段階"],
                    "confidence": 0.7
                }
            ]
        }

    async def analyze(self, content: str) -> PatternAnalysisResult:
        """振り返り内容を分析してパターンを検出"""
        try:
            # LLMによる分析を試行
            response = await self._full_analysis(content)
            if response and response.patterns:
                patterns = [p.to_pattern() for p in response.patterns]
                return self._create_result(patterns)
            
            # ヒューリスティック分析を試行
            patterns = self._heuristic_analysis(content)
            if patterns:
                return self._create_result(patterns)
            
            # 最小パターンを返す
            return self._create_result(self._minimum_patterns())
            
        except Exception as e:
            logger.error(f"Pattern analysis error: {str(e)}")
            return PatternAnalysisResult(
                patterns=self._minimum_patterns(),
                error_occurred=True,
                error_message=str(e)
            )

        # バリデータの設定
        @self.agent.result_validator
        async def validate_patterns(ctx: RunContext, result: PatternAnalysisResponse) -> PatternAnalysisResponse:
            """パターンの検証"""
            if not result.patterns:
                raise ModelRetry("パターンが検出されませんでした。再試行します。")
            
            # カテゴリとconfidenceの正規化
            for pattern in result.patterns:
                if not pattern.confidence:
                    pattern.confidence = 0.5
                pattern.confidence = max(0.0, min(1.0, pattern.confidence))
                
                if not pattern.context:
                    pattern.context = ["コンテキストなし"]
            
            return result

    async def _full_analysis(self, content: str) -> Optional[PatternAnalysisResponse]:
        """LLMを使用した完全なパターン分析"""
        try:
            message = f"""
            以下の振り返り内容から、ユーザーの行動パターンを分析してJSON形式で出力してください。
            必ず以下の形式に従ってください：

            ```json
            {
                "patterns": [
                    {
                        "pattern": "具体的なパターン名",
                        "category": "カテゴリ名(CODING_STYLE等)",
                        "confidence": 0.8,
                        "context": ["具体的な例や文脈"],
                        "related_patterns": ["関連するパターン名"]
                    }
                ]
            }
            ```

            分析対象の内容：
            {content}
            """

            result = await self.agent.run(message.strip())
            if not result.data:
                logger.error("Empty response from LLM")
                return None

            if isinstance(result.data, PatternAnalysisResponse):
                return result.data
            
            logger.error(f"Invalid response type: {type(result.data)}")
            return None

        except Exception as e:
            logger.error(f"Full analysis error: {str(e)}", exc_info=True)
            return None

    def _heuristic_analysis(self, content: str) -> List[Pattern]:
        """ヒューリスティックなパターン分析（フォールバック用）"""
        patterns = []
        normalized_content = ' '.join(content.lower().split())
        detected_patterns = set()  # 検出されたパターンを追跡

        # テンプレートベースのパターン検出
        for category, templates in self.pattern_templates.items():
            for template in templates:
                if any(kw.lower() in normalized_content for kw in template["keywords"]):
                    context = self._extract_context(content, template["keywords"])
                    detected_patterns.add(template["name"])
                    pattern = Pattern(
                        pattern=template["name"],
                        category=category,
                        confidence=template["confidence"],
                        context=context,
                        detected_at=datetime.utcnow(),
                        detection_method="heuristic",
                        related_patterns=[]  # 後で更新
                    )
                    patterns.append(pattern)
                    logger.info(f"Detected heuristic pattern: {template['name']} ({category})")

        # 関連パターンの設定
        if len(patterns) > 1:
            for pattern in patterns:
                pattern.related_patterns = [
                    p.pattern for p in patterns
                    if p.pattern != pattern.pattern
                ]
                logger.debug(f"Related patterns for {pattern.pattern}: {pattern.related_patterns}")

        return patterns

    def _extract_context(self, content: str, keywords: List[str]) -> List[str]:
        """キーワードの前後の文脈を抽出"""
        try:
            context = []
            sentences = re.split(r'[.。!！?？\n]', content)
            
            for sentence in sentences:
                if any(kw.lower() in sentence.lower() for kw in keywords):
                    cleaned = sentence.strip()
                    if cleaned:
                        context.append(cleaned)
                        logger.debug(f"Found context for keywords {keywords}: {cleaned[:50]}...")

            result = context[:3]  # 最大3つの文脈を返す
            if not result:
                logger.warning(f"No context found for keywords: {keywords}")
            return result

        except Exception as e:
            logger.error(f"Error extracting context: {e}")
            return ["コンテキスト抽出エラー"]

    def _minimum_patterns(self) -> List[Pattern]:
        """最小限のパターンセット（エラー時のフォールバック）"""
        logger.warning("Using minimum pattern fallback")
        return [
            Pattern(
                pattern="体系的学習",
                category=PatternCategory.SYSTEMATIC_LEARNING,
                confidence=0.6,
                context=["デフォルトパターン"],
                detected_at=datetime.utcnow(),
                detection_method="fallback",
                related_patterns=[]
            )
        ]

    def _create_result(self, patterns: List[Pattern]) -> PatternAnalysisResult:
        """分析結果を生成（パターンは一時的に無効化）"""
        return PatternAnalysisResult(
            patterns=[],  # パターン生成を無効化
            labels=[DynamicLabel(text=p.pattern) for p in patterns],  # パターンをラベルとして扱う
            clusters=[]  # クラスターは別途生成される
        )