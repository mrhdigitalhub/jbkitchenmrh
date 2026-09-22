from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os, re, uuid, io
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
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
    print(f"Supabase init fail: {e}")

app = FastAPI(title="JB KITCHEN MRH - Clean 950Ln")
templates = Jinja2Templates(directory="app/templates")
if (Path(__file__).parent / "static").exists():
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# === KATEGORI DEFAULT - FOTO CROSS CHECK ===
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

def get_kategori_data():
    if supabase:
        try:
            res = supabase.table("kategori_master").select("*").order("code").execute()
            data = res.data or []
            if data:
                utama = [d for d in data if d.get("type")=="utama" and d.get("is_active",True)]
                sub = [d for d in data if d.get("type")=="sub" and d.get("is_active",True)]
                if utama or sub:
                    return utama, sub
        except: pass
    return DEFAULT_KAT_UTAMA, DEFAULT_SUB_KATEGORI

# === HPP CONFIG - CEK SYNC DENGAN DASHBOARD_ADMIN ===
OH_PERCENT = 0.10
DELIVERY_PERCENT = 0.05
MANPOWER_RATES = {"kepala_produksi":2000,"juru_masak":1500,"pegawai":1000}

def get_pengaturan_biaya():
    oh, delivery, manpower = OH_PERCENT, DELIVERY_PERCENT, MANPOWER_RATES.copy()
    if supabase:
        try:
            res = supabase.table("pengaturan_biaya").select("*").limit(1).execute()
            if res.data:
                row=res.data[0]
                oh=float(row.get("oh_percent",10) or 10)/100
                delivery=float(row.get("delivery_percent",5) or 5)/100
                manpower["kepala_produksi"]=float(row.get("rate_kepala",2000))
                manpower["juru_masak"]=float(row.get("rate_koki",1500))
                manpower["pegawai"]=float(row.get("rate_pegawai",1000))
        except: pass
    return oh, delivery, manpower

def hitung_hpp_final(hpp_bahan_total, porsi=1):
    oh, delivery, manpower = get_pengaturan_biaya()
    total_mp = sum(manpower.values())
    hpp_per_porsi = hpp_bahan_total / max(porsi,1) if porsi else hpp_bahan_total
    return {
        "hpp_bahan_total":hpp_bahan_total,
        "hpp_bahan_per_porsi":hpp_per_porsi,
        "oh_percent":oh*100,"oh_cost":hpp_per_porsi*oh,
        "delivery_percent":delivery*100,"delivery_cost":hpp_per_porsi*delivery,
        "manpower":manpower,"manpower_per_porsi":total_mp,
        "manpower_detail":{"kepala_produksi":manpower["kepala_produksi"],"juru_masak":manpower["juru_masak"],"pegawai":manpower["pegawai"]},
        "hpp_final_per_porsi":hpp_per_porsi + hpp_per_porsi*oh + hpp_per_porsi*delivery + total_mp,
        "hpp_final_total":(hpp_per_porsi + hpp_per_porsi*oh + hpp_per_porsi*delivery + total_mp)*max(porsi,1)
    }

# === KONVERSI SATUAN - UNIFIED 5 SATUAN FIX - SYNC DENGAN INVENTORY_STOCK ===
def konversi_ke_default(bahan: dict, qty_input: float, satuan_input: str):
    sd = (bahan.get("satuan_default") or "Kg").lower()
    si = (satuan_input or sd).lower()
    kj = bahan.get("konversi_json") or {}
    if isinstance(kj,str):
        try:
            import json; kj=json.loads(kj)
        except: kj={}
    faktor=1.0
    if si==sd: faktor=1.0
    else:
        # global fallback
        if si in ["gram","gr","g"] and sd=="kg": faktor=0.001
        if si in ["kg","kilo"] and sd in ["gram","gr"]: faktor=1000
        if si=="pcs" and sd=="kg":
            # per bahan
            nama=(bahan.get("nama_bahan") or "").lower()
            if "telur" in nama: faktor=0.06
            elif "bawang merah" in nama: faktor=0.02
            elif "bawang putih" in nama: faktor=0.01
            elif "tahu" in nama: faktor=0.3
            elif "tempe" in nama: faktor=0.5
            else: faktor=0.1
        # custom dari konversi_json: ex {"pcs_to_kg":0.06}
        key=f"{si}_to_{sd}"
        if key in kj: faktor=float(kj[key])
    return qty_input*faktor, faktor, ""

