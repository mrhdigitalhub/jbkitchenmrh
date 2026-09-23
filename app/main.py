"""
JB KITCHEN MRH - FINAL LENGKAP ANTI NOT FOUND
Fix: Semua route dashboard lengkap + TemplateResponse FastAPI 0.115+ + Opsi C distinct pck vs plk
"""
import os, re, uuid, io, json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"[OK] Supabase: {SUPABASE_URL[:30]}...")
    else:
        print("[WARN] SUPABASE_URL/KEY belum di-set")
except Exception as e:
    print(f"[WARN] Supabase init fail: {e}")

app = FastAPI(title="JB KITCHEN MRH - FINAL LENGKAP")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "app" else BASE_DIR

# Template & Static finder - anti Vercel crash
templates = None
for cand in [
    BASE_DIR / "templates",
    BASE_DIR / "app" / "templates",
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
    print("[FATAL] Templates tidak ketemu")

for static_cand in [
    BASE_DIR / "static",
    BASE_DIR / "app" / "static",
    PROJECT_ROOT / "app" / "static",
    PROJECT_ROOT / "static",
    Path.cwd() / "app" / "static",
    Path.cwd() / "static",
]:
    if static_cand.exists():
        app.mount("/static", StaticFiles(directory=str(static_cand)), name="static")
        print(f"[OK] Static: {static_cand}")
        break

# ================== KONSTANTA OPSI C DISTINCT ==================
DEFAULT_KAT_UTAMA = [
    {"code":"cuc","label":"Cuci / Chemical","type":"utama"},
    {"code":"dgi","label":"Bahan Hewani / Daging","type":"utama"},
    {"code":"nbt","label":"Bahan Nabati","type":"utama"},
    {"code":"pck","label":"📦 Kemasan Kertas & Styrofoam (pck)","type":"utama"},
    {"code":"plk","label":"🥤 Pelengkap Minum & Plastik (plk)","type":"utama"},
    {"code":"prs","label":"Perasa / Saus","type":"utama"},
]
DEFAULT_SUB_KATEGORI = [
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
    {"code":"krt","label":"Kertas / Karton (pck-krt)","parent":"pck","type":"sub"},
    {"code":"pls","label":"Plastik Styrofoam (pck-pls)","parent":"pck","type":"sub"},
    {"code":"sdk","label":"Sendok / Saji / Alat (pck-sdk)","parent":"pck","type":"sub"},
    {"code":"mnm","label":"Minuman / Air (plk-mnm)","parent":"plk","type":"sub"},
    {"code":"cup","label":"Cup & Tutup (plk-cup)","parent":"plk","type":"sub"},
    {"code":"sed","label":"Sedotan & Plastik (plk-sed)","parent":"plk","type":"sub"},
    {"code":"ras","label":"Rasa / Saus","parent":"prs","type":"sub"},
    {"code":"ins","label":"Instant / Bumbu Instan","parent":"prs","type":"sub"},
]

OH_PERCENT = 0.10
DELIVERY_PERCENT = 0.05
MANPOWER_RATES = {"kepala_produksi":2000,"juru_masak":1500,"pegawai":1000}
KAMUS_DEFAULT_LOCAL = {
    "bawang merah": {"qty":0.15,"satuan":"Kg","satuan_default":"Kg","konversi_json":{},"label":"Bawang Merah 0.15 Kg"},
    "telur": {"qty":1,"satuan":"Pcs","satuan_default":"Pcs","konversi_json":{"kg":0.06},"label":"Telur 1 Pcs"},
}

def safe_float(v, default=0.0) -> float:
    try:
        if v is None or v == "": return default
        return float(v)
    except: return default

def format_nama(s: str) -> str:
    return ' '.join([w.capitalize() for w in str(s).split()]) if s else ""

def parse_konversi_json(kj) -> dict:
    if isinstance(kj, dict): return kj
    if isinstance(kj, str):
        try: return json.loads(kj)
        except: return {}
    return {}

def get_kategori_data():
    if not supabase:
        return DEFAULT_KAT_UTAMA, DEFAULT_SUB_KATEGORI
    try:
        res = supabase.table("kategori_master").select("*").order("code").execute()
        data = res.data or []
        if not data:
            return DEFAULT_KAT_UTAMA, DEFAULT_SUB_KATEGORI
        utama = [d for d in data if d.get("type")=="utama" and d.get("is_active",True)]
        sub = [d for d in data if d.get("type")=="sub" and d.get("is_active",True)]
        return (utama or DEFAULT_KAT_UTAMA), (sub or DEFAULT_SUB_KATEGORI)
    except:
        return DEFAULT_KAT_UTAMA, DEFAULT_SUB_KATEGORI

def get_pengaturan_biaya():
    oh, delivery, manpower = OH_PERCENT, DELIVERY_PERCENT, MANPOWER_RATES.copy()
    if not supabase:
        return oh, delivery, manpower
    try:
        res = supabase.table("pengaturan_biaya").select("*").limit(1).execute()
        if res.data:
            row=res.data[0]
            oh=safe_float(row.get("oh_percent",10),10)/100
            delivery=safe_float(row.get("delivery_percent",5),5)/100
            manpower["kepala_produksi"]=safe_float(row.get("rate_kepala",2000),2000)
            manpower["juru_masak"]=safe_float(row.get("rate_koki",1500),1500)
            manpower["pegawai"]=safe_float(row.get("rate_pegawai",1000),1000)
    except: pass
    return oh, delivery, manpower

def hitung_hpp_final(hpp_bahan_total, porsi=1):
    oh, delivery, manpower = get_pengaturan_biaya()
    total_mp = sum(manpower.values())
    porsi = max(porsi,1)
    hpp_per_porsi = hpp_bahan_total / porsi
    hpp_final_per_porsi = hpp_per_porsi + hpp_per_porsi*oh + hpp_per_porsi*delivery + total_mp
    return {"hpp_per_porsi":hpp_per_porsi,"hpp_final_per_porsi":hpp_final_per_porsi,"oh":oh,"delivery":delivery,"manpower":manpower}

async def stats_realtime():
    total_bahan=0; aset=0; stock_min=0; items=[]
    if supabase:
        try:
            res = supabase.table("bahan_inventory").select("*").execute()
            items = res.data or []
            total_bahan = len(items)
            for it in items:
                aset += safe_float(it.get("harga_per_satuan",0))*safe_float(it.get("stock_qty",0))
                if safe_float(it.get("stock_qty",0)) <= safe_float(it.get("stock_minimum",5),5):
                    stock_min+=1
        except Exception as e:
            print(f"stats error: {e}")
    return {"total_bahan":total_bahan,"aset_inventory":aset,"stock_min":stock_min,"items":items,"total_menu":3}

# ================== API BAHAN ==================
@app.get("/api/bahan/list")
async def bahan_list():
    if not supabase:
        return {"items":[],"total":0}
    res = supabase.table("bahan_inventory").select("*").order("nama_bahan").execute()
    return {"items":res.data or [],"total":len(res.data or [])}

@app.get("/api/bahan/search")
async def bahan_search(q: str = ""):
    if not supabase:
        return {"items":[]}
    res = supabase.table("bahan_inventory").select("*").ilike("nama_bahan", f"%{q}%").execute()
    return {"items":res.data or []}

@app.post("/api/bahan/save")
async def bahan_save(request: Request):
    if not supabase: raise HTTPException(500,"No supabase")
    body = await request.json()
    payload = {
        "id": body.get("id") or str(uuid.uuid4()),
        "kode_bahan": body.get("kode_bahan") or body.get("kode") or f"AUTO-{uuid.uuid4().hex[:6]}",
        "nama_bahan": (body.get("nama_bahan") or body.get("nama") or "").lower().strip(),
        "kategori_utama": body.get("kategori_utama") or body.get("kat_utama") or "",
        "kode_kategori": body.get("kode_kategori") or body.get("kat_sub") or "",
        "satuan_default": body.get("satuan_default") or body.get("satuan") or "Kg",
        "stock_qty": safe_float(body.get("stock_qty") or body.get("stock"),0),
        "stock_minimum": safe_float(body.get("stock_minimum") or body.get("stock_min"),5),
        "harga_per_satuan": safe_float(body.get("harga_per_satuan") or body.get("harga"),0),
        "konversi_json": body.get("konversi_json") or {},
        "updated_at": datetime.now().isoformat()
    }
    ex = supabase.table("bahan_inventory").select("id").eq("id", payload["id"]).execute()
    if ex.data:
        supabase.table("bahan_inventory").update(payload).eq("id", payload["id"]).execute()
    else:
        payload["created_at"]=datetime.now().isoformat()
        supabase.table("bahan_inventory").insert(payload).execute()
    return {"ok":True,"id":payload["id"]}

@app.delete("/api/bahan/delete/{id_bahan}")
async def bahan_delete(id_bahan: str):
    if not supabase: raise HTTPException(500,"No supabase")
    supabase.table("bahan_inventory").delete().eq("id", id_bahan).execute()
    return {"ok":True}

@app.post("/api/bahan/quick-update")
async def quick_update(request: Request):
    if not supabase: raise HTTPException(500,"No supabase")
    body = await request.json()
    id = body.get("id")
    if not id: raise HTTPException(400,"id required")
    update = {}
    if "harga_per_satuan" in body: update["harga_per_satuan"]=safe_float(body["harga_per_satuan"])
    if "stock_qty" in body: update["stock_qty"]=safe_float(body["stock_qty"])
    update["updated_at"]=datetime.now().isoformat()
    supabase.table("bahan_inventory").update(update).eq("id", id).execute()
    return {"ok":True}

# ================== OPSI C - INSERT KATEGORI DISTINCT ==================
@app.get("/api/kategori/list")
async def kategori_list():
    utama, sub = get_kategori_data()
    return {"utama":utama,"sub":sub}

@app.post("/api/kategori/sub")
async def create_sub_kategori(request: Request):
    if not supabase: raise HTTPException(500,"Supabase belum konfigurasi")
    try:
        body = await request.json()
        code = str(body.get("code","")).strip().lower()
        label = str(body.get("label","")).strip()
        parent = str(body.get("parent","")).strip().lower()
        if not code or not label or not parent:
            raise HTTPException(400, detail="code, label, parent wajib")
        if len(code) <2 or len(code) >5:
            raise HTTPException(400, detail="kode 2-5 huruf")
        ex = supabase.table("kategori_master").select("code").eq("code", code).execute()
        if ex.data: raise HTTPException(400, detail=f"kode {code} sudah ada")
        res = supabase.table("kategori_master").insert({"code":code,"label":label,"type":"sub","parent":parent,"is_active":True}).execute()
        return {"success":True,"message":f"Sub {code} INSERT ke {parent}","data":res.data[0] if res.data else {}}
    except HTTPException: raise
    except Exception as e: raise HTTPException(500, detail=str(e))

@app.post("/api/kategori/utama")
async def create_utama_kategori(request: Request):
    if not supabase: raise HTTPException(500,"Supabase belum konfigurasi")
    try:
        body = await request.json()
        code = str(body.get("code","")).strip().lower()
        label = str(body.get("label","")).strip()
        if not code or not label: raise HTTPException(400, detail="code, label wajib")
        if len(code)<2 or len(code)>5: raise HTTPException(400, detail="kode 2-5 huruf")
        ex = supabase.table("kategori_master").select("code").eq("code", code).execute()
        if ex.data: raise HTTPException(400, detail=f"kode {code} sudah ada")
        res = supabase.table("kategori_master").insert({"code":code,"label":label,"type":"utama","parent":None,"is_active":True}).execute()
        return {"success":True,"message":f"Kat utama {code} INSERT","data":res.data[0] if res.data else {}}
    except HTTPException: raise
    except Exception as e: raise HTTPException(500, detail=str(e))

# ================== DASHBOARD ROUTES - LENGKAP ANTI NOT FOUND ==================
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse("/dashboard/admin")

@app.get("/dashboard/admin", response_class=HTMLResponse)
async def dashboard_admin(request: Request):
    try:
        stats = await stats_realtime()
        bahan_list = stats.get("items", [])
        menus_list = []
        if supabase:
            try:
                for tbl in ["menu_master", "master_menu", "menu", "menus"]:
                    try:
                        res = supabase.table(tbl).select("*").limit(10).execute()
                        if res.data:
                            menus_list = res.data
                            break
                    except: continue
            except: pass
        if not menus_list:
            menus_list = [{"nama_menu": "Nasi Box Premium", "hpp": 25000},{"nama_menu": "Tumpeng Mini", "hpp": 35000},{"nama_menu": "Snack Box", "hpp": 15000}]
        ctx = {"request": request, "stats": stats, "bahan": bahan_list, "items": bahan_list, "menus": menus_list, "menu_list": menus_list, "role": "ADMIN", **stats}
        ctx["bahan"]=bahan_list; ctx["items"]=bahan_list; ctx["menus"]=menus_list
        if templates is None: return HTMLResponse(f"<h1>JB KITCHEN MRH</h1><pre>{stats}</pre>")
        return templates.TemplateResponse(request, "dashboard_admin.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR {e}</h1><pre>{tb}</pre>", status_code=500)

# INI YANG BIKIN NOT FOUND KEMARIN - SEKARANG DITAMBAHKAN LENGKAP
@app.get("/dashboard/admin/menu", response_class=HTMLResponse)
async def admin_menu(request: Request):
    try:
        stats = await stats_realtime()
        utama, sub = get_kategori_data()
        menus_list = []
        if supabase:
            try:
                for tbl in ["menu_master", "master_menu", "menu", "menus"]:
                    try:
                        res = supabase.table(tbl).select("*").order("nama_menu").execute()
                        if res.data:
                            menus_list = res.data
                            break
                    except: continue
            except: pass
        ctx = {"request": request, "menus": menus_list, "items": menus_list, "kategori_utama": utama, "kategori_sub": sub, "stats": stats, **stats}
        if templates is None: return HTMLResponse("<h1>Templates Not Found</h1>")
        return templates.TemplateResponse(request, "master_menu.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR MENU {e}</h1><pre>{tb}</pre>", status_code=500)

@app.get("/dashboard/admin/inventory", response_class=HTMLResponse)
async def admin_inventory(request: Request):
    try:
        stats = await stats_realtime()
        utama, sub = get_kategori_data()
        ctx = {"request": request, "bahan": stats.get("items",[]), "items": stats.get("items",[]), "kategori_utama": utama, "kategori_sub": sub, "stats": stats, **stats}
        if templates is None: return HTMLResponse("<h1>Templates Not Found</h1>")
        return templates.TemplateResponse(request, "inventory_stock.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR INVENTORY {e}</h1><pre>{tb}</pre>", status_code=500)

@app.get("/dashboard/admin/produksi", response_class=HTMLResponse)
@app.get("/dashboard/admin/paket-bom", response_class=HTMLResponse)
async def admin_paket(request: Request):
    try:
        stats = await stats_realtime()
        utama, sub = get_kategori_data()
        ctx = {"request": request, "stats": stats, "kategori_utama": utama, "kategori_sub": sub, **stats}
        if templates is None: return HTMLResponse("<h1>Templates Not Found</h1>")
        return templates.TemplateResponse(request, "paket_bom.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR PAKET {e}</h1><pre>{tb}</pre>", status_code=500)

@app.get("/dashboard/admin/resep-bom", response_class=HTMLResponse)
@app.get("/dashboard/admin/resep", response_class=HTMLResponse)
async def admin_resep(request: Request):
    try:
        stats = await stats_realtime()
        utama, sub = get_kategori_data()
        ctx = {"request": request, "stats": stats, "kategori_utama": utama, "kategori_sub": sub, **stats}
        if templates is None: return HTMLResponse("<h1>Templates Not Found</h1>")
        return templates.TemplateResponse(request, "resep_bom.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR RESEP {e}</h1><pre>{tb}</pre>", status_code=500)

@app.get("/dashboard/owner", response_class=HTMLResponse)
async def dashboard_owner(request: Request):
    try:
        stats = await stats_realtime()
        ctx = {"request": request, "stats": stats, "bahan": stats.get("items",[]), "role": "OWNER", **stats}
        if templates is None: return HTMLResponse(f"<h1>OWNER</h1><pre>{stats}</pre>")
        return templates.TemplateResponse(request, "dashboard_owner.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR OWNER {e}</h1><pre>{tb}</pre>", status_code=500)

@app.get("/dashboard/produksi", response_class=HTMLResponse)
async def dashboard_produksi(request: Request):
    try:
        stats = await stats_realtime()
        ctx = {"request": request, "stats": stats, "role": "PRODUKSI", **stats}
        if templates is None: return HTMLResponse(f"<h1>PRODUKSI</h1><pre>{stats}</pre>")
        try:
            return templates.TemplateResponse(request, "dashboard_produksi.html", ctx)
        except:
            return templates.TemplateResponse(request, "dashboard_admin.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR PRODUKSI {e}</h1><pre>{tb}</pre>", status_code=500)

@app.get("/dashboard/delivery", response_class=HTMLResponse)
async def dashboard_delivery(request: Request):
    try:
        stats = await stats_realtime()
        ctx = {"request": request, "stats": stats, "role": "DELIVERY", **stats}
        if templates is None: return HTMLResponse(f"<h1>DELIVERY</h1><pre>{stats}</pre>")
        return templates.TemplateResponse(request, "dashboard_delivery.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR DELIVERY {e}</h1><pre>{tb}</pre>", status_code=500)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if templates is None: return HTMLResponse("<h1>Login - Templates Not Found</h1>")
    try:
        return templates.TemplateResponse(request, "login.html", {"request": request})
    except:
        return HTMLResponse("<h1>JB KITCHEN MRH - Login</h1><a href='/dashboard/admin'>Masuk Admin</a>")

# Alias untuk save redirect
@app.get("/dashboard/admin/inventory/save", response_class=HTMLResponse)
async def inv_save_dummy(): return RedirectResponse("/dashboard/admin/inventory")
@app.get("/dashboard/admin/menu/save", response_class=HTMLResponse)
async def menu_save_dummy(): return RedirectResponse("/dashboard/admin/menu")
