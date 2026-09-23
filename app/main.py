"""
JB KITCHEN MRH - Clean Fixed v10.2
FIX: TemplateResponse untuk FastAPI 0.115+ & Starlette 1.6+ (Vercel)
Rumus HPP & Variabel DIKUNCI - Tidak diubah
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
        print("[WARN] SUPABASE_URL/KEY belum di-set di ENV")
except Exception as e:
    print(f"[WARN] Supabase init fail: {e}")

app = FastAPI(title="JB KITCHEN MRH - Clean 950Ln v10.2 - SYNC FIX 3.14")
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "app" else BASE_DIR

# FIX SYNC FINAL - Cari templates di semua lokasi (lokal & Vercel)
templates = None
templates_candidates = [
    BASE_DIR / "templates",                  # app/templates jika file di app/main.py
    BASE_DIR / "app" / "templates",          # app/app/templates (jaga2)
    PROJECT_ROOT / "app" / "templates",      # root/app/templates (struktur Bapak)
    PROJECT_ROOT / "templates",              # root/templates
    Path.cwd() / "app" / "templates",
    Path.cwd() / "templates",
]
for cand in templates_candidates:
    if cand.exists():
        templates = Jinja2Templates(directory=str(cand))
        print(f"[OK] Templates loaded: {cand}")
        break
if templates is None:
    print(f"[FATAL] Templates tidak ketemu. Cek: {templates_candidates}")

# FIX SYNC FINAL - Static
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
        print(f"[OK] Static mounted: {static_cand}")
        break

# ================== KONSTANTA - TETAP SESUAI SPEC EXISTING ==================
DEFAULT_KAT_UTAMA = [
    {"code":"cuc","label":"Cuci / Chemical","type":"utama"},
    {"code":"dgi","label":"Bahan Hewani / Daging","type":"utama"},
    {"code":"nbt","label":"Bahan Nabati","type":"utama"},
    {"code":"pck","label":"Packaging Kertas / Karton","type":"utama"},
    {"code":"plk","label":"Plastik & Kemasan","type":"utama"},
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
    {"code":"krt","label":"Kertas / Karton","parent":"pck","type":"sub"},
    {"code":"pls","label":"Plastik Styrofoam","parent":"pck","type":"sub"},
    {"code":"sdk","label":"Sendok / Saji / Alat","parent":"pck","type":"sub"},
    {"code":"mnm","label":"Minuman / Air","parent":"plk","type":"sub"},
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

# ================== HELPERS - ANTI BOLAK-BALIK ==================
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
    margin_percent, ppn_percent = 0.40, 0.11
    margin_rp = hpp_final_per_porsi * margin_percent
    subtotal = hpp_final_per_porsi + margin_rp
    ppn_rp = subtotal * ppn_percent
    harga_jual = subtotal + ppn_rp
    return {
        "hpp_bahan_total":hpp_bahan_total,
        "hpp_bahan_per_porsi":hpp_per_porsi,
        "oh_percent":oh*100,"oh_cost":hpp_per_porsi*oh,
        "delivery_percent":delivery*100,"delivery_cost":hpp_per_porsi*delivery,
        "manpower":manpower,"manpower_per_porsi":total_mp,
        "manpower_detail":manpower,
        "hpp_final_per_porsi":hpp_final_per_porsi,
        "hpp_final_total":hpp_final_per_porsi*porsi,
        "margin_percent":margin_percent*100,"margin_rp":margin_rp,
        "subtotal_hpp_margin":subtotal,
        "ppn_percent":ppn_percent*100,"ppn_rp":ppn_rp,
        "harga_jual_per_porsi":harga_jual,
        "harga_jual_total":harga_jual*porsi
    }

def konversi_ke_default(bahan: dict, qty_input: float, satuan_input: str):
    sd = (bahan.get("satuan_default") or "Kg").lower()
    si = (satuan_input or sd).lower()
    kj = parse_konversi_json(bahan.get("konversi_json"))
    qty = safe_float(qty_input,0)
    if si == sd: return qty
    if si in kj: return qty * safe_float(kj[si],1)
    if si in ["gram","gr","g"] and sd=="kg": return qty*0.001
    if si in ["kg","kilo"] and sd in ["gram","gr","g"]: return qty*1000
    if si=="pcs" and sd=="kg":
        nama=(bahan.get("nama_bahan") or "").lower()
        if "telur" in nama: return qty*0.06
        return qty*0.05
    if si=="kg" and sd=="pcs":
        nama=(bahan.get("nama_bahan") or "").lower()
        if "telur" in nama: return qty/0.06
        return qty/0.05
    return qty

# ================== ROUTES CORE ==================
@app.get("/health")
async def health():
    return {"status":"ok","app":"JB KITCHEN MRH Clean 950Ln v10.2","supabase":bool(supabase),"time":datetime.now().isoformat()}

@app.get("/api/stats/realtime")
async def stats_realtime():
    if not supabase:
        return {"total_bahan":0,"aset_inventory":0,"stock_min":0,"total_menu":0,"items":[]}
    try:
        bahan_all = supabase.table("bahan_inventory").select("id,kode_bahan,nama_bahan,stock_qty,harga_per_satuan,stock_minimum,satuan_default").execute()
        all_data = bahan_all.data or []
        total = len(all_data)
        aset = sum([safe_float(b.get("stock_qty"))*safe_float(b.get("harga_per_satuan")) for b in all_data])
        min_all = [b for b in all_data if safe_float(b.get("stock_qty")) <= safe_float(b.get("stock_minimum"),5)]
        stock_min = len(min_all)
        sorted_min = sorted(all_data, key=lambda x: safe_float(x.get("stock_qty")))[:5]
        display = min_all[:5] if len(min_all)>=1 else sorted_min
        for b in display:
            if b.get("nama_bahan"): b["nama_bahan"]=format_nama(b["nama_bahan"])
        total_menu = 0
        try:
            menu_res=supabase.table("menu_master").select("id",count="exact").execute()
            total_menu=menu_res.count or len(menu_res.data or [])
        except: pass
        return {"total_bahan":total,"aset_inventory":aset,"stock_min":stock_min,"total_menu":total_menu,"items":display,"timestamp":datetime.now().isoformat()}
    except Exception as e:
        return {"error":str(e),"total_bahan":0,"aset_inventory":0,"stock_min":0,"total_menu":0,"items":[]}

# ================== BAHAN CRUD ==================
@app.get("/dashboard/admin/inventory", response_class=HTMLResponse)
@app.get("/inventory_stock", response_class=HTMLResponse)
async def inventory_stock(request: Request):
    bahan = []
    if supabase:
        try:
            res = supabase.table("bahan_inventory").select("*").order("kode_bahan").execute()
            bahan = res.data or []
        except Exception as e:
            print(e)
    if templates is None:
        return HTMLResponse(f"<h3>Inventory JB KITCHEN MRH</h3><p>Total: {len(bahan)} bahan</p><p>Template folder belum ditemukan di server.</p>")
    return templates.TemplateResponse(request, "inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan)})

@app.post("/dashboard/admin/inventory/save")
async def inventory_save(request: Request):
    if not supabase: raise HTTPException(500,"Supabase not configured")
    form = await request.form()
    data = dict(form)
    stock_awal = safe_float(data.get("stock_awal"),0)
    tambah = safe_float(data.get("tambah"),0)
    terpakai = safe_float(data.get("terpakai"),0)
    stock_qty = stock_awal + tambah - terpakai
    if stock_qty == 0 and data.get("stock_qty"):
        stock_qty = safe_float(data.get("stock_qty"))
    harga_awal = safe_float(data.get("harga_awal"),0)
    harga_baru = safe_float(data.get("harga_baru"),0)
    harga_final = harga_baru if harga_baru>0 else harga_awal
    if harga_final == 0 and data.get("harga_per_satuan"):
        harga_final = safe_float(data.get("harga_per_satuan"))
    payload = {
        "kode_bahan": data.get("kode_bahan"),
        "nama_bahan": (data.get("nama_bahan") or "").lower(),
        "merek": data.get("merek"),
        "kategori_utama": data.get("kategori_utama"),
        "kode_kategori": data.get("kode_kategori"),
        "satuan_default": data.get("satuan_default") or "Kg",
        "stock_qty": stock_qty,
        "harga_per_satuan": harga_final,
        "id_halal": data.get("id_halal"),
        "orgk_flag": data.get("orgk_flag") or "Orgk",
        "hall_flag": data.get("hall_flag"),
        "updated_at": datetime.now().isoformat()
    }
    payload = {k:v for k,v in payload.items() if v is not None}
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

@app.post("/api/bahan/import")
async def import_bahan(file: UploadFile = File(...)):
    if not supabase: raise HTTPException(500,"No supabase")
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content)) if file.filename.endswith("xlsx") else pd.read_csv(io.BytesIO(content))
        df.columns = [c.lower().strip() for c in df.columns]
        imported = 0
        for _, row in df.iterrows():
            kode = str(row.get("kode") or row.get("kode_bahan") or "").strip()
            nama = str(row.get("nama") or row.get("nama_bahan") or "").strip().lower()
            if not nama: continue
            payload = {
                "id": str(uuid.uuid4()),
                "kode_bahan": kode or f"AUTO-{uuid.uuid4().hex[:6]}",
                "nama_bahan": nama,
                "stock_qty": safe_float(row.get("stock") or row.get("stock_qty"),0),
                "harga_per_satuan": safe_float(row.get("harga") or row.get("harga_per_satuan"),0),
                "satuan_default": str(row.get("sat") or row.get("satuan") or "Kg"),
                "kategori_utama": str(row.get("kategori_utama") or ""),
                "kode_kategori": str(row.get("sub") or row.get("kode_kategori") or ""),
            }
            supabase.table("bahan_inventory").insert(payload).execute()
            imported+=1
        return {"ok":True,"imported":imported}
    except Exception as e:
        raise HTTPException(500, f"Import error: {e}")

@app.post("/api/bahan/fix-typo-lut")
async def fix_typo_lut():
    if not supabase: raise HTTPException(500,"No supabase")
    try:
        res = supabase.table("bahan_inventory").select("id,kode_bahan,kode_kategori").or_("kode_bahan.ilike.%1ut%,kode_kategori.eq.1ut").execute()
        fixed = 0
        for row in (res.data or []):
            old_kode = row.get("kode_bahan","")
            new_kode = old_kode.lower().replace("-1ut-","-lut-").replace("1ut","lut")
            upd = {"kode_bahan": new_kode, "kode_kategori":"lut" if "lut" in new_kode else row.get("kode_kategori")}
            if upd["kode_kategori"]=="1ut": upd["kode_kategori"]="lut"
            supabase.table("bahan_inventory").update(upd).eq("id", row["id"]).execute()
            fixed+=1
        return {"ok":True,"fixed":fixed,"message":f"Fixed {fixed} bahan dari 1ut -> lut"}
    except Exception as e:
        raise HTTPException(500,str(e))

@app.delete("/api/bahan/typo-1ut")
async def delete_typo_1ut():
    if not supabase: raise HTTPException(500,"No supabase")
    try:
        res=supabase.table("bahan_inventory").select("id").or_("kode_bahan.ilike.%1ut%,kode_kategori.eq.1ut").execute()
        deleted=0
        for row in (res.data or []):
            supabase.table("bahan_inventory").delete().eq("id",row["id"]).execute()
            deleted+=1
        return {"ok":True,"deleted":deleted}
    except Exception as e:
        raise HTTPException(500,str(e))

@app.delete("/api/bahan/clear-all")
async def clear_all():
    if not supabase: raise HTTPException(500,"No supabase")
    res = supabase.table("bahan_inventory").select("id").execute()
    for row in (res.data or []):
        supabase.table("bahan_inventory").delete().eq("id",row["id"]).execute()
    return {"ok":True,"deleted":len(res.data or [])}

@app.get("/api/kamus/list")
async def kamus_list():
    kamus=KAMUS_DEFAULT_LOCAL.copy()
    if supabase:
        try:
            res=supabase.table("kamus_bom").select("*").execute()
            for row in res.data or []:
                nama=(row.get("nama_bahan") or "").lower()
                if nama:
                    kamus[nama]={"qty":safe_float(row.get("qty_standar"),0.15),"satuan":row.get("satuan_standar","Kg"),"satuan_default":row.get("satuan_default","Kg"),"konversi_json":parse_konversi_json(row.get("konversi_json")),"label":row.get("label",f"{nama}")}
        except Exception as e:
            print(f"kamus list error: {e}")
    return {"items":kamus,"source":"supabase+default"}

@app.post("/api/kamus/save")
async def kamus_save(request: Request):
    body=await request.json()
    nama=(body.get("nama_bahan") or "").lower().strip()
    if not nama: raise HTTPException(400,"nama_bahan required")
    data={"nama_bahan":nama,"qty_standar":safe_float(body.get("qty"),0.15),"satuan_standar":body.get("satuan","Kg"),"satuan_default":body.get("satuan_default","Kg"),"konversi_json":body.get("konversi_json",{}),"label":body.get("label",f"{nama}"),"updated_at":datetime.now().isoformat()}
    if supabase:
        try:
            ex=supabase.table("kamus_bom").select("id").eq("nama_bahan",nama).limit(1).execute()
            if ex.data: supabase.table("kamus_bom").update(data).eq("nama_bahan",nama).execute()
            else: supabase.table("kamus_bom").insert(data).execute()
        except Exception as e:
            raise HTTPException(500,str(e))
    return {"saved":True}

@app.delete("/api/kamus/delete/{nama_bahan}")
async def kamus_delete(nama_bahan: str):
    if not supabase: raise HTTPException(500,"No supabase")
    supabase.table("kamus_bom").delete().eq("nama_bahan",nama_bahan.lower().strip()).execute()
    return {"deleted":True}

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
        # Debug: jika stats error
        if "error" in stats and stats.get("total_bahan", 0) == 0:
            print(f"[ADMIN ERROR] {stats.get('error')}")
        if templates is None:
            return HTMLResponse(f"<h1>JB KITCHEN MRH - Templates NOT FOUND</h1><pre>{json.dumps(stats, indent=2, default=str)}</pre><p>Candidates checked: {templates_candidates if 'templates_candidates' in globals() else 'unknown'}</p>")
        # Pastikan dashboard_admin.html ada
        return templates.TemplateResponse(request, "dashboard_admin.html", {"request": request, **stats})
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ADMIN CRASH] {e}\n{tb}")
        return HTMLResponse(f"<h1>JB KITCHEN MRH - ERROR DEBUG</h1><h3>Error: {e}</h3><pre>{tb}</pre><hr><pre>ENV SUPABASE_URL set: {bool(os.getenv('SUPABASE_URL'))} | SUPABASE_KEY set: {bool(os.getenv('SUPABASE_KEY'))}</pre>", status_code=500)

@app.get("/dashboard/admin/inventory/save", response_class=HTMLResponse)
async def inv_save_dummy(): return RedirectResponse("/dashboard/admin/inventory")
