from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.auth import routes as auth_routes
from app.Routes import BasicRoutes as basic_routes
from app.Routes import Uploadroute as upload_routes  
from app.Routes.ChatRoute import router as chat_router 
from app.auth import super_admin_route 
from app.auth import admin_route
load_dotenv() 

app = FastAPI(title="Document Chatbot API")

app.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])

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
app.include_router(chat_router)
app.include_router(auth_routes.router)
app.include_router(super_admin_route.router, prefix="/super-admin", tags=["Super Admin"])
app.include_router(admin_route.router, prefix="/admin", tags=["Admin"])
 # /