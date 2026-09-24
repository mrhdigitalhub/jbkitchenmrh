import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates_path = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_path):
    templates_path = "app/templates"
if not os.path.exists(templates_path):
    templates_path = os.path.join(os.getcwd(), "app/templates")
templates = Jinja2Templates(directory=templates_path)

# kategori router - tetap
try:
    from .api_kategori import router as kategori_router
except:
    try:
        from app.api_kategori import router as kategori_router
    except:
        from api_kategori import router as kategori_router

try:
    app.include_router(kategori_router, prefix="/api/kategori", tags=["kategori"])
except Exception as e:
    print(f"kategori router not included: {e}")

def get_supabase():
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception as e:
        print(f"supabase init error: {e}")
        return None

def fetch_bahan_safe():
    sb = get_supabase()
    if sb is None:
        return [], "SUPABASE_URL/KEY belum set"
    # Coba beberapa nama tabel yang mungkin - FIX PGRST205
    table_candidates = ["bahan", "kategori_bahan", "master_bahan", "bahan_baku", "inventory_bahan"]
    last_err = None
    for tbl in table_candidates:
        try:
            res = sb.table(tbl).select("*").order("kode_bahan").limit(200).execute()
            data = res.data or []
            print(f"[OK] table {tbl} -> {len(data)} rows")
            return data, f"table:{tbl}"
        except Exception as e:
            last_err = str(e)
            # jika PGRST205 lanjut coba tabel lain
            if "PGRST205" in str(e) or "Could not find the table" in str(e) or "schema cache" in str(e):
                print(f"[TRY] {tbl} not found, coba next")
                continue
            else:
                print(f"[ERR] {tbl}: {e}")
                continue
    return [], last_err or "semua tabel bahan tidak ditemukan"

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    bahan, info = fetch_bahan_safe()
    try:
        # FIX: signature baru Jinja2Templates -> request sebagai arg pertama
        return templates.TemplateResponse(request, "inventory_stock.html", {"bahan": bahan, "total": len(bahan), "info": info})
    except Exception as e:
        # fallback signature lama
        try:
            return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan), "info": info})
        except Exception as e2:
            return HTMLResponse(f"<h1>Fallback root</h1><p>{e}</p><p>{e2}</p><p>info:{info}</p><p>bahan:{len(bahan)}</p>", status_code=200)

@app.get("/dashboard/admin/inventory", response_class=HTMLResponse)
def inventory_page(request: Request):
    bahan, info = fetch_bahan_safe()
    err_str = str(info) if info else ""
    try:
        # FIX tuple dict key -> pakai signature request pertama
        return templates.TemplateResponse(request, "inventory_stock.html", {"bahan": bahan, "total": len(bahan), "info": err_str})
    except Exception as e1:
        print(f"TemplateResponse new sig error: {e1}")
        try:
            # coba old sig
            return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan), "info": err_str})
        except Exception as e2:
            print(f"TemplateResponse old sig error: {e2}")
            # anti 500 - kembalikan HTML langsung dengan info lengkap dari screenshot Bapak
            html = f"""
            <html><head><title>Inventory - fallback</title></head><body>
            <h1>Inventory - fallback (anti 500)</h1>
            <p><b>Error template:</b> {e1} | {e2}</p>
            <p><b>Bahan count:</b> {len(bahan)}</p>
            <p><b>Info DB:</b> {err_str}</p>
            <p>Bahan sample: {str(bahan[:1])[:500]}</p>
            <hr><a href='/health'>/health</a> | <a href='/api/bahan/list'>/api/bahan/list</a>
            </body></html>
            """
            return HTMLResponse(html, status_code=200)

@app.get("/api/bahan/list")
def list_bahan():
    bahan, info = fetch_bahan_safe()
    return {"bahan": bahan, "info": info, "total": len(bahan)}

@app.post("/api/bahan/save")
def save_bahan(payload: dict):
    sb = get_supabase()
    if not sb:
        return JSONResponse({"error": "supabase not configured"}, status_code=400)
    # coba tulis ke tabel yang ada
    for tbl in ["bahan", "kategori_bahan", "master_bahan"]:
        try:
            data = {
                "kode_bahan": (payload.get("kode_bahan") or "").lower().strip(),
                "nama_bahan": (payload.get("nama_bahan") or "").lower().strip(),
                "kategori_utama": (payload.get("kategori_utama") or "").lower(),
                "kode_kategori": (payload.get("kode_kategori") or "").lower(),
                "satuan_default": payload.get("satuan_default") or "Kg",
                "stock_qty": float(payload.get("stock_qty") or 0),
                "harga_per_satuan": float(payload.get("harga_per_satuan") or 0),
            }
            if payload.get("id"):
                sb.table(tbl).update(data).eq("id", payload.get("id")).execute()
            else:
                sb.table(tbl).upsert(data, on_conflict="kode_bahan").execute()
            return {"ok": True, "table": tbl}
        except Exception as e:
            if "PGRST205" in str(e):
                continue
            return JSONResponse({"error": str(e), "table": tbl}, status_code=400)
    return JSONResponse({"error": "tidak ada tabel bahan yang bisa ditulis"}, status_code=400)

@app.delete("/api/bahan/{id}")
def delete_bahan(id: str):
    sb = get_supabase()
    if not sb:
        return JSONResponse({"error": "supabase not configured"}, status_code=400)
    for tbl in ["bahan", "kategori_bahan"]:
        try:
            sb.table(tbl).delete().eq("id", id).execute()
            return {"ok": True, "table": tbl}
        except Exception as e:
            if "PGRST205" in str(e):
                continue
            return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse({"error": "table not found"}, status_code=400)

@app.get("/health")
def health():
    bahan, info = fetch_bahan_safe()
    try:
        files = os.listdir(templates_path)[:20]
    except:
        files = []
    return {"ok": True, "templates_path": templates_path, "files": files, "bahan_total": len(bahan), "db_info": str(info)}
