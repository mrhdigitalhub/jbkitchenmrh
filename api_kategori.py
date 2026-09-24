from fastapi import APIRouter, HTTPException
import os
from supabase import create_client, Client

router = APIRouter()

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(500, "SUPABASE_URL/KEY belum set")
    return create_client(url, key)

@router.get("/list")
def list_kategori():
    sb = get_supabase()
    try:
        utama = sb.table("kategori_utama").select("*").order("code").execute().data or []
        sub = sb.table("kategori_sub").select("*").order("code").execute().data or []
        return {"utama": utama, "sub": sub}
    except Exception as e:
        # fallback jika table belum ada
        raise HTTPException(500, f"Gagal load kategori: {str(e)}")

@router.post("/utama/save")
def save_utama(payload: dict):
    sb = get_supabase()
    code = (payload.get("code") or "").lower().strip()
    label = (payload.get("label") or "").strip()
    if not code or len(code) != 3 or not label:
        raise HTTPException(400, "code 3 huruf & label wajib")
    try:
        # upsert
        sb.table("kategori_utama").upsert({"code": code, "label": label, "type": "utama"}, on_conflict="code").execute()
        return {"ok": True, "code": code}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/sub/save")
def save_sub(payload: dict):
    sb = get_supabase()
    code = (payload.get("code") or "").lower().strip()
    label = (payload.get("label") or "").strip()
    parent = (payload.get("parent_code") or payload.get("parent") or "").lower().strip()
    if not code or len(code) != 3 or not label or not parent:
        raise HTTPException(400, "code, label, parent_code wajib")
    try:
        # cek parent ada
        p = sb.table("kategori_utama").select("code").eq("code", parent).execute().data
        if not p:
            raise HTTPException(400, f"Parent kategori utama '{parent}' tidak ditemukan")
        sb.table("kategori_sub").upsert({"code": code, "label": label, "parent_code": parent, "parent": parent}, on_conflict="code").execute()
        return {"ok": True, "code": code}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.delete("/utama/{code}")
def delete_utama(code: str):
    sb = get_supabase()
    code = code.lower().strip()
    try:
        # 1. cek apakah masih ada sub kategori yang pakai parent ini
        subs = sb.table("kategori_sub").select("code").eq("parent_code", code).execute().data or []
        # fallback cek field lama 'parent'
        if not subs:
            subs = sb.table("kategori_sub").select("code").eq("parent", code).execute().data or []
        if subs:
            raise HTTPException(400, f"Tidak bisa hapus '{code}' karena masih ada {len(subs)} sub kategori yang pakai. Hapus sub-nya dulu.")

        # 2. cek apakah masih ada bahan yang pakai kategori_utama ini
        bahan = sb.table("bahan").select("id").eq("kategori_utama", code).limit(1).execute().data or []
        if bahan:
            raise HTTPException(400, f"Tidak bisa hapus '{code}' karena masih dipakai oleh bahan di inventory. Pindahkan dulu bahannya ke kategori lain.")

        sb.table("kategori_utama").delete().eq("code", code).execute()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        # jangan jadi 500 misterius
        raise HTTPException(400, f"Gagal hapus utama {code}: {str(e)}")

@router.delete("/sub/{code}")
def delete_sub(code: str):
    sb = get_supabase()
    code = code.lower().strip()
    try:
        # cek apakah masih ada bahan yang pakai kode_kategori ini
        bahan = sb.table("bahan").select("id, kode_bahan").eq("kode_kategori", code).limit(5).execute().data or []
        if bahan:
            contoh = ", ".join([b.get("kode_bahan","") for b in bahan[:3]])
            raise HTTPException(400, f"Tidak bisa hapus sub '{code}' karena masih dipakai {len(bahan)}+ bahan. Contoh: {contoh}. Pindahkan dulu bahannya.")

        sb.table("kategori_sub").delete().eq("code", code).execute()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Gagal hapus sub {code}: {str(e)}")
