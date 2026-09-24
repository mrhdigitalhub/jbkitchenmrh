from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter(prefix="/api/kategori", tags=["Kategori"])

class KategoriUtamaCreate(BaseModel):
    code: str
    label: str

class KategoriSubCreate(BaseModel):
    code: str
    label: str
    parent_code: str

def get_supabase():
    # ULTRA SAFE - tidak import dari app.main sama sekali untuk hindari circular import
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            print(f"[WARN] SUPABASE_URL/KEY kosong di Vercel ENV")
            return None
        return create_client(url, key)
    except Exception as e:
        print(f"[WARN] get_supabase fail: {e}")
        return None

def fallback_data():
    return {
        "utama": [
            {"code":"nbt","label":"Bahan Nabati","type":"utama"},
            {"code":"dgi","label":"Bahan Hewani / Daging","type":"utama"},
            {"code":"prs","label":"Perasa / Saus","type":"utama"},
            {"code":"pck","label":"Packaging Kertas / Karton","type":"utama"},
            {"code":"cuc","label":"Cuci / Chemical","type":"utama"},
            {"code":"plk","label":"Plastik & Kemasan","type":"utama"},
        ],
        "sub": [
            {"code":"syr","label":"Sayuran","parent":"nbt"},
            {"code":"umb","label":"Umbi-umbian","parent":"nbt"},
            {"code":"kcg","label":"Kacang & Bijian","parent":"nbt"},
            {"code":"rmp","label":"Rempah","parent":"nbt"},
            {"code":"srl","label":"Serealia / Beras","parent":"nbt"},
            {"code":"myk","label":"Minyak & Lemak","parent":"nbt"},
            {"code":"buh","label":"Buah","parent":"nbt"},
            {"code":"bdr","label":"Bumbu Dasar","parent":"nbt"},
            {"code":"ugs","label":"Unggas Potong","parent":"dgi"},
            {"code":"sap","label":"Sapi","parent":"dgi"},
            {"code":"lut","label":"Laut / Seafood","parent":"dgi"},
            {"code":"oss","label":"Olahan Susu","parent":"dgi"},
            {"code":"tlr","label":"Telur / Unggas","parent":"dgi"},
            {"code":"ras","label":"Rasa / Saus","parent":"prs"},
            {"code":"ins","label":"Instant / Bumbu Instan","parent":"prs"},
            {"code":"krt","label":"Kertas / Karton","parent":"pck"},
            {"code":"pls","label":"Plastik Styrofoam","parent":"pck"},
            {"code":"cir","label":"Cairan","parent":"cuc"},
            {"code":"mnm","label":"Minuman / Air","parent":"plk"},
            {"code":"sdk","label":"Sendok+garpu plastik","parent":"plk"},
        ]
    }

@router.get("/list")
def list_kategori():
    sb = get_supabase()
    if sb is None:
        return fallback_data()
    try:
        utama = sb.table("kategori_utama").select("*").order("code").execute()
        sub = sb.table("kategori_sub").select("*").order("code").execute()
        return {
            "utama": [{"code": u["code"], "label": u["label"], "type": u.get("type","utama")} for u in utama.data],
            "sub": [{"code": s["code"], "label": s["label"], "parent": s["parent_code"]} for s in sub.data]
        }
    except Exception as e:
        print(f"[WARN] list kategori fallback karena {e}")
        return fallback_data()

@router.post("/utama/save")
def save_kategori_utama(payload: KategoriUtamaCreate):
    sb = get_supabase()
    if sb is None: raise HTTPException(status_code=500, detail="Supabase belum init, cek ENV di Vercel")
    code = payload.code.lower().strip()[:3]; label = payload.label.strip()
    if len(code)!=3: raise HTTPException(status_code=400, detail="Code 3 huruf")
    existing = sb.table("kategori_utama").select("code").eq("code",code).execute()
    if existing.data: raise HTTPException(status_code=400, detail=f"Code {code} sudah ada")
    result = sb.table("kategori_utama").insert({"code":code,"label":label,"type":"utama"}).execute()
    return {"success":True,"data":result.data[0] if result.data else {"code":code,"label":label}}

@router.delete("/utama/{code}")
def delete_kategori_utama(code: str):
    sb = get_supabase()
    if sb is None: raise HTTPException(status_code=500, detail="Supabase belum init")
    code=code.lower().strip()
    bahan_check = sb.table("bahan").select("id").eq("kategori_utama",code).limit(1).execute()
    if bahan_check.data: raise HTTPException(status_code=400, detail=f"Tidak bisa hapus {code}, dipakai bahan")
    sb.table("kategori_sub").delete().eq("parent_code",code).execute()
    sb.table("kategori_utama").delete().eq("code",code).execute()
    return {"success":True}

@router.post("/sub/save")
def save_kategori_sub(payload: KategoriSubCreate):
    sb = get_supabase()
    if sb is None: raise HTTPException(status_code=500, detail="Supabase belum init")
    code=payload.code.lower().strip()[:3]; label=payload.label.strip(); parent=payload.parent_code.lower().strip()
    if len(code)!=3 or not label or not parent: raise HTTPException(status_code=400, detail="Data tidak lengkap")
    parent_check = sb.table("kategori_utama").select("code").eq("code",parent).execute()
    if not parent_check.data: raise HTTPException(status_code=400, detail=f"Parent {parent} tidak ada")
    existing = sb.table("kategori_sub").select("code").eq("code",code).execute()
    if existing.data: raise HTTPException(status_code=400, detail=f"Code {code} sudah ada")
    result = sb.table("kategori_sub").insert({"code":code,"label":label,"parent_code":parent}).execute()
    return {"success":True,"data":result.data[0] if result.data else {"code":code,"label":label,"parent_code":parent}}

@router.delete("/sub/{code}")
def delete_kategori_sub(code: str):
    sb = get_supabase()
    if sb is None: raise HTTPException(status_code=500, detail="Supabase belum init")
    code=code.lower().strip()
    bahan_check = sb.table("bahan").select("id").eq("kode_kategori",code).limit(1).execute()
    if bahan_check.data: raise HTTPException(status_code=400, detail=f"Tidak bisa hapus sub {code}")
    sb.table("kategori_sub").delete().eq("code",code).execute()
    return {"success":True}