def hitung_total_hpp(menu_id: str):
    """SINGLE SOURCE OF TRUTH untuk HPP - dipakai add_resep, add_paket, delete_resep - CEK SYNC"""
    if not supabase: return 0,10
    porsi=10
    try:
        mr=supabase.table("menu_master").select("porsi,tipe_menu").eq("id",menu_id).single().execute()
        if mr.data:
            porsi=float(mr.data.get("porsi",10) or 10)
            if porsi==0:
                porsi=10
            if mr.data.get("tipe_menu")=="resep_masakan" and porsi<2:
                porsi=10
    except: porsi=10
    try:
        res=supabase.table("resep_bom").select("*, bahan_inventory(harga_per_satuan,satuan_default,nama_bahan,konversi_json), menu_master!resep_bom_paket_menu_id_fkey(hpp)").eq("menu_id",menu_id).execute()
    except:
        res=supabase.table("resep_bom").select("*, bahan_inventory(harga_per_satuan,satuan_default,nama_bahan), menu_master!resep_bom_paket_menu_id_fkey(hpp)").eq("menu_id",menu_id).execute()
    total=0
    for r in res.data or []:
        qty=float(r.get("qty_need",0) or 0)
        si=r.get("satuan_input") or r.get("satuan") or "Kg"
        # FIX: bahan_id prioritas (buah, air, box, bahan resep)
        if r.get("bahan_id"):
            bahan=r.get("bahan_inventory") or {}
            harga=float(bahan.get("harga_per_satuan",0) or 0)
            qty_conv,_,_=konversi_ke_default(bahan,qty,si)
            total+=qty_conv*porsi*harga
        elif r.get("paket_menu_id"):
            hpp_p=float((r.get("menu_master") or {}).get("hpp",0) or 0)
            total+=qty*porsi*hpp_p
    return total, porsi

# === KAMUS SUPABASE - BUKAN LOCALSTORAGE - CEK SYNC DENGAN MASTER_MENU ===
KAMUS_DEFAULT = {
    'beras':{'qty':0.15,'satuan':'Kg','label':'Beras 0.15 Kg = 150gr'},
    'ayam':{'qty':0.17,'satuan':'Kg','label':'Ayam 0.17 Kg = 170gr'},
    'telur':{'qty':1,'satuan':'Pcs','label':'Telur 1 Pcs = 0.06 Kg'},
    'bawang merah':{'qty':0.015,'satuan':'Kg','label':'Bawang Merah 0.015 Kg'},
    'bawang putih':{'qty':0.01,'satuan':'Kg','label':'Bawang Putih 0.01 Kg'},
    'serai':{'qty':0.03,'satuan':'Ikat','label':'Serai 0.03 Ikat'},
    'tahu':{'qty':1,'satuan':'Pcs','label':'Tahu 1 Pcs'},
    'tempe':{'qty':1,'satuan':'Pcs','label':'Tempe 1 Pcs'},
}

def _ensure_kamus_row(nama_bahan, qty, satuan, satuan_default, konversi_json, label):
    if not supabase or not nama_bahan: return
    nama_low=nama_bahan.strip().lower()
    if not nama_low: return
    try:
        ex=supabase.table("kamus_bom").select("id").eq("nama_bahan",nama_low).limit(1).execute()
        if ex.data: return
    except: pass
    try:
        supabase.table("kamus_bom").insert({
            "nama_bahan":nama_low,"qty_standar":float(qty or 0.15),
            "satuan_standar":satuan or "Kg","satuan_default":satuan_default or satuan or "Kg",
            "konversi_json":konversi_json or {},"label":label or f"{nama_bahan} {qty} {satuan}"
        }).execute()
    except Exception as e:
        print(f"kamus insert skip: {e}")

# === AUTH & DASHBOARD ===
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...), role: str = Form(...)):
    resp=RedirectResponse(url=f"/dashboard/{role}", status_code=302)
    resp.set_cookie(key="role",value=role); resp.set_cookie(key="email",value=email)
    return resp

@app.get("/dashboard/{role}", response_class=HTMLResponse)
async def dashboard(request: Request, role: str):
    stats={"total_bahan":0,"aset_inventory":0,"stock_min":0,"total_menu":0,"avg_hpp":0,"order_aktif":0}
    bahan=[]; orders=[]; menus=[]
    if supabase:
        try:
            bres=supabase.table("bahan_inventory").select("*").order("kode_bahan").execute()
            bahan=bres.data or []
            stats["total_bahan"]=len(bahan)
            aset=sum([float(b.get("stock_qty",0) or 0)*float(b.get("harga_per_satuan",0) or 0) for b in bahan])
            stats["aset_inventory"]=aset
            stats["stock_min"]=len([b for b in bahan if float(b.get("stock_qty",0) or 0) <= float(b.get("stock_minimum",5) or 5)])
            mres=supabase.table("menu_master").select("*").execute()
            menus=mres.data or []
            stats["total_menu"]=len(menus)
            if menus: stats["avg_hpp"]=sum([float(m.get("hpp",0) or 0) for m in menus])/len(menus)
        except Exception as e:
            print(e)
    tmpl={"admin":"dashboard_admin.html","dapur":"dashboard_dapur.html","gudang":"dashboard_gudang.html","delivery":"dashboard_delivery.html"}.get(role,"dashboard_admin.html")
    bahan_min=sorted([b for b in bahan if float(b.get("stock_qty",0) or 0) <= float(b.get("stock_minimum",5) or 5)], key=lambda x: float(x.get("stock_qty",0) or 0))[:5]
    return templates.TemplateResponse(tmpl, {"request":request,"role":role,"stats":stats,"bahan":bahan_min or bahan[:5],"bahan_all":bahan,"orders":orders,"menus":menus})

