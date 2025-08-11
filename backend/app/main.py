from fastapi import FastAPI
from .routes import AdminRoute as admin_routes, getdata as getdata_routes
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Document Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change to your frontend domain(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(admin_routes.router)
app.include_router(getdata_routes.router)   