from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from agents.base import agent as web_agent
from sse_starlette.sse import EventSourceResponse
import asyncio
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, auth
import os

# Firebase Admin SDKの初期化（Google Cloud環境用）
firebase_admin.initialize_app()

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

# from api.routes import router
app = FastAPI(
    title="PydanticAI API",
    version="1.0",
    description="A simple api server for pydanticai",
    docs_url="/docs")

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # フロントエンドのオリジンを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def authenticate_requests(request: Request, call_next):
    if request.url.path == "/docs" or request.url.path == "/openapi.json":
        return await call_next(request)
    
    try:
        await verify_firebase_token(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    
    return await call_next(request)

@app.get("/")
async def redirect_to_doc():
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check(token = Depends(verify_firebase_token)):
    return {"status": "healthy"}


@app.post("/baseagent/invoke")
async def invoke_agent(request: ChatRequest, token = Depends(verify_firebase_token)):
    response = await invoke_generator(web_agent, request.message)
    return JSONResponse({
        "response": response,
        "status": "success"
    })

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
                yield {
                    "event": "message",
                    "data": text
                }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)