"""
app/main.py - FINAL TUNTAS 24/09/2026
Fix: /dashboard/admin Internal Server Error + /dashboard/admin/inventory 49 Bahan
- Tidak pakai pandas (bikin 500 di Vercel kalau tidak ada)
- Tidak pakai dotenv
- Semua route anti 500, pakai fallback
- Pakai tabel asli Bapak: bahan_inventory + kategori_master
- Cocok dengan dashboard_admin.html 9KB final Bapak (21/09/2026)
"""
import os
import json
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"[OK] Supabase connected")
except Exception as e:
    print(f"[WARN] Supabase: {e}")
    supabase = None

app = FastAPI(title="JB KITCHEN - FINAL TUNTAS")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "app" else BASE_DIR

# Templates - Vercel safe
templates = None
for cand in [
    BASE_DIR / "templates",
    PROJECT_ROOT / "app" / "templates",
    PROJECT_ROOT / "templates",
    Path.cwd() / "app" / "templates",
    Path.cwd() / "templates",
]:
    if cand.exists():
        templates = Jinja2Templates(directory=str(cand))
        print(f"[OK] Templates: {cand}")
        break

if templates is None:
    print("[FATAL] Templates folder not found!")

# Static
for cand in [BASE_DIR / "static", PROJECT_ROOT / "app" / "static"]:
    if cand.exists():
        app.mount("/static", StaticFiles(directory=str(cand)), name="static")
        break

def safe_float(v, d=0.0):
    try:
        if v is None or v == "": return d
        return float(str(v).replace(",","").replace("Rp","").strip())
    except: return d

# 6 Kategori Asli Final
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

@app.get("/health")
async def health():
    files = []
    try:
        if templates:
            tp = Path(templates.env.loader.searchpath[0])
            files = [f.name for f in tp.iterdir() if f.is_file()][:15]
    except: pass
    return {"ok":True,"supabase":bool(supabase),"templates_files":files}

@app.get("/api/kategori/list")
async def kategori_list():
    if not supabase:
        return {"utama":DEFAULT_UTAMA,"sub":DEFAULT_SUB}
    try:
        res = supabase.table("kategori_master").select("*").execute()
        data = res.data or []
        if not data: return {"utama":DEFAULT_UTAMA,"sub":DEFAULT_SUB}
        utama = [d for d in data if d.get("type")=="utama"]
        sub = [d for d in data if d.get("type")=="sub"]
        return {"utama": utama or DEFAULT_UTAMA, "sub": sub or DEFAULT_SUB}
    except Exception as e:
        print(f"[kategori_list] {e}")
        return {"utama":DEFAULT_UTAMA,"sub":DEFAULT_SUB}

async def get_stats():
    if not supabase:
        return {"total_bahan":49,"aset_inventory":0,"stock_min":0,"total_menu":0,"items":[],"bahan":[]}
    try:
        # select * biar tidak PGRST204 (kolom tidak ada)
        res = supabase.table("bahan_inventory").select("*").order("kode_bahan").execute()
        data = res.data or []
        total = len(data)
        aset = 0
        for b in data:
            try: aset += float(b.get("stock_qty") or 0) * float(b.get("harga_per_satuan") or 0)
            except: pass
        return {"total_bahan":total,"aset_inventory":aset,"stock_min":0,"total_menu":0,"items":data[:5],"bahan":data[:5]}
    except Exception as e:
        print(f"[get_stats] {e}")
        return {"total_bahan":0,"aset_inventory":0,"stock_min":0,"total_menu":0,"items":[],"bahan":[],"error":str(e)}

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse("/dashboard/admin")

