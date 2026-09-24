from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

# import router kategori - ultra safe
try:
    from .api_kategori import router as kategori_router
except ImportError:
    try:
        from app.api_kategori import router as kategori_router
    except ImportError:
        from api_kategori import router as kategori_router

app = FastAPI(title="JB KITCHEN")

# include kategori router - SEMUA METHOD GET POST DELETE
app.include_router(kategori_router, prefix="/api/kategori", tags=["kategori"])

# mount templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_dir):
    templates_dir = "app/templates"
templates = Jinja2Templates(directory=templates_dir)

# other routers - bahan, menu dll (existing)
try:
    from .routes import bahan_router
    app.include_router(bahan_router)
except Exception as e:
    print(f"bahan_router not loaded: {e}")

@app.get("/")
def root():
    return {"status": "JB KITCHEN API Live", "kategori": "/api/kategori/list"}

@app.get("/health")
def health():
    return {"ok": True}
