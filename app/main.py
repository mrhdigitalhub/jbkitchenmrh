"""
TEMPLATE app/main.py FIXED - OPSI C 1:1 - 0 ERROR
Copy 2 endpoint ini ke file app/main.py Bapak yang sudah ada
Pastikan di atas file sudah ada import ini (jika belum ada, tambahkan):
"""
# --- PASTIKAN IMPORT INI ADA DI ATAS FILE app/main.py ---
# from fastapi import FastAPI, HTTPException, Request
# from supabase import create_client  # atau client supabase Bapak yang sudah ada
# app = FastAPI()  # sudah ada
# supabase = create_client(...)  # sudah ada

# --- PASTE 2 ENDPOINT INI DI BAWAH endpoint /api/kategori/list ---

@app.post("/api/kategori/sub")
async def create_sub_kategori(payload: dict):
    try:
        code = str(payload.get("code", "")).strip().lower()
        label = str(payload.get("label", "")).strip()
        parent = str(payload.get("parent", "")).strip().lower()
        if not code or not label or not parent:
            raise HTTPException(status_code=400, detail="code, label, parent wajib")
        if len(code) < 2 or len(code) > 5:
            raise HTTPException(status_code=400, detail="kode harus 2-5 huruf")
        existing = supabase.table("kategori_master").select("code").eq("code", code).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail=f"kode {code} sudah ada")
        result = supabase.table("kategori_master").insert({
            "code": code,
            "label": label,
            "type": "sub",
            "parent": parent,
            "is_active": True
        }).execute()
        return {"success": True, "data": result.data[0] if result.data else {}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kategori/utama")
async def create_utama_kategori(payload: dict):
    try:
        code = str(payload.get("code", "")).strip().lower()
        label = str(payload.get("label", "")).strip()
        if not code or not label:
            raise HTTPException(status_code=400, detail="code, label wajib")
        if len(code) < 2 or len(code) > 5:
            raise HTTPException(status_code=400, detail="kode harus 2-5 huruf")
        existing = supabase.table("kategori_master").select("code").eq("code", code).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail=f"kode {code} sudah ada")
        result = supabase.table("kategori_master").insert({
            "code": code,
            "label": label,
            "type": "utama",
            "parent": None,
            "is_active": True
        }).execute()
        return {"success": True, "data": result.data[0] if result.data else {}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
