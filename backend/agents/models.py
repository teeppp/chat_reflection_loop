"""共通のデータモデル定義"""
from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class PatternCategory(str, Enum):
    # 学習スタイル
    SYSTEMATIC_LEARNING = "SYSTEMATIC_LEARNING"      # 体系的な学習アプローチ
    INTERACTIVE_LEARNING = "INTERACTIVE_LEARNING"    # 対話的な学習スタイル
    PRACTICAL_LEARNING = "PRACTICAL_LEARNING"        # 実践的な学習方法
    
    # 創造プロセス
    IDEATION = "IDEATION"                           # アイデア創出
    PROJECT_MANAGEMENT = "PROJECT_MANAGEMENT"        # プロジェクト管理
    PROBLEM_SOLVING = "PROBLEM_SOLVING"             # 問題解決アプローチ
    
    # 支援ニーズ
    QUICK_SOLUTION = "QUICK_SOLUTION"               # 即時的な解決策
    DETAILED_GUIDANCE = "DETAILED_GUIDANCE"         # 詳細なガイダンス
    EFFICIENCY_FOCUS = "EFFICIENCY_FOCUS"           # 効率重視
    
    # 共通スキル
    ORGANIZATION = "ORGANIZATION"                    # 情報整理能力
    COMMUNICATION = "COMMUNICATION"                  # コミュニケーション
    FEEDBACK = "FEEDBACK"                           # フィードバック活用

    @classmethod
    def from_str(cls, value: str) -> 'PatternCategory':
        """文字列からカテゴリを取得（大文字小文字を無視）"""
        try:
            return cls[value.upper()]
        except KeyError:
            return cls.SYSTEMATIC_LEARNING

class PatternResult(BaseModel):
    """パターン分析の個別結果"""
    pattern: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: List[str]
    related_patterns: List[str] = []
    suggested_labels: List[str] = Field(default_factory=list)  # 推奨ラベル

    def to_pattern(self) -> 'Pattern':
        """PatternResultをPatternに変換"""
        return Pattern(
            pattern=self.pattern,
            category=PatternCategory.from_str(self.category),
            confidence=self.confidence,
            context=self.context,
            detected_at=datetime.utcnow(),
            detection_method="llm",
            related_patterns=self.related_patterns,
            suggested_labels=self.suggested_labels
        )

class PatternAnalysisResponse(BaseModel):
    """LLMからの応答形式"""
    patterns: List[PatternResult]

class Pattern(BaseModel):
    """検出されたパターン（永続化用）"""
    pattern: str
    category: PatternCategory
    confidence: float = Field(ge=0.0, le=1.0)
    context: List[str]
    detected_at: datetime
    detection_method: str  # 'llm', 'heuristic', 'fallback'
    related_patterns: List[str] = []
    suggested_labels: List[str] = Field(default_factory=list)  # 推奨ラベル

class ProfileLabel(BaseModel):
    """動的なプロファイルラベル"""
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: List[str]
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    occurrence_count: int = Field(default=1, ge=1)
    related_labels: List[str] = Field(default_factory=list)

class ProfileCluster(BaseModel):
    """関連するラベルのクラスター"""
    cluster_id: str
    main_theme: str
    labels: List[str]
    strength: float = Field(ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class PatternAnalysisResult(BaseModel):
    """パターン分析結果（永続化用）"""
    patterns: List[Pattern]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_occurred: bool = False
    error_message: Optional[str] = None