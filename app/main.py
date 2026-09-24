"""
JB KITCHEN MRH - FINAL LENGKAP + BOM ID + INVENTORY DETAIL NO EDIT
Fix 1:1 - tambah route /dashboard/admin/inventory/{id}
"""
import os, re, uuid, io, json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from api_kategori import router as kategori_router

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
except Exception as e:
    print(f"[WARN] Supabase init fail: {e}")

app = FastAPI(title="JB KITCHEN MRH - FINAL + DETAIL NO EDIT")
app.include_router (kategori_router)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "app" else BASE_DIR

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
        break

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
        break

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

def safe_float(v, default=0.0) -> float:
    try:
        if v is None or v == "": return default
        return float(v)
    except: return default

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

@app.get("/api/bahan/list")
async def bahan_list():
    if not supabase: return {"items":[],"total":0}
    res = supabase.table("bahan_inventory").select("*").order("nama_bahan").execute()
    return {"items":res.data or [],"total":len(res.data or [])}

@app.get("/api/kategori/list")
async def kategori_list():
    utama, sub = get_kategori_data()
    return {"utama":utama,"sub":sub}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request): return RedirectResponse("/dashboard/admin")

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
                        if res.data: menus_list = res.data; break
                    except: continue
            except: pass
        if not menus_list:
            menus_list = [{"nama_menu": "Nasi Box Premium", "hpp": 25000},{"nama_menu": "Tumpeng Mini", "hpp": 35000},{"nama_menu": "Snack Box", "hpp": 15000}]
        ctx = {"request": request, "stats": stats, "bahan": bahan_list, "items": bahan_list, "menus": menus_list, "menu_list": menus_list, "role": "ADMIN", **stats}
        if templates is None: return HTMLResponse(f"<h1>JB KITCHEN MRH</h1><pre>{stats}</pre>")
        return templates.TemplateResponse(request, "dashboard_admin.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR {e}</h1><pre>{tb}</pre>", status_code=500)

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
                        if res.data: menus_list = res.data; break
                    except: continue
            except: pass
        ctx = {"request": request, "menus": menus_list, "items": menus_list, "kategori_utama": utama, "kategori_sub": sub, "stats": stats, **stats}
        if templates is None: return HTMLResponse("<h1>Templates Not Found</h1>")
        return templates.TemplateResponse(request, "master_menu.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR MENU {e}</h1><pre>{tb}</pre>", status_code=500)

# INVENTORY LIST + DETAIL 1 CARD NO EDIT
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

@app.get("/dashboard/admin/inventory/{bahan_id}", response_class=HTMLResponse)
async def admin_inventory_detail(request: Request, bahan_id: str):
    try:
        stats = await stats_realtime()
        utama, sub = get_kategori_data()
        bahan_data = None
        if supabase:
            try:
                res = supabase.table("bahan_inventory").select("*").eq("id", bahan_id).limit(1).execute()
                if res.data: bahan_data = res.data[0]
            except: pass
        if not bahan_data:
            # fallback cari dari stats items
            for it in stats.get("items",[]):
                if it.get("id")==bahan_id or str(it.get("id"))==bahan_id:
                    bahan_data=it; break
        if not bahan_data:
            bahan_data={"id":bahan_id,"nama_bahan":f"Bahan {bahan_id[:8]}","kode_bahan":f"orgk-dgi-lut-002","kategori_utama":"dgi","kode_kategori":"lut","satuan_default":"Kg","stock_qty":50,"harga_per_satuan":85000,"supplier":"CV Bahari Jaya","no_hp":"0812-3456-7890","alamat":"Jl. Pelabuhan No.12, Sidoarjo"}
        # cari label kategori
        kat_label = next((k["label"] for k in utama if k["code"]==bahan_data.get("kategori_utama")), bahan_data.get("kategori_utama","-"))
        sub_label = next((k["label"] for k in sub if k["code"]==bahan_data.get("kode_kategori")), bahan_data.get("kode_kategori","-"))
        ctx = {"request": request, "bahan": bahan_data, "kategori_label": kat_label, "sub_label": sub_label, "kategori_utama": utama, "kategori_sub": sub, "stats": stats, **stats}
        if templates is None: return HTMLResponse(f"<h1>DETAIL {bahan_id}</h1><pre>{bahan_data}</pre>")
        try:
            return templates.TemplateResponse(request, "inventory_detail.html", ctx)
        except:
            return templates.TemplateResponse(request, "inventory_detail_FINAL_NO_EDIT.html", ctx)
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR DETAIL {e}</h1><pre>{tb}</pre>", status_code=500)

