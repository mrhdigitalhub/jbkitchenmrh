# ================= OPSI C - TAMBAH KE app/main.py =================
# Paste di bawah endpoint @app.get("/api/kategori/list")
# Pastikan import ini sudah ada di atas file: from fastapi import HTTPException

@app.post("/api/kategori/sub")
async def create_sub_kategori(payload: dict):
    """Opsi C: Tambah Sub Kategori Baru - INSERT kategori_master type='sub'"""
    try:
        code = str(payload.get('code','')).strip().lower()
        label = str(payload.get('label','')).strip()
        parent = str(payload.get('parent','')).strip().lower()
        if not code or not label or not parent:
            raise HTTPException(status_code=400, detail="code, label, parent wajib diisi")
        if len(code) < 2 or len(code) > 5:
            raise HTTPException(status_code=400, detail="kode harus 2-5 huruf")
        # cek duplikat
        existing = supabase.table('kategori_master').select("code").eq("code", code).execute()
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail=f"kode {code} sudah ada")
        result = supabase.table('kategori_master').insert({
            "code": code,
            "label": label,
            "type": "sub",
            "parent": parent,
            "is_active": True
        }).execute()
        return {"success": True, "data": result.data[0] if result.data else {}, "message": f"Sub {code} berhasil ditambah ke {parent}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kategori/utama")
async def create_utama_kategori(payload: dict):
    """Opsi C: Tambah Kategori Utama Baru - INSERT kategori_master type='utama'"""
    try:
        code = str(payload.get('code','')).strip().lower()
        label = str(payload.get('label','')).strip()
        if not code or not label:
            raise HTTPException(status_code=400, detail="code, label wajib diisi")
        if len(code) < 2 or len(code) > 5:
            raise HTTPException(status_code=400, detail="kode harus 2-5 huruf")
        existing = supabase.table('kategori_master').select("code").eq("code", code).execute()
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail=f"kode {code} sudah ada")
        result = supabase.table('kategori_master').insert({
            "code": code,
            "label": label,
            "type": "utama",
            "parent": None,
            "is_active": True
        }).execute()
        return {"success": True, "data": result.data[0] if result.data else {}, "message": f"Kategori utama {code} berhasil ditambah"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ================= END OPSI C =================
