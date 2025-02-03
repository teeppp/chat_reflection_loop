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
    initial_message: Optional[Message] = None

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
        messages.append(request.initial_message)
    
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
    """ユーザーの全振り返りノートからパターンを分析"""
    if token["uid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this profile")

    try:
        # Firestoreから振り返りノートを取得（user_idのみでフィルタリング）
        print(f"Fetching reflections for user: {user_id}")
        docs = db.collection("chat_histories")\
            .where("user_id", "==", user_id)\
            .stream()

        reflection_contents = []
        for doc in docs:
            data = doc.to_dict()
            # Pythonでreflectionフィールドの存在チェック
            if data.get("reflection") and data["reflection"].get("content"):
                content = data["reflection"]["content"]
                print(f"Found reflection: {content[:100]}...")  # 最初の100文字をログ
                reflection_contents.append(content)

        if not reflection_contents:
            print("No reflection notes found for analysis")
            return {"patterns": []}

        all_patterns = []
        for content in reflection_contents:
            print(f"Analyzing reflection... {len(content)} characters")
            patterns = await profile_agent.analyze_reflection(user_id, content)
            print(f"Found patterns in categories: {set(p.category for p in patterns)}")
            for p in patterns:
                print(f"  - {p.category}: {p.pattern} ({p.confidence})")
            all_patterns.extend(patterns)
        
        # カテゴリごとにパターンをグループ化
        categorized_patterns = {}
        for pattern in all_patterns:
            if pattern.category not in categorized_patterns:
                categorized_patterns[pattern.category] = []
            categorized_patterns[pattern.category].append(pattern)
        
        # 各カテゴリ内で確信度でソート
        for category in categorized_patterns:
            categorized_patterns[category].sort(key=lambda p: p.confidence, reverse=True)
        
        return {
            "patterns": [p.dict() for p in all_patterns],
            "categorized": {
                category: [p.dict() for p in patterns]
                for category, patterns in categorized_patterns.items()
            }
        }
    except Exception as e:
        print("Error in analyze_user_reflection:", str(e))
        print("Traceback:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/profiles/{user_id}/instructions/{role}")
async def get_profile_instructions(
    user_id: str,
    role: str,
    token: dict = Depends(verify_firebase_token)
):
    """ユーザー固有の指示を取得"""
    if token["uid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this profile")

    try:
        # 有効な役割かどうかを確認
        if role not in ProfileAgent.VALID_ROLES:
            raise HTTPException(status_code=404, detail=f"Invalid role: {role}")

        instructions = await profile_agent.generate_personalized_instructions(user_id, role)
        if instructions is None:
            # プロファイルが存在しない場合は404を返す
            raise HTTPException(
                status_code=404,
                detail="Profile not found or instructions not available for this role"
            )
        return {"instructions": instructions}
    except HTTPException:
        raise
    except Exception as e:
        print("Error in get_profile_instructions:", str(e))
        print("Traceback:", traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get profile instructions: {str(e)}"
        )


@app.post("/api/v1/reflections/generate")
async def generate_reflection(
    request: GenerateReflectionRequest,
    token: dict = Depends(verify_firebase_token)
):
    """チャットセッションから振り返りメモを生成"""
    try:
        print("Debug - Starting reflection generation")  # デバッグログ追加
        
        # セッションの存在確認
        doc_ref = db.collection("chat_histories").document(request.session_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        chat_data = doc.to_dict()
        if chat_data["user_id"] != token["uid"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this chat session")

        # チャット履歴をReflectionChatMessage形式に変換
        chat_history = [
            ReflectionChatMessage(
                role=msg["role"],
                content=msg["content"]
            ) for msg in chat_data["messages"]
        ]

        print("Debug - Chat History:", chat_history)  # デバッグログ追加

        # 振り返りメモの生成
        reflection = await reflection_generator.generate_reflection(chat_history)
        
        print("Debug - Generated Reflection:", reflection)  # デバッグログ追加

        # セッションIDとユーザーIDを設定
        reflection.session_id = request.session_id
        reflection.user_id = token["uid"]

        # 振り返り情報をチャット履歴に追加
        reflection_dict = reflection.to_dict()
        print("Debug - Reflection Dict:", reflection_dict)  # デバッグログ追加

        # プロファイルの更新を試みる
        try:
            patterns = await profile_agent.update_from_reflection(token["uid"], reflection.content)
            print("Debug - Updated Patterns:", [p.dict() for p in patterns])  # デバッグログ追加
        except Exception as profile_error:
            print("Warning - Profile update failed:", str(profile_error))
            print("Traceback:", traceback.format_exc())
            patterns = []

        doc_ref.update({
            "reflection": reflection_dict
        })

        # 振り返りと更新されたパターンを返す
        return {
            "reflection": reflection_dict,
            "patterns": [p.dict() for p in patterns]
        }

    except Exception as e:
        print("Error in generate_reflection:", str(e))  # エラーログ追加
        print("Traceback:", traceback.format_exc())  # スタックトレース追加
        raise HTTPException(status_code=500, detail=str(e))

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
        print("Error in get_session_reflection:", str(e))  # エラーログ追加
        print("Traceback:", traceback.format_exc())  # スタックトレース追加
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