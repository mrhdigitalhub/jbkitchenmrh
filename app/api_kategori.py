"""
API Supabase untuk Kategori Utama & Sub Kategori
JB KITCHEN - Inventory Master Bahan
File: api_kategori.py atau tambahkan ke main.py

JANGAN MERUBAH FILE FINAL inventory_stock.html & inventory_detail.html display
Hanya tambahkan endpoint baru untuk fitur Kelola Kategori
"""

# ==================== 1. SQL UNTUK SUPABASE (jalankan di SQL Editor) ====================

SQL_CREATE_TABLES = """
-- Tabel Kategori Utama (6 asli + bisa tambah)
CREATE TABLE IF NOT EXISTS kategori_utama (
  code VARCHAR(10) PRIMARY KEY,
  label VARCHAR(100) NOT NULL,
  type VARCHAR(20) DEFAULT 'utama',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel Sub Kategori (19 asli + bisa tambah)
CREATE TABLE IF NOT EXISTS kategori_sub (
  code VARCHAR(10) PRIMARY KEY,
  label VARCHAR(100) NOT NULL,
  parent_code VARCHAR(10) REFERENCES kategori_utama(code) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index untuk performa
CREATE INDEX IF NOT EXISTS idx_kategori_sub_parent ON kategori_sub(parent_code);

-- Insert data awal 6 Kategori Utama (sesuai file final Bapak)
INSERT INTO kategori_utama (code, label, type) VALUES
  ('nbt', 'Bahan Nabati', 'utama'),
  ('dgi', 'Bahan Hewani / Daging', 'utama'),
  ('prs', 'Perasa / Saus', 'utama'),
  ('pck', 'Packaging Kertas / Karton', 'utama'),
  ('cuc', 'Cuci / Chemical', 'utama'),
  ('plk', 'Plastik & Kemasan', 'utama')
ON CONFLICT (code) DO NOTHING;

-- Insert data awal 19 Sub Kategori
INSERT INTO kategori_sub (code, label, parent_code) VALUES
  ('syr', 'Sayuran', 'nbt'),
  ('umb', 'Umbi-umbian', 'nbt'),
  ('kcg', 'Kacang & Bijian', 'nbt'),
  ('rmp', 'Rempah', 'nbt'),
  ('srl', 'Serealia / Beras', 'nbt'),
  ('myk', 'Minyak & Lemak', 'nbt'),
  ('buh', 'Buah', 'nbt'),
  ('bdr', 'Bumbu Dasar', 'nbt'),
  ('ugs', 'Unggas Potong', 'dgi'),
  ('sap', 'Sapi', 'dgi'),
  ('lut', 'Laut / Seafood', 'dgi'),
  ('oss', 'Olahan Susu', 'dgi'),
  ('tlr', 'Telur / Unggas', 'dgi'),
  ('ras', 'Rasa / Saus', 'prs'),
  ('ins', 'Instant / Bumbu Instan', 'prs'),
  ('krt', 'Kertas / Karton', 'pck'),
  ('pls', 'Plastik Styrofoam', 'pck'),
  ('cir', 'Cairan', 'cuc'),
  ('mnm', 'Minuman / Air', 'plk'),
  ('sdk', 'Sendok+garpu plastik', 'plk')
ON CONFLICT (code) DO NOTHING;

-- Enable RLS (optional, sesuaikan dengan policy bahan)
ALTER TABLE kategori_utama ENABLE ROW LEVEL SECURITY;
ALTER TABLE kategori_sub ENABLE ROW LEVEL SECURITY;

-- Policy: allow all for authenticated (sesuaikan dengan project Bapak)
DROP POLICY IF EXISTS "allow_all_kategori_utama" ON kategori_utama;
CREATE POLICY "allow_all_kategori_utama" ON kategori_utama FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "allow_all_kategori_sub" ON kategori_sub;
CREATE POLICY "allow_all_kategori_sub" ON kategori_sub FOR ALL USING (true) WITH CHECK (true);
"""

# ==================== 2. FASTAPI ROUTES (tambahkan ke main.py) ====================

