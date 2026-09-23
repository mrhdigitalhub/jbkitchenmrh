
# === OPSI C BACKEND - TAMBAHKAN KE app/main.py ===
# Letakkan setelah endpoint /api/kategori/list

@app.post("/api/kategori/sub")
async def create_sub_kategori(payload: dict):
    """
    Opsi C: Tambah Sub Kategori Baru - INSERT DB kategori_master type='sub'
    Body: { code: 'sck', label: 'Snack Pelengkap', parent: 'plk' }
    """
    try:
        code = payload.get('code','').strip().lower()
        label = payload.get('label','').strip()
        parent = payload.get('parent','').strip().lower()
        if not code or not label or not parent:
            raise HTTPException(status_code=400, detail="code, label, parent wajib")
        # Validasi parent harus kategori utama yang ada
        supabase.table('kategori_master').insert({
            "code": code,
            "label": label,
            "type": "sub",
            "parent": parent,
            "is_active": True
        }).execute()
        return {"success": True, "code": code, "label": label, "parent": parent, "type": "sub"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kategori/utama")
async def create_utama_kategori(payload: dict):
    """
    Opsi C: Tambah Kategori Utama Baru - INSERT DB kategori_master type='utama'
    Body: { code: 'bks', label: 'Bahan Kemasan Snack' }
    """
    try:
        code = payload.get('code','').strip().lower()
        label = payload.get('label','').strip()
        if not code or not label:
            raise HTTPException(status_code=400, detail="code, label wajib")
        supabase.table('kategori_master').insert({
            "code": code,
            "label": label,
            "type": "utama",
            "parent": None,
            "is_active": True
        }).execute()
        return {"success": True, "code": code, "label": label, "type": "utama"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
