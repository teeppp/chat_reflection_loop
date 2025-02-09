"""動的パターン分析エンジン"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np
from sklearn.cluster import DBSCAN
from collections import defaultdict
import logging
from pydantic import BaseModel
import json
import google.auth
from pydantic_ai.agent import Agent
from pydantic_ai.agent import RunContext
from pydantic_ai.models.vertexai import VertexAIModel
import os

from .models import (
    Pattern,
    DynamicLabel,
    LabelCluster,
    DynamicCategory,
    DynamicPatternEngine,
    PatternAnalysisResult,
    PatternContext
)
from .llm_schemas import DynamicLabelAnalysis

logger = logging.getLogger(__name__)

class VectorizedLabel(BaseModel):
    """ベクトル化されたラベル"""
    label: DynamicLabel
    vector: List[float]

class PatternAnalysisEngine:
    """動的パターン分析エンジン"""
    def __init__(
        self,
        config: Optional[DynamicPatternEngine] = None,
        model: Optional[VertexAIModel] = None
    ):
        """Initialize PatternAnalysisEngine with configuration and LLM model"""
        self.config = config or DynamicPatternEngine()
        
        # Initialize Vertex AI model if not provided
        if model is None:
            credentials, project = google.auth.default()
            model = VertexAIModel(os.getenv('VERTEXAI_LLM_DEPLOYMENT','gemini-2.0-pro-exp-02-05'))
        
        # Initialize agent for label generation with system prompt
        self.agent = Agent(
            model,
            result_type=DynamicLabelAnalysis,
            system_prompt="""あなたは、ユーザーの振り返りメモから、その人の独自の特徴や行動パターンを抽出する専門家です。
            ユーザーの個性的な特徴をハッシュタグ形式で表現してください。
            
            重要な注意点：
            1. 分類や定型的な表現は避け、その人らしさが表れている具体的な特徴を見つけ出してください
            2. 行動、思考、コミュニケーションスタイルなど、多角的な観点から特徴を抽出してください
            3. 特に以下の要素に注目してください：
               - 独特な問題解決アプローチ
               - 特徴的なコミュニケーションパターン
               - 興味・関心の方向性
               - 意思決定の傾向
               - 学習・理解のスタイル"""
        )
        self._vectorized_labels: Dict[str, VectorizedLabel] = {}
        self._label_clusters: Dict[str, LabelCluster] = {}

    async def analyze_pattern(self, content: str) -> PatternAnalysisResult:
        """パターンを分析し、ラベルとクラスターを生成"""
        try:
            # パターンから候補ラベルを抽出
            labels = await self._extract_labels(content)
            
            # ラベルをベクトル化
            vectorized_labels = await self._vectorize_labels(labels)
            
            # クラスタリングを実行
            clusters = await self._cluster_labels(vectorized_labels) if labels else []
            
            # パターンコンテキストを作成
            pattern_context = PatternContext(
                session_id="dynamic",
                title="Dynamic Pattern Analysis",
                summary=content[:100],  # 最初の100文字をサマリーとして使用
                timestamp=datetime.utcnow(),
                excerpt=content,
                metadata={"source": "dynamic_analysis"}
            )

            # パターン分析を実行
            patterns = []
            for label in labels:
                pattern = Pattern(
                    pattern=label.text,  # ラベルをパターンとして使用
                    category="dynamic",  # 動的カテゴリー
                    confidence=label.confidence,
                    context=pattern_context,
                    detected_at=datetime.utcnow(),
                    detection_method="dynamic_analysis",
                    related_patterns=[l.text for l in labels if l.text != label.text],
                    suggested_labels=[l.text for l in labels]
                )
                patterns.append(pattern)

            return PatternAnalysisResult(
                patterns=patterns,  # パターンのリストを返す
                labels=labels,
                clusters=clusters
            )

        except Exception as e:
            logger.error(f"Error in pattern analysis: {str(e)}")
            return PatternAnalysisResult(
                patterns=[],
                error_occurred=True,
                error_message=str(e)
            )

    async def _extract_labels_with_llm(self, content: str) -> List[DynamicLabel]:
        """LLMを使用してラベルを抽出"""
        try:
            # LLMから応答を取得し、JSONとしてパース
            result = await self.agent.run(
                f"以下の振り返りメモから、ユーザーの特徴を抽出してください：\n\n{content}"
            )
            
            # 応答データをモデルにバリデーション
            analysis = DynamicLabelAnalysis.model_validate(result.data)
            
            # DynamicLabelに変換して返却
            return [
                DynamicLabel(
                    text=label.text,
                    confidence=label.confidence,
                    context=label.context,
                    occurrence_count=label.occurrence_count
                )
                for label in analysis.labels
            ]
            
        except Exception as e:
            logger.error(f"Error in LLM label extraction: {str(e)}")
            return []

    async def _extract_labels(self, content: str) -> List[DynamicLabel]:
        """テキストから動的ラベルを抽出"""
        try:
            # LLMを使用してラベルを抽出
            labels = await self._extract_labels_with_llm(content)
            
            # 信頼度でフィルタリング
            filtered_labels = [
                label for label in labels 
                if label.confidence >= self.config.min_confidence
            ]
            
            # 最大ラベル数に制限
            return filtered_labels[:self.config.max_labels_per_pattern]
        
        except Exception as e:
            logger.error(f"Error in label extraction: {str(e)}")
            return []

    async def _vectorize_labels(
        self,
        labels: List[DynamicLabel]
    ) -> Dict[str, VectorizedLabel]:
        """ラベルをベクトル化"""
        vectorized = {}
        for label in labels:
            try:
                # 簡易的なベクトル化（実際の実装ではembedding APIを使用）
                vector = np.random.rand(1).tolist()  # スカラー値として扱う
                
                vectorized[label.text] = VectorizedLabel(
                    label=label,
                    vector=vector
                )
                
            except Exception as e:
                logger.error(f"Error vectorizing label {label.text}: {str(e)}")
                continue
                
        return vectorized

    async def _cluster_labels(
        self,
        vectorized_labels: Dict[str, VectorizedLabel]
    ) -> List[LabelCluster]:
        """ラベルをクラスタリング"""
        if len(vectorized_labels) < 2:
            return []

        try:
            # ベクトルを行列に変換
            vectors = np.array([vl.vector for vl in vectorized_labels.values()])
            
            # クラスタリングのデバッグログ
            logger.info(f"Clustering {len(vectorized_labels)} labels")
            logger.info(f"Vectors shape: {vectors.shape}")

            # DBSCANでクラスタリング - パラメータを調整
            clustering = DBSCAN(
                eps=0.5,  # より緩い閾値
                min_samples=1,  # 最小サンプル数を1に
                metric='euclidean'
            ).fit(vectors)
            
            # クラスタリング結果のデバッグログ
            logger.info(f"Clustering labels: {clustering.labels_}")
            
            # クラスターを生成
            clusters = defaultdict(list)
            for label_text, label_cluster in zip(vectorized_labels.keys(), clustering.labels_):
                clusters[str(label_cluster)].append(label_text)
            
            # クラスター生成のデバッグログ
            logger.info(f"Creating clusters from {len(clusters)} groups")
            
            # LabelClusterオブジェクトを作成
            result_clusters = []
            for cluster_id, label_texts in clusters.items():
                logger.info(f"Processing cluster {cluster_id} with {len(label_texts)} labels")
                
                try:
                    # クラスターの中心を計算
                    cluster_vectors = [
                        vectorized_labels[label_text].vector[0]
                        for label_text in label_texts
                    ]
                    center = float(np.mean(cluster_vectors))
                    radius = float(max(abs(center - v) for v in cluster_vectors)) if len(cluster_vectors) > 1 else 0.1
                    
                    # center_pointをモデルの形式に合わせて保存
                    center_point = {
                        "x": center,
                        "y": 0.0,
                        "z": 0.0
                    }
                    
                    cluster = LabelCluster(
                        cluster_id=f"cluster_{cluster_id}",
                        theme=self._generate_cluster_theme(label_texts),
                        labels=label_texts,
                        strength=1.0,  # 固定値を使用
                        center_point=center_point,
                        radius=radius
                    )
                    result_clusters.append(cluster)
                    logger.info(f"Created cluster: {cluster.model_dump_json()}")
                    
                except Exception as e:
                    logger.error(f"Error creating cluster {cluster_id}: {str(e)}")
                    continue
            
            return result_clusters
            
        except Exception as e:
            logger.error(f"Error in clustering: {str(e)}")
            return []

    def _generate_cluster_theme(self, labels: List[str]) -> str:
        """クラスターのテーマを生成"""
        # 簡易的な実装：最も頻出する単語を使用
        words = [
            word
            for label in labels
            for word in label.replace("#", "").split("_")
        ]
        if not words:
            return "未分類クラスター"
            
        word_counts = defaultdict(int)
        for word in words:
            word_counts[word] += 1
            
        most_common = max(word_counts.items(), key=lambda x: x[1])[0]
        return f"#{most_common}関連"