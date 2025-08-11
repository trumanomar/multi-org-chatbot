from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv() 

from app.Routes import BasicRoutes as basic_routes
from app.Routes import Uploadroute as upload_routes  
from app.Routes.ChatRoute import router as chat_router 



app = FastAPI(title="Document Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"ok": True}


app.include_router(upload_routes.router)   # /admin/upload
app.include_router(basic_routes.router)    # /probe, /probe_scores
app.include_router(chat_router)  # /chat