@app.get("/dashboard/admin/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request):
    bahan=[]
    if supabase:
        try:
            res=supabase.table("bahan_inventory").select("*").order("kode_bahan").execute()
            bahan=res.data or []
        except: pass
    kat_utama, sub_kat = get_kategori_data()
    return templates.TemplateResponse("inventory_stock.html", {"request":request,"bahan":bahan,"total":len(bahan),"kat_utama":kat_utama,"sub_kat":sub_kat})

@app.get("/dashboard/admin/menu", response_class=HTMLResponse)
async def menu_page(request: Request):
    menus=[]; bahan=[]
    if supabase:
        try:
            mres=supabase.table("menu_master").select("*").order("kode_menu").execute()
            menus=mres.data or []
            for m in menus:
                try:
                    rres=supabase.table("resep_bom").select("id",count="exact").eq("menu_id",m["id"]).execute()
                    m["jumlah_bahan"]=rres.count or 0
                except: m["jumlah_bahan"]=0
            bres=supabase.table("bahan_inventory").select("*").order("nama_bahan").execute()
            bahan=bres.data or []
        except Exception as e:
            print("menu page error",e)
    return templates.TemplateResponse("master_menu.html", {"request":request,"menus":menus,"bahan":bahan,"total_bahan":len(bahan),"total_menu":len(menus),"avg_hpp":sum([float(m.get("hpp",0) or 0) for m in menus])/len(menus) if menus else 0,"linked_menu":len([m for m in menus if m.get("jumlah_bahan",0)>0])})

# === OPSI A: HALAMAN TERPISAH RESEP & PAKET - FOCUS ===
@app.get("/dashboard/admin/menu/resep/{menu_id}", response_class=HTMLResponse)
async def resep_bom_page(request: Request, menu_id: str):
    menu=None; bahan=[]
    if supabase:
        try:
            mres=supabase.table("menu_master").select("*").eq("id",menu_id).single().execute()
            menu=mres.data
            bres=supabase.table("bahan_inventory").select("*").order("nama_bahan").execute()
            bahan=bres.data or []
        except Exception as e:
            print("resep page error",e)
    if not menu:
        raise HTTPException(404,"Menu not found")
    return templates.TemplateResponse("resep_bom.html", {"request":request,"menu":menu,"bahan":bahan})

@app.get("/dashboard/admin/menu/paket/{menu_id}", response_class=HTMLResponse)
async def paket_bom_page(request: Request, menu_id: str):
    menu=None; bahan=[]; resep_list=[]
    if supabase:
        try:
            mres=supabase.table("menu_master").select("*").eq("id",menu_id).single().execute()
            menu=mres.data
            bres=supabase.table("bahan_inventory").select("*").order("nama_bahan").execute()
            bahan=bres.data or []
            rres=supabase.table("menu_master").select("*").eq("tipe_menu","resep_masakan").order("kode_menu").execute()
            resep_list=rres.data or []
        except Exception as e:
            print("paket page error",e)
    if not menu:
        raise HTTPException(404,"Menu not found")
    return templates.TemplateResponse("paket_bom.html", {"request":request,"menu":menu,"bahan":bahan,"resep_list":resep_list})

# === MASTER RESEP DAN PAKET - CLEAN 950 Ln - CEK SYNC ===
@app.post("/dashboard/admin/menu/save")
async def save_menu(request: Request):
    form=await request.form()
    def get_str(k,d=""): v=form.get(k,d); return v if v is not None else d
    def to_title(s):
        if not s: return s
        return ' '.join([w.capitalize() for w in s.strip().split()])
    def clean_kode_resep(kode,nama):
        # PERBAIKAN: Resep-NamaMenu-Urut & Paket-NamaMenu-Urut
        k=kode.strip()
        if k.lower().startswith('resep-') or k.lower().startswith('paket-'):
            k=re.sub(r'\s+','-',k.strip()); k=re.sub(r'-+','-',k); k=k.strip('-')
            # Capitalize tiap bagian
            parts=k.split('-')
            if len(parts)>=2:
                return parts[0].capitalize()+'-'+''.join([p.capitalize() for p in parts[1:-1]])+'-'+parts[-1] if parts[-1].isdigit() else parts[0].capitalize()+'-'.join([p.capitalize() for p in parts[1:]])
            return k
        k=re.sub(r'-?10P\b','',k,flags=re.IGNORECASE)
        k=re.sub(r'-?10\s*Porsi\b','',k,flags=re.IGNORECASE)
        k=re.sub(r'\s+','-',k.strip()); k=re.sub(r'-+','-',k); k=k.strip('-')
        if not k:
            cn=''.join([w.capitalize() for w in nama.strip().split() if w])
            k=f"Resep-{cn}-001"
        return k
    def clean_kode_paket(kode,nama,tipe):
        k=kode.strip()
        if k.lower().startswith('paket-') or k.lower().startswith('resep-'):
            k=re.sub(r'\s+','-',k.strip()); k=re.sub(r'-+','-',k); k=k.strip('-')
            return k
        cn=''.join([w.capitalize() for w in nama.strip().split() if w])
        prefix='Paket' if tipe=='paket_masakan' else 'Resep'
        return f"{prefix}-{cn}-001"
    id_val=get_str("id","")
    kode_raw=get_str("kode_menu","").strip()
    nama=to_title(get_str("nama_menu",""))
    nama_clean=re.sub(r'\b10P\b','',nama,flags=re.IGNORECASE)
    nama_clean=re.sub(r'\b\d+\s*Porsi\b','',nama_clean,flags=re.IGNORECASE)
    nama_clean=' '.join(nama_clean.split()).strip()
    if nama_clean: nama=to_title(nama_clean)
    kategori=get_str("kategori_menu","Nasi Box")
    tipe=get_str("tipe_menu","paket_masakan")
    if tipe=="resep_masakan":
        porsi=0.0; satuan="porsi"; kategori="Resep"; harga_jual=0; hpp=0
        deskripsi=get_str("deskripsi","") or f"Resep {nama} - 1 qty=1 porsi (fix 10)"
        kode=clean_kode_resep(kode_raw,nama)
    else:
        porsi=float(form.get("porsi",1) or 1); satuan=get_str("satuan","pax")
        harga_jual=float(form.get("harga_jual",0) or 0); hpp=float(form.get("hpp",0) or 0)
        deskripsi=get_str("deskripsi",""); kode=clean_kode_paket(kode_raw,nama,tipe)
    data={"kode_menu":kode,"nama_menu":nama,"kategori_menu":kategori,"tipe_menu":tipe,"porsi":porsi,"satuan":satuan,"harga_jual":harga_jual,"hpp":hpp,"deskripsi":deskripsi}
    if supabase:
        try:
            if id_val: supabase.table("menu_master").update(data).eq("id",id_val).execute()
            else: supabase.table("menu_master").insert(data).execute()
        except Exception as e:
            print("save menu error",e)
            try:
                fb={k:v for k,v in data.items() if k!="tipe_menu"}
                if id_val: supabase.table("menu_master").update(fb).eq("id",id_val).execute()
                else: supabase.table("menu_master").insert(fb).execute()
            except Exception as e2: print(e2)
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/dashboard/admin/menu", status_code=302)

@app.get("/api/menu/{menu_id}")
async def get_menu(menu_id: str):
    if not supabase: raise HTTPException(404,"No supabase")
    res=supabase.table("menu_master").select("*").eq("id",menu_id).single().execute()
    return res.data

# === RESEP BOM - SINGLE SOURCE, TANPA TAMBAH Ln ===
@app.get("/api/menu/{menu_id}/resep")
async def get_resep(menu_id: str):
    if not supabase: return {"items":[],"hpp_calc":None}
    try:
        porsi=10
        try:
            mr=supabase.table("menu_master").select("porsi").eq("id",menu_id).single().execute()
            porsi=float(mr.data.get("porsi",10) or 10) if mr.data else 10
        except: pass
        # porsi 0 untuk resep display, tapi hitung 10
        if porsi==0: porsi=10
        try:
            res=supabase.table("resep_bom").select("*, bahan_inventory(kode_bahan,nama_bahan,satuan_default,harga_per_satuan,harga_awal,kode_kategori,stock_qty,konversi_json), menu_master!resep_bom_paket_menu_id_fkey(kode_menu,nama_menu,hpp,satuan,porsi)").eq("menu_id",menu_id).execute()
        except:
            res=supabase.table("resep_bom").select("*, bahan_inventory(kode_bahan,nama_bahan,satuan_default,harga_per_satuan,harga_awal,kode_kategori,stock_qty), menu_master!resep_bom_paket_menu_id_fkey(kode_menu,nama_menu,hpp,satuan,porsi)").eq("menu_id",menu_id).execute()
        items=[]; hpp_total=0
        for r in res.data or []:
            qty=float(r.get("qty_need",0) or 0)
            si=r.get("satuan_input") or r.get("satuan") or "Kg"
            # FIX CEK SYNC: bahan_id prioritas utama, baru paket_menu_id
            # Jika bahan_id ada (buah, air, box, bahan resep) -> treat sebagai bahan_inventory
            # Jika paket_menu_id ada (resep untuk paket) -> treat sebagai paket resep
            if r.get("bahan_id"):
                bahan=r.get("bahan_inventory") or {}
                harga=float(bahan.get("harga_per_satuan",0) or bahan.get("harga_awal",0) or 0)
                qty_conv,faktor,_=konversi_ke_default(bahan,qty,si)
                total_qty=qty_conv*porsi; sub=total_qty*harga; hpp_total+=sub
                kode_sub=bahan.get("kode_kategori",""); kode_full=bahan.get("kode_bahan","")
                no=kode_full.split('-')[-1] if '-' in kode_full else ''
                kode_rapi=f"{kode_sub}-{no} → {bahan.get('nama_bahan','').title()} → Rp {harga:,.0f} → {bahan.get('satuan_default','Kg')}"
                warns=[]
                if harga==0: warns.append("HARGA 0! Update di Inventory")
                if float(bahan.get("stock_qty",0) or 0)==0: warns.append("STOCK 0!")
                if faktor!=1.0: warns.append(f"Konversi {si}→{bahan.get('satuan_default','Kg')} x{faktor}")
                # tipe asli untuk display: jika parent paket masakan -> paket_bahan, else resep
                tipe_display=r.get("tipe","resep")
                if tipe_display=="paket":
                    tipe_display="paket_bahan"
                items.append({"id":r["id"],"tipe":tipe_display,"bahan_id":r.get("bahan_id"),"kode_bahan":kode_rapi,"kode_bahan_raw":kode_full,"sub_kode":kode_sub,"no_urut":no,"nama_bahan":' '.join([w.capitalize() for w in str(bahan.get("nama_bahan","")).split()]),"satuan":bahan.get("satuan_default","Kg"),"satuan_input":si,"harga":harga,"qty_need":qty,"qty_converted":qty_conv,"faktor":faktor,"total_qty":total_qty,"subtotal":sub,"subtotal_per_porsi":qty_conv*harga,"stock_qty":float(bahan.get("stock_qty",0) or 0),"warning":" | ".join(warns),"is_harga_0":harga==0,"is_stock_0":float(bahan.get("stock_qty",0) or 0)==0})
            elif r.get("paket_menu_id"):
                paket=r.get("menu_master") or {}
                hpp_p=float(paket.get("hpp",0) or 0)
                # OPSI A: Qty paket resep selalu 1 batch per porsi paket, satuan batch (bukan Kg)
                # Koreksi data lama yang 15 Kg seperti screenshot -> jadi 1 batch
                qty_fixed = qty
                if qty_fixed > 10:  # data lama 15 Kg salah input -> koreksi Opsi A
                    qty_fixed = 1.0
                total_qty=qty_fixed*porsi; sub=total_qty*hpp_p; hpp_total+=sub
                items.append({"id":r["id"],"tipe":"paket","bahan_id":r.get("paket_menu_id"),"kode_bahan":paket.get("kode_menu",""),"nama_bahan":paket.get("nama_menu",""),"satuan":"batch","satuan_input":"batch","harga":hpp_p,"qty_need":qty_fixed,"qty_converted":qty_fixed,"total_qty":total_qty,"subtotal":sub,"subtotal_per_porsi":qty_fixed*hpp_p,"stock_qty":0,"warning":""})
            else:
                # fallback jika tidak ada bahan_id maupun paket_menu_id
                items.append({"id":r["id"],"tipe":"unknown","nama_bahan":"(data tidak valid)","qty_need":qty,"harga":0,"subtotal":0})
        return {"items":items,"hpp_calc":hitung_hpp_final(hpp_total,porsi),"porsi":porsi}
    except Exception as e:
        print("get resep error",e)
        return {"items":[],"hpp_calc":None}

@app.post("/api/menu/{menu_id}/resep/add")
async def add_resep(menu_id: str, request: Request):
    body=await request.json()
    bahan_id=body.get("bahan_id"); qty=float(body.get("qty_need",0) or 0)
    si=body.get("satuan_input") or body.get("satuan") or "Kg"; tipe=body.get("tipe","resep")
    if not supabase: raise HTTPException(500,"No supabase")
    if not bahan_id: raise HTTPException(400,"bahan_id required")
    try:
        supabase.table("resep_bom").select("id").limit(1).execute()
    except Exception as e:
        raise HTTPException(500,f"Tabel resep_bom belum ada: {e}")
    try:
        # FIX SYNC ANTI-DOUBLE: cek apakah bahan sudah ada di paket ini -> update qty, bukan insert double
        try:
            existing = supabase.table("resep_bom").select("id,qty_need").eq("menu_id",menu_id).eq("bahan_id",bahan_id).execute()
            if existing.data and len(existing.data)>0:
                # update qty jika sudah ada (prevent double Air Minum seperti screenshot)
                first = existing.data[0]
                old_qty = float(first.get("qty_need",0) or 0)
                # jika qty sama persis dan dalam 3 detik terakhir, anggap double-click -> skip insert
                # else akumulasi
                if abs(old_qty - qty) < 0.0001:
                    # duplicate detection -> return ok tanpa insert baru
                    total,porsi=hitung_total_hpp(menu_id)
                    calc=hitung_hpp_final(total,porsi)
                    return {"ok":True,"hpp_per_porsi":calc["hpp_final_per_porsi"],"total":total,"final":calc["hpp_final_per_porsi"],"dedup":True}
                # jika qty beda, update jadi qty baru (bukan tambah double)
                supabase.table("resep_bom").update({"qty_need":qty,"satuan_input":si,"tipe":tipe}).eq("id",first["id"]).execute()
                # hapus duplicate lain jika ada >1 baris untuk bahan yang sama
                if len(existing.data)>1:
                    for dup in existing.data[1:]:
                        try: supabase.table("resep_bom").delete().eq("id",dup["id"]).execute()
                        except: pass
                total,porsi=hitung_total_hpp(menu_id)
                calc=hitung_hpp_final(total,porsi)
                hpp_final=calc["hpp_final_per_porsi"]
                supabase.table("menu_master").update({"hpp":hpp_final}).eq("id",menu_id).execute()
                return {"ok":True,"hpp_per_porsi":hpp_final,"hpp_bahan":calc["hpp_bahan_per_porsi"],"total":total,"final":hpp_final,"dedup":False,"updated":True}
        except Exception as dedup_e:
            print(f"dedup check fail (continue insert): {dedup_e}")

        try:
            supabase.table("resep_bom").insert({"menu_id":menu_id,"bahan_id":bahan_id,"qty_need":qty,"satuan_input":si,"tipe":tipe}).execute()
        except Exception as e:
            msg=str(e)
            if "satuan_input" in msg or "PGRST204" in msg or "schema cache" in msg:
                try:
                    supabase.table("resep_bom").insert({"menu_id":menu_id,"bahan_id":bahan_id,"qty_need":qty,"satuan":si,"tipe":tipe}).execute()
                except:
                    supabase.table("resep_bom").insert({"menu_id":menu_id,"bahan_id":bahan_id,"qty_need":qty,"tipe":tipe}).execute()
            else:
                if "tipe" in msg:
                    supabase.table("resep_bom").insert({"menu_id":menu_id,"bahan_id":bahan_id,"qty_need":qty,"satuan_input":si}).execute()
                else: raise
        try:
            if bahan_id:
                try:
                    b_res=supabase.table("bahan_inventory").select("nama_bahan,satuan_default,konversi_json").eq("id",bahan_id).single().execute()
                except:
                    b_res=supabase.table("bahan_inventory").select("nama_bahan,satuan_default").eq("id",bahan_id).single().execute()
                if b_res.data:
                    _ensure_kamus_row(b_res.data.get("nama_bahan",""),qty,si,b_res.data.get("satuan_default") or "Kg",b_res.data.get("konversi_json") or {},f"{b_res.data.get('nama_bahan','')} {qty} {si} (auto)")
        except Exception as e:
            print(f"kamus auto fail: {e}")
        total,porsi=hitung_total_hpp(menu_id)
        calc=hitung_hpp_final(total,porsi)
        hpp_final=calc["hpp_final_per_porsi"]
        supabase.table("menu_master").update({"hpp":hpp_final}).eq("id",menu_id).execute()
    except HTTPException: raise
    except Exception as e:
        print("add resep error",e); raise HTTPException(500,f"Gagal tambah bahan: {e}")
    return {"ok":True,"hpp_per_porsi":hpp_final,"hpp_bahan":calc["hpp_bahan_per_porsi"],"total":total,"final":hpp_final}

@app.post("/api/menu/{menu_id}/resep/add-paket")
async def add_resep_paket(menu_id: str, request: Request):
    body=await request.json()
    paket_id=body.get("paket_menu_id")
    # OPSI A: Qty 1 batch = 1 porsi paket pakai 1 resep utuh, bukan Kg
    qty_input=float(body.get("qty_need",1) or 1)
    qty=1.0  # force Opsi A: selalu 1 batch per porsi paket
    if qty_input!=1:
        qty=qty_input  # jika user input 1 tetap 1, jika input lain tetap pakai tapi satuan batch
        if qty>10: # jika user salah input 15 seperti screenshot -> koreksi jadi 1
            qty=1.0
    if not supabase: raise HTTPException(500,"No supabase")
    if not paket_id: raise HTTPException(400,"paket_menu_id required")
    try:
        # ANTI DOUBLE paket resep
        try:
            existing = supabase.table("resep_bom").select("id").eq("menu_id",menu_id).eq("paket_menu_id",paket_id).execute()
            if existing.data and len(existing.data)>0:
                total,porsi=hitung_total_hpp(menu_id)
                calc=hitung_hpp_final(total,porsi)
                return {"ok":True,"hpp_per_porsi":calc["hpp_final_per_porsi"],"total":total,"final":calc["hpp_final_per_porsi"],"dedup":True}
        except: pass

        try:
            supabase.table("resep_bom").insert({"menu_id":menu_id,"paket_menu_id":paket_id,"qty_need":qty,"satuan_input":"batch","tipe":"paket"}).execute()
        except Exception as e:
            msg=str(e)
            if "satuan_input" in msg:
                supabase.table("resep_bom").insert({"menu_id":menu_id,"paket_menu_id":paket_id,"qty_need":qty,"satuan":"batch","tipe":"paket"}).execute()
            else:
                supabase.table("resep_bom").insert({"menu_id":menu_id,"paket_menu_id":paket_id,"qty_need":qty,"tipe":"paket"}).execute()
        total,porsi=hitung_total_hpp(menu_id)
        calc=hitung_hpp_final(total,porsi)
        hpp_final=calc["hpp_final_per_porsi"]
        supabase.table("menu_master").update({"hpp":hpp_final}).eq("id",menu_id).execute()
        return {"ok":True,"hpp_per_porsi":hpp_final,"total":total,"final":hpp_final}
    except Exception as e:
        print("add paket error",e); raise HTTPException(500,f"Gagal tambah paket: {e}")

@app.post("/api/menu/{menu_id}/porsi")
async def update_porsi(menu_id: str, request: Request):
    body=await request.json()
    porsi=float(body.get("porsi",1) or 1)
    if porsi<=0: porsi=1
    satuan=body.get("satuan","porsi")
    if not supabase: raise HTTPException(500,"No supabase")
    try:
        supabase.table("menu_master").update({"porsi":porsi,"satuan":satuan}).eq("id",menu_id).execute()
        total,_=hitung_total_hpp(menu_id)
        # hitung ulang dengan porsi baru
        calc=hitung_hpp_final(total,porsi)
        hpp_final=calc["hpp_final_per_porsi"]
        supabase.table("menu_master").update({"hpp":hpp_final}).eq("id",menu_id).execute()
        return {"ok":True,"porsi":porsi,"satuan":satuan,"hpp_final":hpp_final,"calc":calc}
    except Exception as e:
        print("update porsi error",e); raise HTTPException(500,str(e))

@app.delete("/api/resep/{resep_id}")
async def delete_resep(resep_id: str):
    if not supabase: raise HTTPException(500,"No supabase")
    try:
        cur=supabase.table("resep_bom").select("menu_id").eq("id",resep_id).single().execute()
        menu_id=cur.data.get("menu_id") if cur.data else None
        supabase.table("resep_bom").delete().eq("id",resep_id).execute()
        if menu_id:
            total,porsi=hitung_total_hpp(menu_id)
            calc=hitung_hpp_final(total,porsi)
            hpp_final=calc["hpp_final_per_porsi"]
            # jika sudah tidak ada bahan, hpp = 0
            if total==0:
                hpp_final=0
            supabase.table("menu_master").update({"hpp":hpp_final}).eq("id",menu_id).execute()
    except Exception as e:
        print("delete resep error",e)
    return {"deleted":True}

@app.delete("/api/menu/delete/{menu_id}")
async def delete_menu(menu_id: str):
    if not supabase: raise HTTPException(500,"No supabase")
    try:
        supabase.table("resep_bom").delete().eq("menu_id",menu_id).execute()
        supabase.table("menu_master").delete().eq("id",menu_id).execute()
        return {"deleted":True,"id":menu_id}
    except Exception as e:
        print("delete menu error",e); raise HTTPException(500,str(e))

# === KATEGORI & BAHAN + BAHAN LIST FIX LOADING LAMBAT ===
@app.get("/api/bahan/list")
async def bahan_list():
    if not supabase:
        return {"items":[],"count":0}
    try:
        # ambil hanya kolom yang dipakai BOM biar cepat, limit 500
        res=supabase.table("bahan_inventory").select("id,kode_bahan,nama_bahan,kode_kategori,kategori_utama,satuan_default,harga_per_satuan,stock_qty").order("nama_bahan").limit(500).execute()
        return {"items":res.data or [],"bahan":res.data or [],"count":len(res.data or [])}
    except Exception as e:
        print("bahan list error",e)
        return {"items":[],"count":0,"error":str(e)}

@app.get("/api/kategori/list")
async def kategori_list():
    utama,sub=get_kategori_data()
    return {"utama":utama,"sub":sub}

@app.post("/api/kategori/save")
async def kategori_save(request: Request):
    form=await request.form()
    code=form.get("code","").strip().lower()[:4]; label=form.get("label","").strip()
    type_=form.get("type","utama"); parent=form.get("parent","").strip().lower()
    if not code or not label: raise HTTPException(400,"code & label required")
    data={"code":code,"label":label,"type":type_,"parent":parent,"is_active":True}
    if supabase:
        try:
            ex=supabase.table("kategori_master").select("*").eq("code",code).eq("type",type_).execute()
            if ex.data: supabase.table("kategori_master").update(data).eq("code",code).eq("type",type_).execute()
            else: supabase.table("kategori_master").insert(data).execute()
        except: pass
    return {"saved":True,"data":data}

@app.delete("/api/kategori/{code}")
async def kategori_delete(code: str, type: str = "sub"):
    if supabase:
        try: supabase.table("kategori_master").update({"is_active":False}).eq("code",code).eq("type",type).execute()
        except: pass
    return {"deleted":True,"code":code}

@app.post("/dashboard/admin/inventory/save")
async def save_bahan(request: Request):
    form=await request.form()
    def get_str(k,d=""): v=form.get(k,d); return v if v is not None else d
    def get_float(k,default=0):
        v=form.get(k); 
        if v in (None,""," "): return default
        try: return float(v)
        except: return default
    id_val=get_str("id","")
    kode=get_str("kode_bahan","").strip(); nama=' '.join([w.capitalize() for w in get_str("nama_bahan","").strip().split()])
    kat_utama=get_str("kategori_utama","nbt").lower(); kode_kat=get_str("kode_kategori","buh").lower()
    satuan=get_str("satuan_default","Kg"); stock=get_float("stock_qty",0); stock_min=get_float("stock_minimum",5)
    harga=get_float("harga_per_satuan",0); supplier=get_str("supplier",""); merek=' '.join([w.capitalize() for w in get_str("merek","").split()])
    hall=get_str("hall_flag","Orgk"); orgk="Orgk" if hall=="Orgk" else ""
    # konversi_json dari form jika ada
    konversi_json={}
    try:
        kj_raw=get_str("konversi_json","")
        if kj_raw:
            import json; konversi_json=json.loads(kj_raw)
    except: pass
    data={"kode_bahan":kode,"nama_bahan":nama,"kategori_utama":kat_utama,"kode_kategori":kode_kat,"satuan_default":satuan,"stock_qty":stock,"stock_minimum":stock_min,"harga_per_satuan":harga,"supplier":supplier,"merek":merek,"hall_flag":hall,"orgk_flag":orgk,"konversi_json":konversi_json}
    if supabase:
        try:
            if id_val: supabase.table("bahan_inventory").update(data).eq("id",id_val).execute()
            else: supabase.table("bahan_inventory").insert(data).execute()
            _ensure_kamus_row(nama,0.15,satuan,satuan,konversi_json,f"{nama} 0.15 {satuan} (auto dari inventory)")
        except Exception as e:
            print("save bahan error",e)
            # fallback tanpa konversi_json jika kolom belum ada
            try:
                fb={k:v for k,v in data.items() if k!="konversi_json"}
                if id_val: supabase.table("bahan_inventory").update(fb).eq("id",id_val).execute()
                else: supabase.table("bahan_inventory").insert(fb).execute()
            except Exception as e2: print(e2)
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/dashboard/admin/inventory", status_code=302)

# === KAMUS SUPABASE ===
KAMUS_DEFAULT = KAMUS_DEFAULT
@app.get("/api/kamus/list")
async def kamus_list():
    kamus=KAMUS_DEFAULT.copy()
    if supabase:
        try:
            res=supabase.table("kamus_bom").select("*").execute()
            for row in res.data or []:
                nama=(row.get("nama_bahan") or "").lower()
                if nama:
                    kj=row.get("konversi_json") or {}
                    if isinstance(kj,str):
                        try:
                            import json; kj=json.loads(kj)
                        except: kj={}
                    kamus[nama]={"qty":float(row.get("qty_standar",0.15) or 0.15),"satuan":row.get("satuan_standar","Kg"),"satuan_default":row.get("satuan_default","Kg"),"konversi_json":kj,"label":row.get("label",f"{nama} {row.get('qty_standar',0.15)} {row.get('satuan_standar','Kg')}")}
        except Exception as e:
            print(f"kamus list error: {e}")
    return {"items":kamus,"source":"supabase+default"}

@app.post("/api/kamus/save")
async def kamus_save(request: Request):
    body=await request.json()
    nama=(body.get("nama_bahan") or "").lower().strip()
    qty=float(body.get("qty",0.15) or 0.15); satuan=body.get("satuan","Kg")
    satuan_default=body.get("satuan_default",satuan); kj=body.get("konversi_json",{}); label=body.get("label",f"{nama} {qty} {satuan}")
    if not nama: raise HTTPException(400,"nama_bahan required")
    if supabase:
        try:
            ex=supabase.table("kamus_bom").select("id").eq("nama_bahan",nama).limit(1).execute()
            data={"nama_bahan":nama,"qty_standar":qty,"satuan_standar":satuan,"satuan_default":satuan_default,"konversi_json":kj,"label":label,"updated_at":datetime.now().isoformat()}
            if ex.data: supabase.table("kamus_bom").update(data).eq("nama_bahan",nama).execute()
            else: supabase.table("kamus_bom").insert(data).execute()
            return {"saved":True,"source":"supabase"}
        except Exception as e:
            print(f"kamus save error: {e}"); raise HTTPException(500,str(e))
    return {"saved":True,"source":"memory"}

@app.delete("/api/kamus/delete/{nama_bahan}")
async def kamus_delete(nama_bahan: str):
    if not supabase: raise HTTPException(500,"No supabase")
    nama_low=nama_bahan.lower().strip()
    try:
        supabase.table("kamus_bom").delete().eq("nama_bahan",nama_low).execute()
        return {"deleted":True,"nama":nama_low}
    except Exception as e:
        print(f"kamus delete error: {e}"); raise HTTPException(500,str(e))

# === LAINNYA ===
@app.get("/api/stats/realtime")
async def stats_realtime():
    if not supabase: return {"total_bahan":0,"aset_inventory":0,"stock_min":0,"total_menu":0}
    try:
        bahan_res=supabase.table("bahan_inventory").select("kode_bahan,nama_bahan,stock_qty,harga_per_satuan,stock_minimum,satuan_default").order("stock_qty").limit(5).execute()
        bahan_all=supabase.table("bahan_inventory").select("stock_qty,harga_per_satuan,stock_minimum").execute()
        all_data=bahan_all.data or []
        total=len(all_data); aset=sum([float(b.get("stock_qty",0) or 0)*float(b.get("harga_per_satuan",0) or 0) for b in all_data])
        stock_min=len([b for b in all_data if float(b.get("stock_qty",0) or 0) <= float(b.get("stock_minimum",5) or 5)])
        total_menu=0
        try:
            menu_res=supabase.table("menu_master").select("id",count="exact").execute()
            total_menu=menu_res.count or len(menu_res.data or [])
        except: pass
        min_items=[]
        for b in (bahan_res.data or []):
            if float(b.get("stock_qty",0) or 0) <= float(b.get("stock_minimum",5) or 5):
                min_items.append(b)
        if len(min_items)<5: min_items=bahan_res.data or []
        for b in min_items:
            if b.get("nama_bahan"): b["nama_bahan"]=' '.join([w.capitalize() for w in str(b["nama_bahan"]).split()])
        return {"total_bahan":total,"aset_inventory":aset,"stock_min":stock_min,"total_menu":total_menu,"items":min_items[:5],"timestamp":datetime.now().isoformat()}
    except Exception as e:
        return {"error":str(e)}

@app.get("/health")
async def health(): return {"status":"ok","app":"JB KITCHEN MRH Clean 950Ln","supabase":bool(supabase)}
