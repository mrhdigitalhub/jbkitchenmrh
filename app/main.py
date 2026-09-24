import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from supabase import create_client, Client

# ===== App init =====
app = FastAPI(title="JB KITCHEN - Inventory")

# ===== Supabase helper =====
def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="SUPABASE_URL / SUPABASE_KEY belum set di Vercel Env")
    return create_client(url, key)

# ===== Templates =====
# Vercel path bisa di app/templates atau templates
templates_path = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_path):
    templates_path = "app/templates"
if not os.path.exists(templates_path):
    templates_path = "templates"
templates = Jinja2Templates(directory=templates_path)

# ===== Import kategori router (FIX DELETE) =====
try:
    from .api_kategori import router as kategori_router
except ImportError:
    try:
        from app.api_kategori import router as kategori_router
    except ImportError:
        from api_kategori import router as kategori_router

app.include_router(kategori_router, prefix="/api/kategori", tags=["kategori"])

# ===== Routes Inventory =====
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": [], "total": 0})

@app.get("/dashboard/admin/inventory", response_class=HTMLResponse)
def inventory_page(request: Request):
    try:
        sb = get_supabase()
        res = sb.table("bahan").select("*").order("kode_bahan").execute()
        bahan = res.data or []
        return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan)})
    except Exception as e:
        # fallback biar tidak Not Found
        return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": [], "total": 0, "error": str(e)})

@app.get("/api/bahan/list")
def list_bahan():
    sb = get_supabase()
    data = sb.table("bahan").select("*").order("kode_bahan").execute().data or []
    return {"bahan": data}

@app.post("/api/bahan/save")
def save_bahan(payload: dict):
    sb = get_supabase()
    try:
        # payload dari modal
        kode = (payload.get("kode_bahan") or "").lower().strip()
        nama = (payload.get("nama_bahan") or "").lower().strip()
        if not nama:
            raise HTTPException(400, "nama_bahan wajib")
        data = {
            "kode_bahan": kode,
            "nama_bahan": nama,
            "kategori_utama": (payload.get("kategori_utama") or "").lower(),
            "kode_kategori": (payload.get("kode_kategori") or "").lower(),
            "satuan_default": payload.get("satuan_default") or "Kg",
            "stock_qty": float(payload.get("stock_qty") or 0),
            "harga_per_satuan": float(payload.get("harga_per_satuan") or 0),
            "id_halal": payload.get("id_halal"),
            "hall_flag": payload.get("hall_flag"),
        }
        # upsert by id if exists
        if payload.get("id"):
            sb.table("bahan").update(data).eq("id", payload.get("id")).execute()
        else:
            # cek duplikat kode
            sb.table("bahan").upsert(data, on_conflict="kode_bahan").execute()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))

@app.delete("/api/bahan/{id}")
def delete_bahan(id: str):
    sb = get_supabase()
    try:
        sb.table("bahan").delete().eq("id", id).execute()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/health")
def health():
    return {"ok": True, "templates_path": templates_path}
