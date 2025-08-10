from fastapi import FastAPI
from app.Routes import AdminRoute as admin_routes, getdata as getdata_routes

app = FastAPI(title="Document Chatbot API")

app.include_router(admin_routes.router)
app.include_router(getdata_routes.router)
