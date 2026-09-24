import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="JB KITCHEN")

# Templates path - anti crash
templates_path = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_path):
    templates_path = "app/templates"
if not os.path.exists(templates_path):
    templates_path = os.path.join(os.getcwd(), "app/templates")
if not os.path.exists(templates_path):
    templates_path = "templates"
print(f"[TEMPLATES] using {templates_path}")

try:
    templates = Jinja2Templates(directory=templates_path)
except Exception as e:
    print(f"Template init error: {e}")
    templates = None

# Import kategori router - ANTI CIRCULAR & ANTI CRASH
kategori_router = None
try:
    from .api_kategori import router as kategori_router
except Exception as e1:
    try:
        from app.api_kategori import router as kategori_router
    except Exception as e2:
        try:
            from api_kategori import router as kategori_router
        except Exception as e3:
            print(f"[WARN] kategori_router gagal load: {e1} | {e2} | {e3}")

if kategori_router is not None:
    app.include_router(kategori_router, prefix="/api/kategori", tags=["kategori"])

def get_supabase():
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception as e:
        print(f"[Supabase] error: {e}")
        return None

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    # anti 500
    if templates is None:
        return HTMLResponse("<h1>JB KITCHEN - Templates not found</h1>", status_code=200)
    try:
        sb = get_supabase()
        bahan = []
        if sb:
            try:
                res = sb.table("bahan").select("*").order("kode_bahan").limit(100).execute()
                bahan = res.data or []
            except Exception as e:
                print(f"bahan fetch error: {e}")
                bahan = []
        return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan)})
    except Exception as e:
        print(f"ROOT error: {e}")
        return HTMLResponse(f"<pre>Error: {e}</pre><a href='/health'>health</a>", status_code=200)

@app.get("/dashboard/admin/inventory", response_class=HTMLResponse)
def inventory_page(request: Request):
    # INI YANG BIKIN INTERNAL SERVER ERROR KEMARIN - sekarang anti crash
    if templates is None:
        return HTMLResponse("<h1>JB KITCHEN - Templates folder missing</h1><p>Check app/templates/inventory_stock.html</p>", status_code=200)
    bahan = []
    error_msg = None
    sb = get_supabase()
    if sb is None:
        error_msg = "SUPABASE_URL / KEY belum set di Vercel"
    else:
        try:
            res = sb.table("bahan").select("*").order("kode_bahan").execute()
            bahan = res.data or []
        except Exception as e:
            error_msg = str(e)
            print(f"[inventory] supabase error: {e}")
            bahan = []
    try:
        return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan), "error": error_msg})
    except Exception as e:
        # JANGAN 500, kembalikan HTML langsung
        print(f"[TemplateResponse error] {e}")
        html = f"<html><body><h1>Inventory - fallback</h1><p>Error template: {e}</p><p>Bahan count: {len(bahan)}</p><pre>{error_msg}</pre><a href='/health'>/health</a></body></html>"
        return HTMLResponse(html, status_code=200)

@app.get("/api/bahan/list")
def list_bahan():
    sb = get_supabase()
    if sb is None:
        return JSONResponse({"bahan": [], "error": "supabase not configured"}, status_code=200)
    try:
        data = sb.table("bahan").select("*").order("kode_bahan").execute().data or []
        return {"bahan": data}
    except Exception as e:
        return {"bahan": [], "error": str(e)}

@app.post("/api/bahan/save")
def save_bahan(payload: dict):
    sb = get_supabase()
    if sb is None:
        return JSONResponse({"error": "supabase not configured"}, status_code=200)
    try:
        kode = (payload.get("kode_bahan") or "").lower().strip()
        nama = (payload.get("nama_bahan") or "").lower().strip()
        if not nama:
            return JSONResponse({"error": "nama_bahan wajib"}, status_code=400)
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
        if payload.get("id"):
            sb.table("bahan").update(data).eq("id", payload.get("id")).execute()
        else:
            sb.table("bahan").upsert(data, on_conflict="kode_bahan").execute()
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.delete("/api/bahan/{id}")
def delete_bahan(id: str):
    sb = get_supabase()
    if sb is None:
        return JSONResponse({"error": "supabase not configured"}, status_code=400)
    try:
        sb.table("bahan").delete().eq("id", id).execute()
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/health")
def health():
    files = []
    try:
        if os.path.exists(templates_path):
            files = os.listdir(templates_path)[:10]
    except:
        pass
    return {"ok": True, "templates_path": templates_path, "files": files, "has_supabase": get_supabase() is not None}