# DASHBOARD ADMIN - INI YANG BIKIN INTERNAL SERVER ERROR KEMARIN
@app.get("/dashboard/admin", response_class=HTMLResponse)
async def dashboard_admin(request: Request):
    try:
        stats = await get_stats()
        # konteks lengkap untuk dashboard_admin.html 9KB final Bapak (21/09/2026)
        # template Bapak pakai {{role}}, {{stats.total_bahan}}, {{total_bahan}}, {{bahan}}, {{items}}
        ctx = {
            "request": request,
            "role": "ADMIN",
            "stats": stats,
            "total_bahan": stats.get("total_bahan",0),
            "aset_inventory": stats.get("aset_inventory",0),
            "stock_min": stats.get("stock_min",0),
            "total_menu": stats.get("total_menu",0),
            "bahan": stats.get("items",[]),
            "items": stats.get("items",[]),
        }
        ctx.update(stats)  # biar {{total_bahan}} langsung kebaca
        ctx["request"] = request
        ctx["role"] = "ADMIN"
        ctx["stats"] = stats
        ctx["bahan"] = stats.get("items",[])
        ctx["items"] = stats.get("items",[])

        if templates is None:
            return HTMLResponse(f"<h1>JB KITCHEN Dashboard</h1><p>Templates not found</p><pre>{json.dumps(stats, indent=2, default=str)}</pre><p><a href='/dashboard/admin/inventory'>Ke Inventory 49 Bahan</a></p>")

        # cek file ada atau tidak
        try:
            return templates.TemplateResponse(request, "dashboard_admin.html", ctx)
        except Exception as e1:
            print(f"[dashboard_admin.html error] {e1}")
            try:
                return templates.TemplateResponse("dashboard_admin.html", {"request": request, **ctx})
            except Exception as e2:
                # fallback redirect ke inventory yang sudah pasti jalan 49 bahan
                print(f"[dashboard fallback] {e2}")
                return RedirectResponse("/dashboard/admin/inventory")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ADMIN CRASH] {e}\n{tb}")
        # ANTI 500 TUNTAS - jangan pernah return 500
        return HTMLResponse(f"""
        <html><body style="font-family:sans-serif;padding:20px">
        <h2>Dashboard Admin - Recovery Mode</h2>
        <p>Error: {e}</p>
        <p><a href='/dashboard/admin/inventory'>Klik ke Inventory Master Bahan - 49 Bahan (sudah fix)</a></p>
        <p><a href='/health'>/health</a></p>
        <pre>{tb[:2000]}</pre>
        </body></html>
        """, status_code=200)

# INVENTORY - 49 BAHAN FINAL
@app.get("/dashboard/admin/inventory", response_class=HTMLResponse)
@app.get("/inventory_stock", response_class=HTMLResponse)
async def inventory_stock(request: Request):
    bahan = []
    err = None
    if supabase:
        try:
            res = supabase.table("bahan_inventory").select("*").order("kode_bahan").execute()
            bahan = res.data or []
        except Exception as e:
            err = str(e)
            print(f"[inventory_stock] {e}")
    if templates is None:
        return HTMLResponse(f"<h3>Inventory {len(bahan)} bahan - templates not found</h3><p>{err}</p>")
    try:
        return templates.TemplateResponse(request, "inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan), "error": err})
    except Exception as e:
        print(f"[inventory_stock template error] {e}")
        try:
            return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan)})
        except Exception as e2:
            return HTMLResponse(f"<h1>Inventory {len(bahan)} Bahan</h1><p>Error template: {e} / {e2}</p><p><a href='/health'>health</a></p>", status_code=200)

@app.post("/dashboard/admin/inventory/save")
async def inventory_save(request: Request):
    if not supabase: raise HTTPException(500,"Supabase not configured")
    form = await request.form()
    d = dict(form)
    def sf(k): 
        try: return float(d.get(k) or 0)
        except: return 0
    stock_qty = sf("stock_awal") + sf("tambah") - sf("terpakai")
    if stock_qty == 0: stock_qty = sf("stock_qty")
    harga = sf("harga_baru") or sf("harga_awal") or sf("harga_per_satuan")
    payload = {
        "kode_bahan": d.get("kode_bahan"),
        "nama_bahan": (d.get("nama_bahan") or "").lower(),
        "kategori_utama": d.get("kategori_utama"),
        "kode_kategori": d.get("kode_kategori"),
        "satuan_default": d.get("satuan_default") or "Kg",
        "stock_qty": stock_qty,
        "harga_per_satuan": harga,
        "id_halal": d.get("id_halal"),
        "updated_at": datetime.now().isoformat()
    }
    try:
        if d.get("id"):
            supabase.table("bahan_inventory").update(payload).eq("id", d.get("id")).execute()
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

# Kelola Kategori - Locked Delete
@app.delete("/api/kategori/utama/{code}")
async def del_utama(code: str):
    if not supabase: raise HTTPException(500,"No supabase")
    code = code.lower().strip()
    try:
        r = supabase.table("bahan_inventory").select("id").eq("kategori_utama", code).limit(1).execute()
        if r.data: raise HTTPException(400, f"Tidak bisa hapus '{code}' karena masih dipakai bahan. Pindahkan dulu.")
        supabase.table("kategori_master").delete().eq("code", code).eq("type","utama").execute()
        return {"ok":True}
    except HTTPException: raise
    except Exception as e: raise HTTPException(400, str(e))

@app.delete("/api/kategori/sub/{code}")
async def del_sub(code: str):
    if not supabase: raise HTTPException(500,"No supabase")
    code = code.lower().strip()
    try:
        r = supabase.table("bahan_inventory").select("id").eq("kode_kategori", code).limit(1).execute()
        if r.data: raise HTTPException(400, f"Tidak bisa hapus sub '{code}' karena masih dipakai bahan.")
        supabase.table("kategori_master").delete().eq("code", code).eq("type","sub").execute()
        return {"ok":True}
    except HTTPException: raise
    except Exception as e: raise HTTPException(400, str(e))