# BOM DETAIL
@app.get("/dashboard/admin/menu/resep/{menu_id}", response_class=HTMLResponse)
@app.get("/dashboard/admin/menu/resep/{menu_id}/", response_class=HTMLResponse)
async def bom_resep_detail(request: Request, menu_id: str):
    try:
        stats = await stats_realtime()
        utama, sub = get_kategori_data()
        menu_data = None
        bom_items = []
        if supabase:
            try:
                for tbl in ["menu_master", "master_menu", "menu", "menus"]:
                    try:
                        res = supabase.table(tbl).select("*").eq("id", menu_id).limit(1).execute()
                        if res.data: menu_data = res.data[0]; break
                    except: continue
            except: pass
        if not menu_data:
            menu_data = {"id": menu_id, "nama_menu": f"Resep {menu_id[:8]}", "kode_menu": f"Resep-{menu_id[:8]}"}
        ctx = {"request": request, "menu": menu_data, "bom": bom_items, "items": bom_items, "kategori_utama": utama, "kategori_sub": sub, "stats": stats, "bahan_list": stats.get("items",[]), **stats}
        if templates is None: return HTMLResponse(f"<h1>BOM Resep {menu_id}</h1>")
        try: return templates.TemplateResponse(request, "resep_bom.html", ctx)
        except: return templates.TemplateResponse(request, "master_menu.html", {"request": request, "menus": [menu_data], **stats})
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR BOM RESEP {e}</h1><pre>{tb}</pre>", status_code=500)

@app.get("/dashboard/admin/menu/paket/{menu_id}", response_class=HTMLResponse)
@app.get("/dashboard/admin/menu/paket/{menu_id}/", response_class=HTMLResponse)
async def bom_paket_detail(request: Request, menu_id: str):
    try:
        stats = await stats_realtime()
        utama, sub = get_kategori_data()
        menu_data = None
        bom_items = []
        if supabase:
            try:
                for tbl in ["menu_master", "master_menu", "menu", "menus"]:
                    try:
                        res = supabase.table(tbl).select("*").eq("id", menu_id).limit(1).execute()
                        if res.data: menu_data = res.data[0]; break
                    except: continue
            except: pass
        if not menu_data:
            menu_data = {"id": menu_id, "nama_menu": f"Paket {menu_id[:8]}", "kode_menu": f"Paket-{menu_id[:8]}"}
        ctx = {"request": request, "menu": menu_data, "paket": menu_data, "bom": bom_items, "items": bom_items, "kategori_utama": utama, "kategori_sub": sub, "stats": stats, "bahan_list": stats.get("items",[]), **stats}
        if templates is None: return HTMLResponse(f"<h1>BOM Paket {menu_id}</h1>")
        try: return templates.TemplateResponse(request, "paket_bom.html", ctx)
        except: return templates.TemplateResponse(request, "master_menu.html", {"request": request, "menus": [menu_data], **stats})
    except Exception as e:
        import traceback; tb=traceback.format_exc()
        return HTMLResponse(f"<h1>ERROR BOM PAKET {e}</h1><pre>{tb}</pre>", status_code=500)

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
        try: return templates.TemplateResponse(request, "dashboard_produksi.html", ctx)
        except: return templates.TemplateResponse(request, "dashboard_admin.html", ctx)
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
    try: return templates.TemplateResponse(request, "login.html", {"request": request})
    except: return HTMLResponse("<h1>JB KITCHEN MRH - Login</h1><a href='/dashboard/admin'>Masuk Admin</a>")

@app.get("/dashboard/admin/inventory/save", response_class=HTMLResponse)
async def inv_save_dummy(): return RedirectResponse("/dashboard/admin/inventory")
@app.get("/dashboard/admin/menu/save", response_class=HTMLResponse)
async def menu_save_dummy(): return RedirectResponse("/dashboard/admin/menu")
