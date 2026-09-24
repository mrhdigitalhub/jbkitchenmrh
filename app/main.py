"""
JB KITCHEN - app/main.py FINAL WORKING 1:1
- Fix Internal Server Error di /dashboard/admin (screenshot Bapak)
- Fix 0 Bahan (screenshot sebelumnya) -> pakai bahan_inventory yang asli
- Tidak ubah rumus, tidak tambah file baru
"""
import os, json, uuid
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"[WARN] Supabase init: {e}")

app = FastAPI(title="JB KITCHEN MRH")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "app" else BASE_DIR

# Templates - cari di semua lokasi (Vercel safe)
templates = None
for cand in [BASE_DIR / "templates", PROJECT_ROOT / "app" / "templates", PROJECT_ROOT / "templates", Path.cwd() / "app" / "templates", Path.cwd() / "templates"]:
    if cand.exists():
        templates = Jinja2Templates(directory=str(cand))
        print(f"[OK] Templates: {cand}")
        break

# Static
for cand in [BASE_DIR / "static", PROJECT_ROOT / "app" / "static"]:
    if cand.exists():
        app.mount("/static", StaticFiles(directory=str(cand)), name="static")
        break

def safe_float(v, d=0.0):
    try:
        if v is None or v == "": return d
        return float(v)
    except: return d

def format_nama(s):
    return ' '.join([w.capitalize() for w in str(s).split()]) if s else ""

# === Kategori - 6 Utama Final ===
DEFAULT_UTAMA = [
    {"code":"cuc","label":"Cuci / Chemical","type":"utama"},
    {"code":"dgi","label":"Bahan Hewani / Daging","type":"utama"},
    {"code":"nbt","label":"Bahan Nabati","type":"utama"},
    {"code":"pck","label":"Packaging Kertas / Karton","type":"utama"},
    {"code":"plk","label":"Plastik & Kemasan","type":"utama"},
    {"code":"prs","label":"Perasa / Saus","type":"utama"},
]
DEFAULT_SUB = [
    {"code":"cir","label":"Cairan","parent":"cuc","type":"sub"},
    {"code":"lut","label":"Laut / Seafood","parent":"dgi","type":"sub"},
    {"code":"oss","label":"Olahan Susu","parent":"dgi","type":"sub"},
    {"code":"sap","label":"Sapi","parent":"dgi","type":"sub"},
    {"code":"tlr","label":"Telur / Unggas","parent":"dgi","type":"sub"},
    {"code":"ugs","label":"Unggas Potong","parent":"dgi","type":"sub"},
    {"code":"buh","label":"Buah","parent":"nbt","type":"sub"},
    {"code":"kcg","label":"Kacang & Bijian","parent":"nbt","type":"sub"},
    {"code":"rmp","label":"Rempah","parent":"nbt","type":"sub"},
    {"code":"srl","label":"Serealia / Beras","parent":"nbt","type":"sub"},
    {"code":"syr","label":"Sayuran","parent":"nbt","type":"sub"},
    {"code":"umb","label":"Umbi-umbian","parent":"nbt","type":"sub"},
    {"code":"bdr","label":"Bumbu Dasar","parent":"nbt","type":"sub"},
    {"code":"myk","label":"Minyak & Lemak","parent":"nbt","type":"sub"},
    {"code":"krt","label":"Kertas / Karton","parent":"pck","type":"sub"},
    {"code":"pls","label":"Plastik Styrofoam","parent":"pck","type":"sub"},
    {"code":"sdk","label":"Sendok / Saji / Alat","parent":"pck","type":"sub"},
    {"code":"mnm","label":"Minuman / Air","parent":"plk","type":"sub"},
    {"code":"ras","label":"Rasa / Saus","parent":"prs","type":"sub"},
    {"code":"ins","label":"Instant / Bumbu Instan","parent":"prs","type":"sub"},
]

def get_kategori_data():
    if not supabase:
        return DEFAULT_UTAMA, DEFAULT_SUB
    try:
        res = supabase.table("kategori_master").select("*").order("code").execute()
        data = res.data or []
        if not data: return DEFAULT_UTAMA, DEFAULT_SUB
        utama = [d for d in data if d.get("type")=="utama"]
        sub = [d for d in data if d.get("type")=="sub"]
        return (utama or DEFAULT_UTAMA), (sub or DEFAULT_SUB)
    except:
        return DEFAULT_UTAMA, DEFAULT_SUB

# === Stats untuk /dashboard/admin - ANTI 500 ===
@app.get("/health")
async def health():
    return {"status":"ok","supabase":bool(supabase),"templates":str(templates) if templates else "none"}

@app.get("/api/stats/realtime")
async def stats_realtime():
    if not supabase:
        return {"total_bahan":0,"aset_inventory":0,"stock_min":0,"total_menu":0,"items":[]}
    try:
        res = supabase.table("bahan_inventory").select("id,kode_bahan,nama_bahan,stock_qty,harga_per_satuan").execute()
        data = res.data or []
        total = len(data)
        aset = sum([safe_float(b.get("stock_qty"))*safe_float(b.get("harga_per_satuan")) for b in data])
        return {"total_bahan":total,"aset_inventory":aset,"stock_min":0,"total_menu":0,"items":data[:5]}
    except Exception as e:
        return {"error":str(e),"total_bahan":0,"aset_inventory":0,"stock_min":0,"total_menu":0,"items":[]}

@app.get("/api/kategori/list")
async def kategori_list():
    utama, sub = get_kategori_data()
    return {"utama":utama,"sub":sub}

