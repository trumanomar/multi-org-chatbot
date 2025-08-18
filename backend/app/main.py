from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.auth import routes as auth_routes
from app.auth import super_admin_route, admin_route
from app.Routes import BasicRoutes as basic_routes
from app.Routes import Uploadroute as upload_routes
from app.Routes.ChatRoute import router as chat_router
from app.Feedback.routes import post_route,get_route
load_dotenv()

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

# ── Include routers (prefixes are defined IN the modules themselves) ──
app.include_router(auth_routes.router)          # routes.py has prefix="/auth"
app.include_router(super_admin_route.router)    # super_admin_route.py will have prefix="/super-admin"
app.include_router(admin_route.router)          # admin_route.py has prefix="/admin"
app.include_router(upload_routes.router)        # Uploadroute.py has prefix="/admin"
app.include_router(basic_routes.router)         # /probe, /probe_scores
app.include_router(chat_router)     
app.include_router(post_route.app)
app.include_router(get_route.app)

    # defines /chat/*
