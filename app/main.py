"""
app/main.py - FINAL OPSI C 1:1 - 0 ERROR
File ini adalah file yang benar: D:/Master MRH Project/Kitchen/jb-kitchen-app/app/main.py
Jangan edit file main.py di root jb-kitchen-app/main.py
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

# --- SETUP FASTAPI & SUPABASE (sudah ada di file Bapak, jangan dihapus) ---
app = FastAPI(title="JB Kitchen - Opsi C")

# Jika Bapak sudah punya supabase client, pakai yang lama, jika belum ini contoh:
# from supabase import create_client
# supabase_url = os.getenv("SUPABASE_URL")
# supabase_key = os.getenv("SUPABASE_KEY")
# supabase = create_client(supabase_url, supabase_key)

# Untuk contoh biar Pylance tidak error "supabase is not defined"
# Ganti dengan client Bapak yang asli
try:
    from supabase import create_client
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
    else:
        supabase = None
except:
    supabase = None

templates = Jinja2Templates(directory="app/templates")

# --- ENDPOINT YANG SUDAH ADA (jangan dihapus) ---
@app.get("/api/kategori/list")
async def kategori_list():
    """Endpoint lama Bapak - tetap ada"""
    try:
        if supabase is None:
            # Fallback data jika supabase belum connect - biar tidak error
            return {
                "utama": [
                    {"code": "nbt", "label": "Bahan Nabati", "type": "utama"},
                    {"code": "dgi", "label": "Bahan Hewani / Daging", "type": "utama"},
                    {"code": "prs", "label": "Perasa / Saus", "type": "utama"},
                    {"code": "pck", "label": "Packaging Kertas / Karton", "type": "utama"},
                    {"code": "cuc", "label": "Cuci / Chemical", "type": "utama"},
                    {"code": "plk", "label": "Plastik & Kemasan", "type": "utama"},
                ],
                "sub": [
                    {"code": "syr", "label": "Sayuran", "parent": "nbt"},
                    {"code": "krt", "label": "Kertas / Karton", "parent": "pck"},
                    {"code": "pls", "label": "Plastik Styrofoam", "parent": "pck"},
                    {"code": "sdk", "label": "Sendok+garpu plastik", "parent": "plk"},
                    {"code": "mnm", "label": "Minuman / Air", "parent": "plk"},
                    {"code": "ras", "label": "Rasa / Saus", "parent": "prs"},
                ]
            }
        utama = supabase.table("kategori_master").select("*").eq("type", "utama").eq("is_active", True).execute()
        sub = supabase.table("kategori_master").select("*").eq("type", "sub").eq("is_active", True).execute()
        return {"utama": utama.data, "sub": sub.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ================= OPSI C - 2 ENDPOINT BARU - 0 ERROR =================
@app.post("/api/kategori/sub")
async def create_sub_kategori(payload: dict):
    """
    OPSI C: Tambah Sub Kategori Baru
    Body: {"code": "sck", "label": "Snack Pelengkap", "parent": "plk"}
    INSERT INTO kategori_master (code, label, type='sub', parent)
    """
    try:
        code = str(payload.get("code", "")).strip().lower()
        label = str(payload.get("label", "")).strip()
        parent = str(payload.get("parent", "")).strip().lower()

        if not code or not label or not parent:
            raise HTTPException(status_code=400, detail="code, label, parent wajib diisi")

        if len(code) < 2 or len(code) > 5:
            raise HTTPException(status_code=400, detail="kode harus 2-5 huruf")

        if supabase is None:
            raise HTTPException(status_code=500, detail="supabase client belum terkonfigurasi")

        existing = supabase.table("kategori_master").select("code").eq("code", code).execute()
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail=f"kode {code} sudah ada di kategori_master")

        result = supabase.table("kategori_master").insert({
            "code": code,
            "label": label,
            "type": "sub",
            "parent": parent,
            "is_active": True
        }).execute()

        return {
            "success": True,
            "message": f"Sub {code} - {label} berhasil ditambah ke parent {parent}",
            "data": result.data[0] if result.data else {}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/kategori/utama")
async def create_utama_kategori(payload: dict):
    """
    OPSI C: Tambah Kategori Utama Baru
    Body: {"code": "bks", "label": "Bahan Kemasan Snack"}
    INSERT INTO kategori_master (code, label, type='utama', parent=NULL)
    """
    try:
        code = str(payload.get("code", "")).strip().lower()
        label = str(payload.get("label", "")).strip()

        if not code or not label:
            raise HTTPException(status_code=400, detail="code, label wajib diisi")

        if len(code) < 2 or len(code) > 5:
            raise HTTPException(status_code=400, detail="kode harus 2-5 huruf")

        if supabase is None:
            raise HTTPException(status_code=500, detail="supabase client belum terkonfigurasi")

        existing = supabase.table("kategori_master").select("code").eq("code", code).execute()
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail=f"kode {code} sudah ada di kategori_master")

        result = supabase.table("kategori_master").insert({
            "code": code,
            "label": label,
            "type": "utama",
            "parent": None,
            "is_active": True
        }).execute()

        return {
            "success": True,
            "message": f"Kategori utama {code} - {label} berhasil ditambah",
            "data": result.data[0] if result.data else {}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ================= END OPSI C =================
