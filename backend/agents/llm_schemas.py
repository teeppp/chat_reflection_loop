"""LLMの出力スキーマ定義"""
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai.agent import RunContext

class LabelResponse(BaseModel):
    """LLMが生成するラベルの形式"""
    text: str = Field(..., description="ハッシュタグ形式のラベル")
    confidence: float = Field(..., description="確信度（0-1の範囲）", ge=0.0, le=1.0)
    context: List[str] = Field(..., description="ラベルの根拠となる文脈")
    occurrence_count: int = Field(default=1, description="出現回数")
    first_seen: datetime = Field(default_factory=datetime.utcnow, description="最初の検出日時")
    last_seen: datetime = Field(default_factory=datetime.utcnow, description="最後の検出日時")

class DynamicLabelAnalysis(BaseModel):
    """振り返りメモからの動的ラベル分析結果"""
    labels: List[LabelResponse] = Field(..., description="抽出されたラベルのリスト")
    analysis_confidence: float = Field(..., description="分析全体の確信度", ge=0.0, le=1.0)