from fastapi import FastAPI, Request, HTTPException, Depends, Response, Query
from fastapi.responses import RedirectResponse, JSONResponse
from agents.base import agent as web_agent
from agents.reflection import ReflectionGenerator, ChatMessage as ReflectionChatMessage, ReflectionDocument
from repositories.reflection_repository import ReflectionRepository
from agents.profile_agent import ProfileAgent, ProfileUpdateRequest
from repositories.user_profile_repository import UserProfileRepository
from sse_starlette.sse import EventSourceResponse
import asyncio
from pydantic import BaseModel, Field
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
)
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import json
import traceback

# Firebase Admin SDKの初期化（Google Cloud環境用）
firebase_admin.initialize_app()
db = firestore.client()

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatHistory(BaseModel):
    """拡張されたチャット履歴モデル"""
    user_id: str
    session_id: str
    messages: List[Message] = []  # フロントエンド用の履歴
    raw_messages: bytes = b''  # PydanticAI用の生の履歴(JSON文字列)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = None
    reflection: Optional[dict] = None  # 振り返り情報

async def verify_firebase_token(request: Request):
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    
    token = authorization.split(" ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class CreateChatSessionRequest(BaseModel):
    initial_message: Optional[List[Message]] = None

class GenerateReflectionRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None

app = FastAPI(
    title="PydanticAI API",
    version="1.0",
    description="A simple api server for pydanticai",
    docs_url="/docs")

# OPTIONSリクエストに対して204を返す
@app.options("/{path:path}")
async def options_handler(request: Request):
    return Response(status_code=204)


# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発中は全てのオリジンを許可
    allow_credentials=True,  # Cookieなどの認証情報は不要
    # 全てのリクエストメソッドを許可(["GET", "POST"]など個別指定も可能)
    allow_methods=["*"],
    # アクセス可能なレスポンスヘッダーを設定（今回は必要ない）
    allow_headers=["*"],
)

