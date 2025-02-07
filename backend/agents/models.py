"""共通のデータモデル定義"""
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

class DynamicCategory(BaseModel):
    """動的なカテゴリー定義"""
    name: str
    description: str
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    parent_category: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime = Field(default_factory=datetime.utcnow)
    usage_count: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PatternResult(BaseModel):
    """パターン分析の個別結果"""
    pattern: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: List[str]
    related_patterns: List[str] = Field(default_factory=list)
    suggested_labels: List[str] = Field(default_factory=list)

    def to_pattern(self) -> 'Pattern':
        """PatternResultをPatternに変換"""
        return Pattern(
            pattern=self.pattern,
            category=self.category,
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

class PatternContext(BaseModel):
    """パターンのコンテキスト情報"""
    session_id: str
    title: str
    summary: str
    timestamp: datetime
    excerpt: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Pattern(BaseModel):
    """検出されたパターン（永続化用）"""
    pattern: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: Union[PatternContext, List[str]]
    detected_at: datetime
    detection_method: str
    related_patterns: List[str] = Field(default_factory=list)
    suggested_labels: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class DynamicLabel(BaseModel):
    """動的なプロファイルラベル"""
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: List[str]
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    occurrence_count: int = Field(default=1, ge=1)
    related_labels: List[str] = Field(default_factory=list)
    source_patterns: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    clusters: List[str] = Field(default_factory=list)

class LabelCluster(BaseModel):
    """関連するラベルのクラスター"""
    cluster_id: str
    theme: str
    labels: List[str]
    strength: float = Field(ge=0.0, le=1.0)
    center_point: Dict[str, float] = Field(default_factory=dict)
    radius: float = Field(ge=0.0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    parent_cluster: Optional[str] = None
    subclusters: List[str] = Field(default_factory=list)

class PatternAnalysisResult(BaseModel):
    """パターン分析結果（永続化用）"""
    patterns: List[Pattern]
    labels: List[DynamicLabel] = Field(default_factory=list)
    clusters: List[LabelCluster] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_occurred: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DynamicPatternEngine(BaseModel):
    """パターン分析エンジン設定"""
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    max_labels_per_pattern: int = Field(default=5, ge=1)
    clustering_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    label_similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    enabled_features: Dict[str, bool] = Field(
        default_factory=lambda: {
            "dynamic_categorization": True,
            "auto_clustering": True,
            "label_suggestion": True,
            "pattern_evolution": True
        }
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentInstruction(BaseModel):
    """エージェントへの指示"""
    role: str
    instructions: str
    priority: int

class ProfileInsightResult(BaseModel):
    """プロファイル分析結果"""
    primary_labels: List[str]
    clusters: List[LabelCluster]
    confidence: float
    reasoning: str

class UserTendency(BaseModel):
    """ユーザーの傾向"""
    label: str
    strength: float
    context: List[str]
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class UserProfile(BaseModel):
    """ユーザープロファイル"""
    user_id: str
    patterns: List[Pattern] = Field(default_factory=list)
    labels: List[DynamicLabel] = Field(default_factory=list)
    clusters: List[LabelCluster] = Field(default_factory=list)
    categories: List[DynamicCategory] = Field(default_factory=list)
    base_instructions: List[AgentInstruction] = Field(default_factory=list)
    personalized_instructions: Optional[str] = None
    insights: Optional[ProfileInsightResult] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tendencies: List[UserTendency] = Field(default_factory=list)

    def add_tendency(self, tendency: "UserTendency"):
        """傾向を追加"""
        # 既存の傾向を更新または新規追加
        for existing in self.tendencies or []:
            if existing.label == tendency.label:
                # 強度を平均化
                existing.strength = (existing.strength + tendency.strength) / 2
                # コンテキストを結合（重複を除去）
                existing.context = list(set(existing.context + tendency.context))
                existing.last_updated = datetime.utcnow()
                return
        
        # 新規追加
        self.tendencies.append(tendency)

    def update_clusters(self, new_clusters: List[LabelCluster]):
        """クラスターを更新"""
        self.clusters = new_clusters

    def add_category(self, category: DynamicCategory):
        """カテゴリーを追加"""
        # 既存のカテゴリーを更新または新規追加
        for existing in self.categories:
            if existing.name == category.name:
                existing.patterns.extend(category.patterns)
                return
        
        # 新規追加
        self.categories.append(category)

class ProfileInsightResult(BaseModel):
    """プロファイル分析結果"""
    primary_labels: List[str]
    clusters: List[LabelCluster]
    confidence: float
    reasoning: str