FASTAPI_CODE = '''
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from supabase import create_client, Client

# Supabase client (gunakan env yang sudah ada di main.py Bapak)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter(prefix="/api/kategori", tags=["Kategori"])

class KategoriUtamaCreate(BaseModel):
    code: str
    label: str

class KategoriSubCreate(BaseModel):
    code: str
    label: str
    parent_code: str

# GET /api/kategori/list - untuk dropdown di modal bahan
@router.get("/list")
def list_kategori():
    try:
        utama = supabase.table("kategori_utama").select("*").order("code").execute()
        sub = supabase.table("kategori_sub").select("*").order("code").execute()
        # format sesuai yang dipakai di inventory_stock.html: {utama: [...], sub: [...]}
        return {
            "utama": [{"code": u["code"], "label": u["label"], "type": u.get("type","utama")} for u in utama.data],
            "sub": [{"code": s["code"], "label": s["label"], "parent": s["parent_code"]} for s in sub.data]
        }
    except Exception as e:
        # fallback ke hardcode 6+19 kalau tabel belum ada
        print(f"Error list kategori: {e}")
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

# POST /api/kategori/utama/save - tambah kategori utama baru
@router.post("/utama/save")
def save_kategori_utama(payload: KategoriUtamaCreate):
    code = payload.code.lower().strip()[:3]
    label = payload.label.strip()
    if len(code) != 3:
        raise HTTPException(status_code=400, detail="Code harus 3 huruf")
    if not label:
        raise HTTPException(status_code=400, detail="Label wajib")
    
    # cek duplikat
    existing = supabase.table("kategori_utama").select("code").eq("code", code).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail=f"Code {code} sudah ada")
    
    try:
        result = supabase.table("kategori_utama").insert({"code": code, "label": label, "type": "utama"}).execute()
        return {"success": True, "data": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# DELETE /api/kategori/utama/{code} - hapus kategori utama (cek masih dipakai bahan?)
@router.delete("/utama/{code}")
def delete_kategori_utama(code: str):
    code = code.lower().strip()
    # cek apakah masih dipakai bahan
    try:
        bahan_check = supabase.table("bahan").select("id").eq("kategori_utama", code).limit(1).execute()
        if bahan_check.data:
            raise HTTPException(status_code=400, detail=f"Tidak bisa hapus {code}, masih dipakai {len(bahan_check.data)} bahan. Hapus/pindah bahan dulu.")
        
        # hapus sub dulu yang parent_code = code (karena CASCADE, tapi cek dulu)
        supabase.table("kategori_sub").delete().eq("parent_code", code).execute()
        supabase.table("kategori_utama").delete().eq("code", code).execute()
        return {"success": True, "message": f"Kategori {code} dihapus"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST /api/kategori/sub/save - tambah sub kategori baru
@router.post("/sub/save")
def save_kategori_sub(payload: KategoriSubCreate):
    code = payload.code.lower().strip()[:3]
    label = payload.label.strip()
    parent = payload.parent_code.lower().strip()
    
    if not parent:
        raise HTTPException(status_code=400, detail="Parent kategori utama wajib")
    if len(code) != 3:
        raise HTTPException(status_code=400, detail="Code harus 3 huruf")
    if not label:
        raise HTTPException(status_code=400, detail="Label wajib")
    
    # cek parent ada
    parent_check = supabase.table("kategori_utama").select("code").eq("code", parent).execute()
    if not parent_check.data:
        raise HTTPException(status_code=400, detail=f"Parent {parent} tidak ada")
    
    # cek duplikat sub
    existing = supabase.table("kategori_sub").select("code").eq("code", code).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail=f"Code sub {code} sudah ada")
    
    try:
        result = supabase.table("kategori_sub").insert({"code": code, "label": label, "parent_code": parent}).execute()
        return {"success": True, "data": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# DELETE /api/kategori/sub/{code} - hapus sub kategori
@router.delete("/sub/{code}")
def delete_kategori_sub(code: str):
    code = code.lower().strip()
    try:
        bahan_check = supabase.table("bahan").select("id").eq("kode_kategori", code).limit(1).execute()
        if bahan_check.data:
            raise HTTPException(status_code=400, detail=f"Tidak bisa hapus sub {code}, masih dipakai bahan. Hapus/pindah bahan dulu.")
        
        supabase.table("kategori_sub").delete().eq("code", code).execute()
        return {"success": True, "message": f"Sub {code} dihapus"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Tambahkan di main.py Bapak:
# from api_kategori import router as kategori_router
# app.include_router(kategori_router)
'''

# ==================== 3. CARA PASANG DI VERCEL ====================

INSTRUKSI = """
1. Buka Supabase Dashboard > SQL Editor > New Query
2. Copy paste SQL_CREATE_TABLES di atas > RUN
3. Cek Table Editor: kategori_utama (6 row) dan kategori_sub (20 row) harus ada

4. Di project Vercel (FastAPI):
   - Buat file baru app/api_kategori.py
   - Copy FASTAPI_CODE di atas ke file tersebut
   - Di main.py tambahkan:
     from api_kategori import router as kategori_router
     app.include_router(kategori_router)

5. Deploy:
   git add app/api_kategori.py app/main.py
   git commit -m "feat: API Supabase kategori utama & sub - kelola kategori"
   git push origin main

6. Test:
   - GET https://kitchenmrh.vercel.app/api/kategori/list -> harus return 6 utama + 20 sub
   - Buka /dashboard/admin/inventory -> klik + Tambah -> klik [+ Kelola] -> tambah bbu - Bumbu Basah
   - Cek dropdown Kategori Utama langsung ada Bumbu Basah tanpa refresh
   - Buat bahan baru dengan kategori baru -> simpan -> total bahan 50 -> Dashboard live update

Flow sesuai yang Bapak minta:
- ✏️ Edit = update supplier/stock/harga kode sama (tetap)
- + Tambah = bahan baru (tetap)
- [+ Kelola] = tambah/hapus kategori utama & sub (baru, tidak rubah display final)
"""

print(INSTRUKSI)
