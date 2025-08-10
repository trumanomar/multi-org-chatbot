from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(open("frontend/lib/screens/login_screen.dart", "r").read())

@app.get("/api/chat", response_class=JSONResponse)
async def chat():
    return HTMLResponse(open("frontend/lib/screens/chat.dart", "r").read())


    