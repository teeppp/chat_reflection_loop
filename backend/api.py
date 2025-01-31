from fastapi import FastAPI, Request, HTTPException, Depends, Response, Query
from fastapi.responses import RedirectResponse, JSONResponse
from agents.base import agent as web_agent
from sse_starlette.sse import EventSourceResponse
import asyncio
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import json

# Firebase Admin SDKの初期化（Google Cloud環境用）
firebase_admin.initialize_app()
db = firestore.client()

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatHistory(BaseModel):
    user_id: str
    session_id: str
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = None

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

class CreateChatSessionRequest(BaseModel):
    initial_message: Optional[Message] = None


# from api.routes import router
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

@app.put("/api/v1/chat-histories/{session_id}")
async def add_message(
    session_id: str,
    message: Message,
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
        doc_ref.update({
            "messages": firestore.ArrayUnion([message.dict()]),
            "updated_at": datetime.utcnow()
        })
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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



@app.post("/baseagent/invoke")
async def invoke_agent(request: ChatRequest, token = Depends(verify_firebase_token)):
    response = await invoke_generator(web_agent, request.message)
    content = {
        "response": response,
        "status": "success"
    }
    return Response(
        content=json.dumps(content, ensure_ascii=False).encode('utf-8'),
        media_type="application/json",
        headers={"Content-Type": "application/json; charset=utf-8"}
    )

@app.post("/baseagent/stream")
async def stream_agent(request: ChatRequest, token = Depends(verify_firebase_token)) -> EventSourceResponse:
    return EventSourceResponse(stream_generator(web_agent, request.message))

async def invoke_generator(agent, message):
    response = await agent.run(message)
    return response.data

async def stream_generator(agent, message):
    # response = web_agent.arun(message,stream=True)
    
    # レスポンスを小さなチャンクに分割して送信
        async with agent.run_stream(message) as result:
            async for text in result.stream(debounce_by=0.01):
                # text here is a `str` and the frontend wants
                # JSON encoded ModelResponse, so we create one
                data = json.dumps({"text": text}, ensure_ascii=False)
                yield {
                    "event": "message",
                    "data": data
                }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)