# チャット履歴APIエンドポイント
@app.post("/api/v1/chat-histories")
async def create_chat_session(
    request: CreateChatSessionRequest,
    token: dict = Depends(verify_firebase_token)
):
    user_id = token["uid"]
    session_id = db.collection("chat_histories").document().id
    
    messages = []
    if request.initial_message:
        messages.extend(request.initial_message)
    
    chat_history = ChatHistory(
        user_id=user_id,
        session_id=session_id,
        messages=messages
    )
    
    try:
        db.collection("chat_histories").document(chat_history.session_id).set(
            chat_history.dict(exclude_none=True)
        )
        return {"session_id": chat_history.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def add_message_internal(session_id: str, message: Message, user_id: str) -> bool:
    """内部的にメッセージを追加する関数"""
    doc_ref = db.collection("chat_histories").document(session_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    chat_data = doc.to_dict()
    if chat_data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat session")
    
    try:
        doc_ref.update({
            "messages": firestore.ArrayUnion([message.dict()]),
            "updated_at": datetime.utcnow()
        })
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/chat-histories/{session_id}")
async def add_message(
    session_id: str,
    message: Message,
    token: dict = Depends(verify_firebase_token)
):
    """既存のメッセージ追加APIエンドポイント（後方互換性のため維持）"""
    user_id = token["uid"]
    success = await add_message_internal(session_id, message, user_id)
    return {"success": success}

@app.get("/api/v1/chat-histories")
async def get_chat_histories(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    token: dict = Depends(verify_firebase_token)
):
    user_id = token["uid"]
    try:
        query = db.collection("chat_histories")\
            .where("user_id", "==", user_id)\
            .order_by("updated_at", direction=firestore.Query.DESCENDING)\
            .offset((page - 1) * per_page)\
            .limit(per_page)
        
        docs = query.stream()
        histories = [doc.to_dict() for doc in docs]
        
        # 総件数を取得
        total_query = db.collection("chat_histories").where("user_id", "==", user_id)
        total = len(list(total_query.stream()))
        
        return {
            "histories": histories,
            "total": total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/chat-histories/{session_id}")
async def get_chat_session(
    session_id: str,
    token: dict = Depends(verify_firebase_token)
):
    user_id = token["uid"]
    doc = db.collection("chat_histories").document(session_id).get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    chat_data = doc.to_dict()
    if chat_data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat session")
    
    return {"history": chat_data}

@app.delete("/api/v1/chat-histories/clear")
async def clear_chat_histories(token: dict = Depends(verify_firebase_token)):
    user_id = token["uid"]
    try:
        # ユーザーIDに一致するドキュメントを検索
        query = db.collection("chat_histories").where("user_id", "==", user_id)
        docs = list(query.stream())
        
        if docs:  # ドキュメントが存在する場合のみ削除を実行
            # Firestoreのドキュメントを削除する処理を非同期で実行
            delete_tasks = [doc.reference.delete() for doc in docs]
            await asyncio.gather(*delete_tasks)
        
        # ドキュメントの有無に関わらず成功レスポンスを返す
        return {
            "success": True,
            "message": "Chat histories cleared successfully",
            "deleted_count": len(docs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/chat-histories/{session_id}")
async def delete_chat_session(
    session_id: str,
    token: dict = Depends(verify_firebase_token)
):
    user_id = token["uid"]
    doc_ref = db.collection("chat_histories").document(session_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    chat_data = doc.to_dict()
    if chat_data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat session")
    
    try:
        doc_ref.delete()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.middleware("http")
async def authenticate_requests(request: Request, call_next):
    # PreFlightリクエストと、docsへのアクセスは認証をスキップ
    if request.method == "OPTIONS" or request.url.path == "/docs" or request.url.path == "/openapi.json":
        return await call_next(request)
    
    try:
        await verify_firebase_token(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    
    return await call_next(request)

@app.get("/")
async def redirect_to_doc(token = Depends(verify_firebase_token)):
    return RedirectResponse(url="/docs")
@app.get("/health")
async def health_check():
    return {"status": "healthy"}



async def manage_chat_history(
    thread_id: Optional[str],
    user_id: str,
    user_message: str,
    assistant_response: Optional[str] = None,
    error_message: Optional[str] = None
) -> None:
    """チャット履歴を管理する関数"""
    if not thread_id:
        return

    try:
        # ユーザーメッセージを保存
        user_msg = Message(role="user", content=user_message)
        await add_message_internal(thread_id, user_msg, user_id)

        # アシスタントの応答を保存（存在する場合）
        if assistant_response is not None:
            assistant_msg = Message(role="assistant", content=assistant_response)
            await add_message_internal(thread_id, assistant_msg, user_id)

        # エラーメッセージを保存（存在する場合）
        if error_message is not None:
            error_msg = Message(role="system", content=error_message)
            await add_message_internal(thread_id, error_msg, user_id)

    except Exception as e:
        # 履歴保存のエラーはログに記録するが、メインの処理は継続
        print(f"Error saving chat history: {str(e)}")

@app.post("/baseagent/invoke")
async def invoke_agent(request: ChatRequest, token = Depends(verify_firebase_token)):
    user_id = token["uid"]
    thread_id = request.thread_id
    
    try:
        # セッションIDが存在する場合、Firestoreから履歴を取得
        message_history = None
        if thread_id:
            doc = db.collection("chat_histories").document(thread_id).get()
            if doc.exists:
                chat_data = doc.to_dict()
                if chat_data["user_id"] == user_id:
                    # 生の履歴からメッセージ履歴を復元
                    raw_messages = chat_data.get("raw_messages", "")
                    if raw_messages:
                        print("Debug - Retrieved raw_messages:", raw_messages)
                        message_history = ModelMessagesTypeAdapter.validate_json(raw_messages)
                        print("Debug - Parsed message_history:", message_history)
        
        # レスポンスとメッセージ履歴を取得
        response_text, all_messages_json = await invoke_generator(web_agent, request.message, message_history)
        # メッセージ履歴をFirestoreに保存
        if thread_id:
            try:
                # ユーザーメッセージを追加
                user_message = Message(
                    role="user",
                    content=request.message,
                    timestamp=datetime.utcnow()
                )
                
                # アシスタントメッセージを追加
                assistant_message = Message(
                    role="assistant",
                    content=response_text,
                    timestamp=datetime.utcnow()
                )
                
                # Firestoreを更新
                doc_ref = db.collection("chat_histories").document(thread_id)
                doc_ref.update({
                    "messages": firestore.ArrayUnion([
                        user_message.dict(),
                        assistant_message.dict()
                    ]),
                    "raw_messages": all_messages_json,  # 生の履歴を保存
                    "updated_at": datetime.utcnow()
                })
            except Exception as history_error:
                print(f"Failed to save chat history: {str(history_error)}")
                # 履歴保存の失敗は無視して処理を続行
        
        content = {
            "response": response_text,
            "thread_id": thread_id,
            "status": "success"
        }
        return Response(
            content=json.dumps(content, ensure_ascii=False).encode('utf-8'),
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except Exception as e:
        error_message = f"Error during agent execution: {str(e)}"
        
        # エラー時もセッションIDが存在する場合のみ履歴を保存
        if thread_id:
            try:
                error_msg = Message(role="system", content=error_message)
                await add_message_internal(thread_id, error_msg, user_id)
            except Exception as history_error:
                print(f"Failed to save error message to history: {str(history_error)}")
        
        raise HTTPException(status_code=500, detail=error_message)

@app.post("/baseagent/stream")
async def stream_agent(request: ChatRequest, token = Depends(verify_firebase_token)) -> EventSourceResponse:
    return EventSourceResponse(stream_generator(web_agent, request.message))

async def invoke_generator(agent, message, message_history=None):
    """非ストリーミングでの実行と履歴取得"""
    print("Debug - message_history in invoke_generator:", message_history)
    response = await agent.run(message, message_history=message_history, deps=True)
    # レスポンスと新規メッセージを返す
    return response.data, response.all_messages_json()

async def stream_generator(agent, message):
    """ストリーミング実行と履歴取得"""
    async with agent.run_stream(message) as result:
        async for text in result.stream(debounce_by=0.01):
            data = json.dumps({"text": text}, ensure_ascii=False)
            yield {
                "event": "message",
                "data": data
            }
        
        # ストリーミング完了後に全メッセージ履歴を送信
        all_messages = result.all_all_messages()
        yield {
            "event": "history",
            "data": all_messages
        }

# コンポーネント初期化
reflection_generator = ReflectionGenerator()
profile_repository = UserProfileRepository(db)
profile_agent = ProfileAgent(profile_repository)

# ユーザープロファイル管理エンドポイント
@app.post("/api/v1/profiles/{user_id}/analyze-reflection")
async def analyze_user_reflection(
    user_id: str,
    reflection: ReflectionDocument,
    token: dict = Depends(verify_firebase_token)
):
    """振り返りノートを分析してプロファイルを更新"""
    if token["uid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this profile")

    try:
        # プロファイル更新用の分析を実行
        analysis_result = await profile_agent.analyze_reflection(user_id, reflection.content)
        
        # 分析結果を返す（パターンのみ）
        return {
            "patterns": [p.dict() for p in analysis_result.patterns]
        }
    except Exception as e:
        print("Error in analyze_reflection:", str(e))
        print("Traceback:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# プロファイル分析結果取得用エンドポイント
class AnalyzeRequest(BaseModel):
    content: Optional[str] = None
    force_update: bool = False

@app.post("/api/v1/profiles/{user_id}/analyze")
async def analyze_user_patterns(
    user_id: str,
    request: AnalyzeRequest,
    token: dict = Depends(verify_firebase_token)
):
    """全振り返りノートの分析を実行して保存"""
    if token["uid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this profile")

    try:
        print(f"分析を開始: {user_id}")
        
        # 単一の振り返り内容がある場合はそれを分析
        if request.content:
            print("単一の振り返り内容を分析")
            result = await profile_agent.analyze_reflection(user_id, request.content)
            await profile_agent._update_profile_with_analysis(user_id, result)
            analyzed_count = 1
        
        # force_updateまたは振り返り内容が指定されていない場合は全履歴を分析
        elif request.force_update:
            print("全ての振り返りノートを分析")
            docs = db.collection("chat_histories")\
                .where("user_id", "==", user_id)\
                .stream()
            
            docs_list = list(docs)
            print(f"取得した振り返りノート数: {len(docs_list)}")

            analysis_tasks = []
            for doc in docs_list:
                data = doc.to_dict()
                if data.get("reflection") and data["reflection"].get("content"):
                    content = data["reflection"]["content"]
                    print(f"振り返りの内容: {content[:100]}...")  # 最初の100文字のみ表示
                    task = profile_agent.analyze_reflection(user_id, content)
                    analysis_tasks.append(task)

            print(f"分析タスク数: {len(analysis_tasks)}")
            if analysis_tasks:
                results = await asyncio.gather(*analysis_tasks)
                print(f"分析結果数: {len(results)}")
                # 各分析結果をプロファイルに反映
                for i, result in enumerate(results):
                    print(f"分析結果 {i + 1}: パターン数 = {len(result.patterns)}")
                    await profile_agent._update_profile_with_analysis(user_id, result)
                analyzed_count = len(analysis_tasks)
            else:
                analyzed_count = 0
        else:
            print("分析をスキップ（振り返り内容なし、force_update=false）")
            analyzed_count = 0

        return {
            "status": "success",
            "message": "分析が完了しました",
            "analyzed_count": analyzed_count
        }
    except Exception as e:
        logger.error(f"Error in analyze_user_reflections: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/profiles/{user_id}/analysis")
async def get_profile_analysis(
    user_id: str,
    token: dict = Depends(verify_firebase_token)
):
    """保存された分析結果を取得"""
    if token["uid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this profile")

    try:
        # 保存された分析結果を取得
        result = await profile_agent.get_profile_analysis(user_id)
        if not result:
            return {"patterns": [], "labels": [], "clusters": [], "categorized": {}}

        # カテゴリごとにパターンをグループ化
        categorized_patterns = {}
        for pattern in result.patterns:
            if pattern.pattern:  # 空のパターンは除外
                if pattern.category not in categorized_patterns:
                    categorized_patterns[pattern.category] = []
                categorized_patterns[pattern.category].append(pattern)

        # 各カテゴリ内で確信度でソート
        for patterns in categorized_patterns.values():
            patterns.sort(key=lambda p: p.confidence, reverse=True)

        return {
            "patterns": [p.dict() for p in result.patterns if p.pattern],
            "labels": [{"text": label.text} for label in result.labels],
            "clusters": [c.dict() for c in result.clusters],
            "categorized": {
                category: [p.dict() for p in patterns]
                for category, patterns in categorized_patterns.items()
            }
        }
    except Exception as e:
        print("Error in get_profile_analysis:", str(e))
        print("Traceback:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# 既存のエンドポイントを更新（キャッシュを活用）
@app.post("/api/v1/reflections/generate")
async def generate_reflection(
    request: GenerateReflectionRequest,
    token: dict = Depends(verify_firebase_token)
):
    """チャットセッションから振り返りメモを生成"""
    try:
        print("Debug - Starting reflection generation")
        
        # セッションの存在確認と権限チェック
        doc_ref = db.collection("chat_histories").document(request.session_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        chat_data = doc.to_dict()
        if chat_data["user_id"] != token["uid"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this chat session")

        # チャット履歴を変換
        chat_history = [
            ReflectionChatMessage(
                role=msg["role"],
                content=msg["content"]
            ) for msg in chat_data["messages"]
        ]

        # 振り返りメモを生成
        reflection = await reflection_generator.generate_reflection(chat_history)
        reflection.session_id = request.session_id
        reflection.user_id = token["uid"]
        reflection_dict = reflection.to_dict()

        # セッションIDが提供されている場合、そのセッションの振り返りを分析
        analysis_result = await profile_agent.analyze_reflection(
            token["uid"],
            reflection.content,
            session_id=reflection.session_id
        )

        # 振り返り情報とタイムスタンプを更新
        update_data = {
            "reflection": reflection_dict,
            "updated_at": datetime.utcnow()
        }
        
        try:
            # 非同期を使用せずに更新
            doc_ref.update(update_data)
            print("Debug - Reflection data updated successfully")
            
            return {
                "reflection": reflection_dict,
                "patterns": [p.dict() for p in analysis_result.patterns],
                "updated_at": update_data["updated_at"]
            }
        except Exception as update_error:
            print(f"Debug - Error updating reflection data: {str(update_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update reflection data: {str(update_error)}"
            )

    except Exception as e:
        print("Error in generate_reflection:", str(e))
        print("Traceback:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# 振り返り取得用エンドポイント
@app.get("/api/v1/reflections/session/{session_id}")
async def get_session_reflection(
    session_id: str,
    token: dict = Depends(verify_firebase_token)
):
    """セッションの振り返りメモを取得"""
    try:
        # セッションの存在と権限を確認
        doc = db.collection("chat_histories").document(session_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        chat_data = doc.to_dict()
        if chat_data["user_id"] != token["uid"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this chat session")
        
        if "reflection" not in chat_data:
            raise HTTPException(status_code=404, detail="Reflection not found for this session")

        return {"reflection": chat_data["reflection"]}

    except Exception as e:
        print("Error in get_session_reflection:", str(e))
        print("Traceback:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/profiles/{user_id}/analyze-reflection")
async def get_user_reflection_analysis(
    user_id: str,
    token: dict = Depends(verify_firebase_token)
):
    """ユーザーの分析結果を取得（キャッシュ活用）"""
    if token["uid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this profile")

    try:
        # キャッシュされた分析結果を取得
        cached_result = await profile_agent.get_cached_analysis(user_id)
        if cached_result:
            patterns = cached_result.patterns
        else:
            # キャッシュがない場合は保存されている最新の結果を返す
            profile = await profile_repository.get_profile(user_id)
            if not profile:
                return {"patterns": [], "categorized": {}}
            patterns = profile.patterns

        # カテゴリごとにパターンをグループ化
        categorized_patterns = {}
        for pattern in patterns:
            if pattern.category not in categorized_patterns:
                categorized_patterns[pattern.category] = []
            categorized_patterns[pattern.category].append(pattern)

        # 各カテゴリ内で確信度でソート
        for category in categorized_patterns:
            categorized_patterns[category].sort(key=lambda p: p.confidence, reverse=True)

        return {
            "patterns": [p.dict() for p in patterns],
            "categorized": {
                category: [p.dict() for p in patterns]
                for category, patterns in categorized_patterns.items()
            }
        }
    except Exception as e:
        print("Error in get_user_reflection_analysis:", str(e))
        print("Traceback:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/reflections/user")
async def get_user_reflections(token: dict = Depends(verify_firebase_token)):
    """ユーザーの全振り返りメモを取得"""
    try:
        user_id = token["uid"]
        docs = db.collection("chat_histories")\
            .where("user_id", "==", user_id)\
            .stream()
        
        reflections = []
        for doc in docs:
            data = doc.to_dict()
            if "reflection" in data:
                reflection = data["reflection"]
                reflection["session_id"] = doc.id
                reflections.append(reflection)

        return {"reflections": reflections}

    except Exception as e:
        print("Error in get_user_reflections:", str(e))  # エラーログ追加
        print("Traceback:", traceback.format_exc())  # スタックトレース追加
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)