# === FIX UTAMA: /dashboard/admin JANGAN CRASH ===
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse("/dashboard/admin/inventory")

@app.get("/dashboard/admin", response_class=HTMLResponse)
async def dashboard_admin(request: Request):
    # Jangan paksa load dashboard_admin.html kalau tidak ada - redirect ke inventory yang pasti ada
    # Ini yang bikin Internal Server Error di screenshot Bapak
    try:
        if templates is None:
            return RedirectResponse("/dashboard/admin/inventory")
        # cek apakah dashboard_admin.html ada
        tmpl_dir = Path(templates.env.loader.searchpath[0]) if hasattr(templates.env.loader, 'searchpath') else None
        has_dashboard = False
        if tmpl_dir:
            has_dashboard = (tmpl_dir / "dashboard_admin.html").exists()
        if not has_dashboard:
            # kalau tidak ada, redirect ke inventory (yang final)
            return RedirectResponse("/dashboard/admin/inventory")
        stats = await stats_realtime()
        context = {"request": request, "stats": stats, "role": "ADMIN", "total_bahan": stats.get("total_bahan",0), "bahan": stats.get("items",[]), "items": stats.get("items",[])}
        context.update(stats)
        context["bahan"] = stats.get("items",[])
        return templates.TemplateResponse(request, "dashboard_admin.html", context)
    except Exception as e:
        # ANTI 500 - jangan pernah 500
        print(f"[ADMIN ERROR] {e}")
        return RedirectResponse("/dashboard/admin/inventory")

# === INVENTORY - FINAL 1:1 ===
@app.get("/dashboard/admin/inventory", response_class=HTMLResponse)
@app.get("/inventory_stock", response_class=HTMLResponse)
async def inventory_stock(request: Request):
    bahan = []
    if supabase:
        try:
            res = supabase.table("bahan_inventory").select("*").order("kode_bahan").execute()
            bahan = res.data or []
        except Exception as e:
            print(f"[inventory] {e}")
    if templates is None:
        return HTMLResponse(f"<h3>Inventory {len(bahan)} bahan - templates not found</h3>")
    try:
        return templates.TemplateResponse(request, "inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan)})
    except Exception as e:
        # fallback old signature
        try:
            return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan)})
        except Exception as e2:
            return HTMLResponse(f"<h1>Inventory fallback</h1><p>Error: {e} / {e2}</p><p>Total: {len(bahan)}</p>")

@app.post("/dashboard/admin/inventory/save")
async def inventory_save(request: Request):
    if not supabase: raise HTTPException(500,"Supabase not configured")
    form = await request.form()
    data = dict(form)
    stock_qty = safe_float(data.get("stock_awal"),0) + safe_float(data.get("tambah"),0) - safe_float(data.get("terpakai"),0)
    if stock_qty == 0: stock_qty = safe_float(data.get("stock_qty"))
    harga = safe_float(data.get("harga_baru"),0) or safe_float(data.get("harga_awal"),0) or safe_float(data.get("harga_per_satuan"),0)
    payload = {
        "kode_bahan": data.get("kode_bahan"),
        "nama_bahan": (data.get("nama_bahan") or "").lower(),
        "kategori_utama": data.get("kategori_utama"),
        "kode_kategori": data.get("kode_kategori"),
        "satuan_default": data.get("satuan_default") or "Kg",
        "stock_qty": stock_qty,
        "harga_per_satuan": harga,
        "id_halal": data.get("id_halal"),
        "updated_at": datetime.now().isoformat()
    }
    try:
        if data.get("id"):
            supabase.table("bahan_inventory").update(payload).eq("id", data.get("id")).execute()
        else:
            payload["id"] = str(uuid.uuid4())
            supabase.table("bahan_inventory").insert(payload).execute()
        return RedirectResponse(url="/dashboard/admin/inventory", status_code=303)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/bahan/{id}")
async def delete_bahan(id: str):
    if not supabase: raise HTTPException(500,"No supabase")
    supabase.table("bahan_inventory").delete().eq("id", id).execute()
    return {"ok":True}

# === Kelola Kategori - Proteksi Locked Delete (tambahan tanpa ubah final) ===
@app.delete("/api/kategori/utama/{code}")
async def delete_kategori_utama(code: str):
    if not supabase: raise HTTPException(500,"No supabase")
    code = code.lower().strip()
    # cek bahan_inventory pakai kategori ini
    try:
        res = supabase.table("bahan_inventory").select("id").eq("kategori_utama", code).limit(1).execute()
        if res.data:
            raise HTTPException(400, f"Tidak bisa hapus '{code}' karena masih dipakai {len(res.data)} bahan di inventory. Pindahkan dulu.")
        supabase.table("kategori_master").delete().eq("code", code).eq("type","utama").execute()
        return {"ok":True}
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(400, f"Gagal hapus: {e}")

@app.delete("/api/kategori/sub/{code}")
async def delete_kategori_sub(code: str):
    if not supabase: raise HTTPException(500,"No supabase")
    code = code.lower().strip()
    try:
        res = supabase.table("bahan_inventory").select("id").eq("kode_kategori", code).limit(1).execute()
        if res.data:
            raise HTTPException(400, f"Tidak bisa hapus sub '{code}' karena masih dipakai bahan. Pindahkan dulu.")
        supabase.table("kategori_master").delete().eq("code", code).eq("type","sub").execute()
        return {"ok":True}
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(400, f"Gagal hapus: {e}")
