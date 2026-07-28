
import uvicorn
import uuid
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from prod_assistant.workflow.agentic_workflow_with_mcp_websearch import AgenticRAG

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- FastAPI Endpoints ----------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request,
        name="chat.html")


# @app.on_event("startup")
# async def startup():
#     app.state.rag_agent = AgenticRAG()
#     await app.state.rag_agent.initialize()


# @app.post("/get")
# async def chat(msg: str = Form(...)):
#     answer = await app.state.rag_agent.run(msg)
#     return answer

@app.on_event("startup")
async def startup():
    app.state.agent = AgenticRAG()
    await app.state.agent.async_init()


@app.post("/get")
async def chat(msg: str = Form(...)):
    # answer = await app.state.agent.run(msg)
    # return answer
    session_thread_id = str(uuid.uuid4())
    answer = await app.state.agent.run(msg, thread_id=session_thread_id)
    return answer


# uvicorn prod_assistant.router.main:app --reload --port 8001