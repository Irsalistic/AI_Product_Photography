from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# create API client
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Import routers from each endpoint module

from photography import router as inpaint_router

# Include routers in the application

app.include_router(inpaint_router)


# Optionally, you can define a home or root endpoint
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):  # Include 'request: Request' as a parameter
    return templates.TemplateResponse("index.html", {"request": request})  # Pass the request in the context
