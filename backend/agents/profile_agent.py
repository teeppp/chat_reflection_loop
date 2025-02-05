"""ユーザープロファイル管理のエージェントクラス"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
import logging
import traceback

from pydantic_ai.agent import Agent
from pydantic_ai.agent import RunContext
from pydantic_ai.models.vertexai import VertexAIModel
import google.auth

from agents.pattern_analysis_engine import PatternAnalysisEngine
from agents.models import (
    Pattern,
    DynamicLabel,
    LabelCluster,
    DynamicCategory,
    DynamicPatternEngine,
    PatternAnalysisResult,
    ProfileInsightResult
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

class LastAnalysis(BaseModel):
    """最後の分析情報"""
    timestamp: datetime
    content_hash: str
    result: PatternAnalysisResult

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
        
        # 最後の分析情報を保持
        self._last_analysis: Dict[str, LastAnalysis] = {}

    def _generate_content_hash(self, content: str) -> str:
        """コンテンツのハッシュを生成"""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()

    async def _get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """チャットセッション情報を取得"""
        try:
            doc = self.repository.db.collection("chat_histories").document(session_id).get()
            if doc.exists:
                data = doc.to_dict()
                return {
                    'title': data.get('title', '不明なセッション'),
                    'created_at': data.get('created_at', datetime.utcnow()),
                    'reflection': data.get('reflection', {}).get('content', '')
                }
        except Exception as e:
            logger.error(f"セッション情報取得エラー: {e}")
        return None

    def _convert_to_user_pattern(self, pattern: Pattern, session_info: Optional[Dict[str, Any]] = None) -> UserPattern:
        """PatternをUserPatternに変換（バリデーション付き）"""
        try:
            # コンテキストデータの取得と変換
            context_data = {}

            if hasattr(pattern, 'context') and pattern.context:
                if isinstance(pattern.context, (dict, list)):
                    # 古い形式のデータを新しい形式に変換
                    if isinstance(pattern.context, list):
                        # リスト形式の古いデータ
                        context_str = pattern.context[0] if pattern.context else ""
                        context_data = {
                            'session_id': 'legacy_session',
                            'title': '過去の振り返り',
                            'summary': context_str,
                            'timestamp': datetime.utcnow().isoformat(),
                            'excerpt': context_str[:100] if context_str else ''
                        }
                    else:
                        # 辞書形式の古いデータ（必須フィールドを確実に含める）
                        context_data = {
                            'session_id': pattern.context.get('session_id', 'legacy_session'),
                            'title': pattern.context.get('title', '過去の振り返り'),
                            'summary': pattern.context.get('summary', ''),
                            'timestamp': pattern.context.get('timestamp', datetime.utcnow().isoformat()),
                            'excerpt': pattern.context.get('excerpt', '')
                        }
                else:
                    # PatternContextオブジェクトから変換
                    context_data = {
                        'session_id': pattern.context.session_id,
                        'title': pattern.context.title,
                        'summary': pattern.context.summary,
                        'timestamp': pattern.context.timestamp.isoformat(),
                        'excerpt': pattern.context.excerpt
                    }
            elif session_info:
                # セッション情報から新規コンテキストを作成
                context_data = {
                    'session_id': session_info.get('session_id', 'new_session'),
                    'title': session_info.get('title', '新規セッション'),
                    'summary': session_info.get('reflection', '')[:200],
                    'timestamp': session_info.get('created_at', datetime.utcnow()).isoformat(),
                    'excerpt': session_info.get('reflection', '')[:100]
                }
            else:
                # デフォルトコンテキスト
                context_data = {
                    'session_id': 'default_session',
                    'title': 'デフォルトセッション',
                    'summary': '',
                    'timestamp': datetime.utcnow().isoformat(),
                    'excerpt': ''
                }

            return UserPattern(
                pattern=pattern.pattern,
                category=pattern.category or "behavioral",
                confidence=pattern.confidence or 0.5,
                last_updated=pattern.detected_at or datetime.utcnow(),
                context=context_data
            )
        except Exception as e:
            logger.error(f"Pattern conversion error: {str(e)}, pattern: {pattern}")
            logger.info("デフォルト値でパターンを作成します")
            # デフォルト値で作成
            return UserPattern(
                pattern=pattern.pattern,
                category="behavioral",
                confidence=0.5,
                last_updated=datetime.utcnow(),
                examples=[]
            )

    async def analyze_reflection(
        self,
        user_id: str,
        reflection_content: str,
        session_id: Optional[str] = None
    ) -> PatternAnalysisResult:
        """振り返りからパターンを分析（差分チェック付き）"""
        try:
            if not reflection_content.strip():
                return PatternAnalysisResult(patterns=[], error_occurred=True, error_message="空の内容です")

            # コンテンツのハッシュを計算
            content_hash = self._generate_content_hash(reflection_content)
            
            # 前回の分析結果をチェック
            last = self._last_analysis.get(user_id)
            if last and last.content_hash == content_hash:
                logger.info("キャッシュされた分析結果を使用")
                return last.result

            # セッション情報を取得
            session_info = None
            if session_id:
                session_info = await self._get_session_info(session_id)
                logger.info(f"セッション情報を取得: {session_info}")

            # 動的パターン分析を実行
            analysis_result = await self.pattern_engine.analyze_pattern(reflection_content)
            
            if analysis_result.error_occurred:
                logger.warning(f"Pattern analysis error: {analysis_result.error_message}")
                return analysis_result

            timestamp = datetime.utcnow()  # タイムスタンプを定義
            
            # パターンを整形
            patterns = []
            logger.info(f"検出されたパターン: {len(analysis_result.patterns)}")
            if analysis_result.patterns:
                for p in analysis_result.patterns:
                    if not p.pattern:  # 空のパターンは除外
                        continue
                    try:
                        # パターンのコンテキストを作成
                        pattern_context = PatternContext(
                            session_id=session_id or "unknown",
                            title=session_info['title'] if session_info else "不明なセッション",
                            summary=reflection_content[:200],  # 振り返りの冒頭を要約として使用
                            timestamp=timestamp,
                            excerpt=reflection_content[:100] if reflection_content else '',
                            metadata={
                                'source': 'reflection_analysis',
                                'pattern_type': p.category or 'behavioral'
                            }
                        )

                        # Patternモデルに変換（必須フィールドを設定）
                        pattern = Pattern(
                            pattern=p.pattern,
                            category=p.category or "behavioral",
                            confidence=p.confidence,
                            context=pattern_context,
                            detected_at=timestamp,
                            detection_method="llm_analysis"
                        )
                        patterns.append(pattern)
                        logger.info(f"パターン変換: {pattern.pattern}")
                    except Exception as pattern_error:
                        logger.error(f"パターン変換エラー: {str(pattern_error)}")
                        continue

            # 検出されたラベルを追加
            labels = []
            if analysis_result.labels:
                logger.info(f"検出されたラベル: {len(analysis_result.labels)}")
                for label in analysis_result.labels:
                    try:
                        if not label.text:  # 空のラベルをスキップ
                            continue
                        dynamic_label = DynamicLabel(
                            text=label.text,
                            confidence=label.confidence,
                            context=[reflection_content[:200]]  # デフォルトコンテキスト
                        )
                        labels.append(dynamic_label)
                    except Exception as label_error:
                        logger.error(f"ラベル変換エラー: {str(label_error)}")
                        continue

            # 結果を組み合わせて返す
            analysis_result = PatternAnalysisResult(
                patterns=patterns,
                labels=labels,
                clusters=[],  # クラスターは後で生成
                error_occurred=False,
                timestamp=timestamp  # タイムスタンプを設定
            )
            
            try:
                # プロファイルを更新
                await self._update_profile_with_analysis(user_id, analysis_result)
                logger.info(f"プロファイル更新完了: {user_id}")
                
                # 分析結果を保存
                self._last_analysis[user_id] = LastAnalysis(
                    timestamp=timestamp,
                    content_hash=content_hash,
                    result=analysis_result
                )
                logger.info("分析結果をキャッシュに保存")
                
                return analysis_result
                
            except Exception as e:
                logger.error(f"Error updating profile: {str(e)}")
                return PatternAnalysisResult(
                    patterns=[],
                    error_occurred=True,
                    error_message=f"プロファイルの更新中にエラーが発生しました: {str(e)}"
                )
            
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
            logger.info(f"プロファイル更新開始: ユーザー={user_id}")
            success_count = {"patterns": 0, "labels": 0, "clusters": 0}
            error_count = {"patterns": 0, "labels": 0, "clusters": 0}

            # パターンを更新
            for pattern in analysis.patterns:
                try:
                    user_pattern = self._convert_to_user_pattern(pattern)
                    await self.repository.add_pattern(user_id, user_pattern)
                    success_count["patterns"] += 1
                    logger.info(f"パターン保存成功: {pattern.pattern}")
                except Exception as e:
                    error_count["patterns"] += 1
                    logger.error(f"パターン保存エラー: {str(e)}, パターン: {pattern.pattern}")
                    continue
            
            # ラベルを更新
            for label in analysis.labels:
                try:
                    if not label.text:
                        continue
                    await self.repository.add_label(user_id, label)
                    success_count["labels"] += 1
                    logger.info(f"ラベル保存成功: {label.text}")
                except Exception as e:
                    error_count["labels"] += 1
                    logger.error(f"ラベル保存エラー: {str(e)}, ラベル: {label.text}")
                    continue
            
            # クラスターを更新
            for cluster in analysis.clusters:
                try:
                    if not cluster.labels:
                        continue
                    await self.repository.update_cluster(user_id, cluster)
                    success_count["clusters"] += 1
                    logger.info(f"クラスター保存成功: {cluster.theme}")
                except Exception as e:
                    error_count["clusters"] += 1
                    logger.error(f"クラスター保存エラー: {str(e)}, クラスター: {cluster.theme}")
                    continue

            logger.info(f"プロファイル更新完了 - 成功数: {success_count}, エラー数: {error_count}")
                
        except Exception as e:
            logger.error(f"プロファイル更新中の重大なエラー: {str(e)}")
            raise

    async def get_profile_analysis(
        self,
        user_id: str
    ) -> Optional[PatternAnalysisResult]:
        """保存された分析結果を取得（レガシーデータ対応）"""
        """保存された分析結果を取得"""
        try:
            logger.info(f"プロファイル分析結果の取得開始: {user_id}")
            
            profile = await self.repository.get_profile(user_id)
            if not profile:
                logger.warning(f"プロファイルが見つかりません: {user_id}")
                return None

            logger.info(f"プロファイル取得成功: パターン数={len(profile.patterns)}, "
                       f"ラベル数={len(profile.labels)}, "
                       f"クラスター数={len(profile.clusters)}")

            # パターンの詳細をログ出力
            for i, p in enumerate(profile.patterns):
                logger.info(f"パターン {i + 1}: {p.pattern} "
                          f"(カテゴリ={p.category}, 確信度={p.confidence})")

            # プロファイルからパターンを変換
            patterns = []
            for p in profile.patterns:
                try:
                    # レガシーデータのコンテキスト変換
                    pattern_context = None
                    if isinstance(p.context, dict):
                        # 新しい形式のデータ
                        pattern_context = PatternContext(
                            session_id=p.context.get('session_id', 'legacy'),
                            title=p.context.get('title', '過去の振り返り'),
                            summary=p.context.get('summary', ''),
                            timestamp=datetime.utcnow(),
                            excerpt=p.context.get('excerpt', ''),
                            metadata=p.context.get('metadata', {})
                        )
                    else:
                        # レガシーデータを変換
                        context_text = p.context[0] if isinstance(p.context, list) and p.context else str(p.context) if p.context else ''
                        pattern_context = PatternContext(
                            session_id='legacy',
                            title='過去の振り返り',
                            summary=context_text,
                            timestamp=datetime.utcnow(),
                            excerpt=context_text[:100] if context_text else '',
                            metadata={'legacy_data': True}
                        )

                    pattern = Pattern(
                        pattern=p.pattern,
                        category=p.category,
                        confidence=p.confidence,
                        detected_at=datetime.utcnow(),
                        detection_method="analysis",
                        context=pattern_context
                    )
                    patterns.append(pattern)
                    logger.info(f"パターン読み込み成功: {pattern.pattern}")
                except Exception as e:
                    logger.error(f"パターン変換エラー: {str(e)}")
                    continue

            # 結果を作成
            result = PatternAnalysisResult(
                patterns=patterns,
                labels=profile.labels or [],
                clusters=profile.clusters or [],
                error_occurred=False,
                timestamp=datetime.utcnow()
            )

            logger.info("分析結果の変換が完了しました")
            return result

        except Exception as e:
            logger.error(f"Error in get_profile_analysis: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
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

        # 最後の分析情報をクリア
        if user_id in self._last_analysis:
            del self._last_analysis[user_id]