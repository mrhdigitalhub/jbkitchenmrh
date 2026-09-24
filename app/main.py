"""
JB KITCHEN - app/main.py FINAL SYNC 2.0
- Sinkron dengan dashboard_admin.html Bapak (polling 8 detik + 15 detik)
- Fix sidebar: /dashboard/admin, /dashboard/admin/inventory, /dashboard/admin/menu
- Fix stats: total_bahan, aset_inventory, stock_min, total_menu, order_aktif, order_closed
- Supabase Realtime 6 tabel aktif (sudah di-enable via SQL tadi)
- 1 Sumber Kebenaran
"""
import os, json, uuid
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"[WARN] Supabase init: {e}")

app = FastAPI(title="JB KITCHEN MRH")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "app" else BASE_DIR

# Templates - Vercel safe - cari semua lokasi
templates = None
for cand in [BASE_DIR / "templates", PROJECT_ROOT / "app" / "templates", PROJECT_ROOT / "templates", Path.cwd() / "app" / "templates", Path.cwd() / "templates"]:
    if cand.exists():
        templates = Jinja2Templates(directory=str(cand))
        print(f"[OK] Templates: {cand}")
        break

# Static
for cand in [BASE_DIR / "static", PROJECT_ROOT / "app" / "static"]:
    if cand.exists():
        app.mount("/static", StaticFiles(directory=str(cand)), name="static")
        break

def safe_float(v, d=0.0):
    try:
        if v is None or v == "": return d
        return float(v)
    except: return d

def format_nama(s):
    return ' '.join([w.capitalize() for w in str(s).split()]) if s else ""

DEFAULT_UTAMA = [
    {"code":"cuc","label":"Cuci / Chemical","type":"utama"},
    {"code":"dgi","label":"Bahan Hewani / Daging","type":"utama"},
    {"code":"nbt","label":"Bahan Nabati","type":"utama"},
    {"code":"pck","label":"Packaging Kertas / Karton","type":"utama"},
    {"code":"pik","label":"Plastik & Kemasan","type":"utama"},
    {"code":"prs","label":"Perasa / Saus","type":"utama"},
    {"code":"raw","label":"Bahan Pendukung Utama","type":"utama"},
]
DEFAULT_SUB = [
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
    if not supabase:
        return DEFAULT_UTAMA, DEFAULT_SUB
    try:
        res = supabase.table("kategori_bahan").select("*").order("code").execute()
        data = res.data or []
        if not data:
            # fallback ke kategori_master kalau ada
            try:
                res2 = supabase.table("kategori_master").select("*").order("code").execute()
                data = res2.data or []
            except:
                pass
        if not data: return DEFAULT_UTAMA, DEFAULT_SUB
        utama = [d for d in data if d.get("type")=="utama"]
        sub = [d for d in data if d.get("type")=="sub"]
        return (utama or DEFAULT_UTAMA), (sub or DEFAULT_SUB)
    except:
        return DEFAULT_UTAMA, DEFAULT_SUB

# === STATS REALTIME - SINKRON DENGAN dashboard_admin.html ===
async def get_stats_full():
    total_bahan = 0
    aset_inventory = 0.0
    stock_min = 0
    total_menu = 0
    order_aktif = 0
    order_closed = 0
    items_min = []
    all_items = []
    menus = []

    if supabase:
        try:
            res = supabase.table("bahan_inventory").select("id,kode_bahan,nama_bahan,stock_qty,satuan_default,harga_per_satuan,stock_minimum").order("kode_bahan").execute()
            all_items = res.data or []
            total_bahan = len(all_items)
            aset_inventory = sum([safe_float(b.get("stock_qty"))*safe_float(b.get("harga_per_satuan")) for b in all_items])
            # hitung stock minimum (stock_qty <= stock_minimum atau <=5 default)
            for b in all_items:
                min_val = safe_float(b.get("stock_minimum"), 5)
                if safe_float(b.get("stock_qty")) <= min_val:
                    stock_min += 1
                    if len(items_min) < 5:
                        items_min.append(b)
            if not items_min:
                items_min = all_items[:5]
        except Exception as e:
            print(f"[stats bahan] {e}")
        try:
            res_menu = supabase.table("menu_master").select("id,nama_menu,hpp").order("nama_menu").execute()
            menus = res_menu.data or []
            total_menu = len(menus)
        except:
            try:
                res_menu = supabase.table("menu_master").select("*").execute()
                menus = res_menu.data or []
                total_menu = len(menus)
            except Exception as e:
                print(f"[stats menu] {e}")
        try:
            res_orders = supabase.table("orders").select("id,status").execute()
            orders = res_orders.data or []
            for o in orders:
                st = str(o.get("status","")).lower()
                if st in ["aktif","proses","baru","pending","open"]:
                    order_aktif += 1
                elif st in ["closed","selesai","done","complete"]:
                    order_closed += 1
                else:
                    # kalau tidak ada status jelas, anggap aktif kalau 0
                    if order_aktif==0 and order_closed==0:
                        order_aktif = len(orders)
        except Exception as e:
            print(f"[stats orders] {e}")

    return {
        "total_bahan": total_bahan,
        "aset_inventory": aset_inventory,
        "stock_min": stock_min,
        "total_menu": total_menu,
        "order_aktif": order_aktif,
        "order_closed": order_closed,
        "items": items_min,
        "all_items": all_items,
        "menus": menus
    }

@app.get("/health")
async def health():
    return {"status":"ok","supabase":bool(supabase),"templates":str(templates) if templates else "none"}

@app.get("/api/stats/realtime")
async def stats_realtime():
    try:
        s = await get_stats_full()
        return {
            "total_bahan": s["total_bahan"],
            "aset_inventory": s["aset_inventory"],
            "stock_min": s["stock_min"],
            "total_menu": s["total_menu"],
            "order_aktif": s["order_aktif"],
            "order_closed": s["order_closed"],
            "items": s["items"],
            "menus": s["menus"][:5]
        }
    except Exception as e:
        return {"total_bahan":0,"aset_inventory":0,"stock_min":0,"total_menu":0,"order_aktif":0,"order_closed":0,"items":[],"menus":[],"error":str(e)}

@app.get("/api/bahan/minimum")
async def bahan_minimum():
    try:
        s = await get_stats_full()
        return {"items": s["items"], "count": s["stock_min"]}
    except Exception as e:
        return {"items": [], "count": 0, "error": str(e)}


@app.post("/api/kategori/utama/save")
async def save_kategori_utama(request: Request):
    if not supabase: raise HTTPException(500,"No supabase")
    data = await request.json()
    code = str(data.get("code","")).lower().strip()
    label = str(data.get("label","")).strip()
    if len(code)!=3: raise HTTPException(400,"Code harus 3 huruf")
    if not label: raise HTTPException(400,"Label wajib")
    saved=[]
    last_err=""
    try:
        chk = supabase.table("kategori_master").select("code").eq("code", code).execute()
        if chk.data:
            supabase.table("kategori_master").update({"label": label, "type": "utama", "is_active": True}).eq("code", code).execute()
        else:
            supabase.table("kategori_master").insert({"id": str(uuid.uuid4()), "code": code, "label": label, "type": "utama", "is_active": True}).execute()
        saved.append("kategori_master")
    except Exception as e:
        last_err=str(e)
    for tbl in ["kategori_bahan","kategori"]:
        try:
            chk = supabase.table(tbl).select("kode_kategori").eq("kode_kategori", code).execute()
            if chk.data:
                supabase.table(tbl).update({"nama_kategori": label}).eq("kode_kategori", code).execute()
            else:
                supabase.table(tbl).insert({"kode_kategori": code, "nama_kategori": label}).execute()
            saved.append(tbl)
        except Exception as e:
            last_err=str(e)
            continue
    if not saved:
        raise HTTPException(500, f"Gagal save utama {code}: {last_err}")
    return {"ok": True, "tables": saved, "code": code}

@app.post("/api/kategori/sub/save")
async def save_kategori_sub(request: Request):
    if not supabase: raise HTTPException(500,"No supabase")
    data = await request.json()
    code = str(data.get("code","")).lower().strip()
    label = str(data.get("label","")).strip()
    parent = str(data.get("parent","") or data.get("parent_code","")).lower().strip()
    if len(code)!=3 or len(parent)!=3:
        raise HTTPException(400,f"Code dan parent harus 3 huruf, got code={code} parent={parent}")
    if not label:
        raise HTTPException(400,"Label wajib")
    saved=[]
    last_err=""
    try:
        chk = supabase.table("kategori_master").select("code").eq("code", code).execute()
        if chk.data:
            supabase.table("kategori_master").update({"label": label, "type": "sub", "parent": parent, "is_active": True}).eq("code", code).execute()
        else:
            supabase.table("kategori_master").insert({"id": str(uuid.uuid4()), "code": code, "label": label, "type": "sub", "parent": parent, "is_active": True}).execute()
        saved.append("kategori_master")
    except Exception as e:
        last_err=str(e)
    if not saved:
        raise HTTPException(500, f"Gagal save sub {code}: {last_err}")
    return {"ok": True, "tables": saved, "code": code, "parent": parent}

@app.delete("/api/kategori/utama/{code}")
@app.delete("/api/kategori/{code}")
async def delete_kategori(code: str):
    if not supabase: raise HTTPException(500,"No supabase")
    code = code.lower().strip()
    try:
        supabase.table("kategori_master").delete().eq("code", code).execute()
    except Exception: pass
    try:
        supabase.table("kategori_bahan").delete().eq("kode_kategori", code).execute()
    except Exception: pass
    try:
        supabase.table("kategori").delete().eq("kode_kategori", code).execute()
    except Exception: pass
    return {"ok": True, "deleted": code}

@app.delete("/api/kategori/sub/{code}")
async def delete_kategori_sub(code: str):
    if not supabase: raise HTTPException(500,"No supabase")
    code = code.lower().strip()
    try:
        supabase.table("kategori_master").delete().eq("code", code).execute()
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "deleted": code}


@app.get("/api/kategori/list")
async def kategori_list():
    utama, sub = get_kategori_data()
    return {"utama":utama,"sub":sub}

# === ROOT ===
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse("/dashboard/admin")

# === DASHBOARD ADMIN - SYNC DENGAN FILE BAPAK ===
@app.get("/dashboard/admin", response_class=HTMLResponse)
async def dashboard_admin(request: Request):
    if templates is None:
        return RedirectResponse("/dashboard/admin/inventory")
    try:
        stats = await get_stats_full()
        context = {
            "request": request,
            "role": "ADMIN",
            "stats": stats,
            "bahan": stats["items"],
            "menus": stats["menus"],
            "total_bahan": stats["total_bahan"]
        }
        # coba render dashboard_admin.html yang Bapak kirim
        try:
            return templates.TemplateResponse(request, "dashboard_admin.html", context)
        except:
            return templates.TemplateResponse("dashboard_admin.html", context)
    except Exception as e:
        print(f"[ADMIN ERROR] {e}")
        import traceback; traceback.print_exc()
        return RedirectResponse("/dashboard/admin/inventory")

# === INVENTORY - 49 BAHAN ===
@app.get("/dashboard/admin/inventory", response_class=HTMLResponse)
@app.get("/inventory_stock", response_class=HTMLResponse)
async def inventory_stock(request: Request):
    bahan = []
    if supabase:
        try:
            res = supabase.table("bahan_inventory").select("*").order("kode_bahan").execute()
            bahan = res.data or []
        except Exception as e:
            print(f"[inventory] {e}")
    if templates is None:
        return HTMLResponse(f"<h3>Inventory {len(bahan)} bahan - templates not found</h3>")
    try:
        try:
            return templates.TemplateResponse(request, "inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan)})
        except:
            return templates.TemplateResponse("inventory_stock.html", {"request": request, "bahan": bahan, "total": len(bahan)})
    except Exception as e:
        return HTMLResponse(f"<h1>Inventory fallback {len(bahan)} bahan</h1><p>Error: {e}</p>")

@app.post("/dashboard/admin/inventory/save")
async def inventory_save(request: Request):
    if not supabase: raise HTTPException(500,"Supabase not configured")
    form = await request.form()
    data = dict(form)
    stock_qty = safe_float(data.get("stock_awal"),0) + safe_float(data.get("tambah"),0) - safe_float(data.get("terpakai"),0)
    if stock_qty == 0: stock_qty = safe_float(data.get("stock_qty"))
    harga = safe_float(data.get("harga_baru"),0) or safe_float(data.get("harga_awal"),0) or safe_float(data.get("harga_per_satuan"),0)
    payload = {
        "kode_bahan": data.get("kode_bahan"),
        "nama_bahan": (data.get("nama_bahan") or "").lower(),
        "kategori_utama": data.get("kategori_utama"),
        "kode_kategori": data.get("kode_kategori"),
        "satuan_default": data.get("satuan_default") or "Kg",
        "stock_qty": stock_qty,
        "harga_per_satuan": harga,
        "id_halal": data.get("id_halal"),
        "updated_at": datetime.now().isoformat()
    }
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

# === MASTER MENU - FIX SIDEBAR NO 3 ===
@app.get("/dashboard/admin/menu", response_class=HTMLResponse)
@app.get("/master-menu", response_class=HTMLResponse)
@app.get("/master_menu", response_class=HTMLResponse)
@app.get("/dashboard/admin/master-menu", response_class=HTMLResponse)
async def master_menu(request: Request):
    menus = []
    if supabase:
        try:
            res = supabase.table("menu_master").select("*").order("nama_menu").execute()
            menus = res.data or []
        except Exception as e:
            print(f"[menu] {e}")
    if templates is None:
        return HTMLResponse(f"<h3>Master Menu {len(menus)} - templates not found</h3><a href='/dashboard/admin'>Back</a>")
    # coba semua kemungkinan nama template
    for tmpl_name in ["master_menu.html", "master-menu.html", "menu_master.html", "inventory_stock.html"]:
        try:
            tmpl_path = Path(templates.env.loader.searchpath[0]) / tmpl_name
            if tmpl_path.exists():
                try:
                    return templates.TemplateResponse(request, tmpl_name, {"request": request, "menu": menus, "menus": menus, "total": len(menus)})
                except:
                    return templates.TemplateResponse(tmpl_name, {"request": request, "menu": menus, "menus": menus, "total": len(menus)})
        except:
            continue
    # fallback kalau tidak ada template menu, tampilkan inventory dengan info
    return RedirectResponse("/dashboard/admin/inventory")

# === TAMBAHAN ROUTE UNTUK SIDEBAR LAIN (ANTI 404) ===
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_redirect(request: Request):
    return RedirectResponse("/dashboard/admin")

@app.get("/dashboard/delivery", response_class=HTMLResponse)
@app.get("/dashboard/produksi", response_class=HTMLResponse)
@app.get("/dashboard/kasir", response_class=HTMLResponse)
@app.get("/paket_bom", response_class=HTMLResponse)
@app.get("/resep_bom", response_class=HTMLResponse)
async def generic_redirect(request: Request):
    # sementara semua arahkan ke inventory yang sudah pasti jalan 49 bahan
    return RedirectResponse("/dashboard/admin")

# === KATEGORI PROTEKSI ===


@app.get("/dashboard/admin/inventory/{bahan_id}", response_class=HTMLResponse)
async def inventory_detail(bahan_id: str, request: Request):
    bahan = None
    kategori_label = ""
    sub_label = ""
    if supabase:
        try:
            res = supabase.table("bahan_inventory").select("*").eq("id", bahan_id).single().execute()
            bahan = res.data
            # join kategori label
            if bahan:
                try:
                    kat_code = bahan.get("kategori_utama")
                    sub_code = bahan.get("kode_kategori")
                    if kat_code:
                        rk = supabase.table("kategori_bahan").select("label").eq("code", kat_code).eq("type","utama").execute()
                        if rk.data:
                            kategori_label = rk.data[0].get("label","")
                    if sub_code:
                        rs = supabase.table("kategori_bahan").select("label").eq("code", sub_code).eq("type","sub").execute()
                        if rs.data:
                            sub_label = rs.data[0].get("label","")
                except:
                    pass
        except:
            try:
                res = supabase.table("bahan_inventory").select("*").eq("id", bahan_id).execute()
                if res.data:
                    bahan = res.data[0]
            except Exception as e:
                print(f"[detail] {e}")
    if templates is None:
        return HTMLResponse(f"<h3>Detail {bahan_id} - templates not found</h3>")
    for tmpl_name in ["inventory_detail.html", "detail_bahan.html"]:
        try:
            p = Path(templates.env.loader.searchpath[0]) / tmpl_name
            if p.exists():
                try:
                    return templates.TemplateResponse(request, tmpl_name, {"request": request, "bahan": bahan or {}, "kategori_label": kategori_label, "sub_label": sub_label})
                except:
                    return templates.TemplateResponse(tmpl_name, {"request": request, "bahan": bahan or {}, "kategori_label": kategori_label, "sub_label": sub_label})
        except:
            continue
    return HTMLResponse(f"<h1>Detail Bahan</h1><p>{bahan}</p><a href='/dashboard/admin/inventory'>Back</a>")

# === BOM RESEP & PAKET - untuk resep_bom.html & paket_bom.html ===
@app.get("/dashboard/admin/menu/resep/{menu_id}", response_class=HTMLResponse)
async def resep_bom(menu_id: str, request: Request):
    menu = None
    bahan_list = []
    bom_items = []
    if supabase:
        try:
            res = supabase.table("menu_master").select("*").eq("id", menu_id).single().execute()
            menu = res.data
        except:
            try:
                res = supabase.table("menu_master").select("*").eq("id", menu_id).execute()
                if res.data: menu = res.data[0]
            except: pass
        try:
            res_b = supabase.table("bahan_inventory").select("id,nama_bahan,kode_bahan,harga_per_satuan,satuan_default,stock_qty").order("nama_bahan").execute()
            bahan_list = res_b.data or []
        except Exception as e:
            print(f"[bom bahan] {e}")
        # coba load bom existing dari tabel menu_bom / kamus_bom / resep_bom
        for tbl in ["menu_bom", "kamus_bom", "resep_bom", "bom_resep"]:
            try:
                res_bom = supabase.table(tbl).select("*").eq("menu_id", menu_id).execute()
                if res_bom.data:
                    bom_items = res_bom.data
                    break
            except: continue
    if templates is None:
        return HTMLResponse(f"<h3>BOM Resep {menu_id}</h3>")
    for tmpl_name in ["resep_bom.html", "bom_resep.html", "resep.html"]:
        try:
            p = Path(templates.env.loader.searchpath[0]) / tmpl_name
            if p.exists():
                try:
                    return templates.TemplateResponse(request, tmpl_name, {"request": request, "menu": menu or {"kode_menu": menu_id, "nama_menu": "Resep"}, "bahan": bahan_list, "bom": bom_items, "menus": []})
                except:
                    return templates.TemplateResponse(tmpl_name, {"request": request, "menu": menu or {}, "bahan": bahan_list, "bom": bom_items})
        except: continue
    return HTMLResponse(f"<h1>Resep BOM {menu_id}</h1><p>Template resep_bom.html tidak ditemukan</p><a href='/dashboard/admin/menu'>Back</a>")

@app.get("/dashboard/admin/menu/paket/{menu_id}", response_class=HTMLResponse)
async def paket_bom(menu_id: str, request: Request):
    menu = None
    bahan_list = []
    resep_list = []
    bom_items = []
    if supabase:
        try:
            res = supabase.table("menu_master").select("*").eq("id", menu_id).single().execute()
            menu = res.data
        except:
            try:
                res = supabase.table("menu_master").select("*").eq("id", menu_id).execute()
                if res.data: menu = res.data[0]
            except: pass
        try:
            res_b = supabase.table("bahan_inventory").select("id,nama_bahan,kode_bahan,harga_per_satuan,satuan_default").order("nama_bahan").execute()
            bahan_list = res_b.data or []
        except: pass
        try:
            res_r = supabase.table("menu_master").select("id,kode_menu,nama_menu,tipe_menu").eq("tipe_menu","resep_masakan").execute()
            resep_list = res_r.data or []
            if not resep_list:
                res_r = supabase.table("menu_master").select("*").execute()
                resep_list = [m for m in (res_r.data or []) if str(m.get("tipe_menu","")).lower()=="resep_masakan" or str(m.get("tipe","")).lower()=="resep_masakan"]
        except: pass
        for tbl in ["paket_bom", "menu_bom", "kamus_bom"]:
            try:
                res_bom = supabase.table(tbl).select("*").eq("menu_id", menu_id).execute()
                if res_bom.data:
                    bom_items = res_bom.data
                    break
            except: continue
    if templates is None:
        return HTMLResponse(f"<h3>Paket BOM {menu_id}</h3>")
    for tmpl_name in ["paket_bom.html", "bom_paket.html", "paket.html"]:
        try:
            p = Path(templates.env.loader.searchpath[0]) / tmpl_name
            if p.exists():
                try:
                    return templates.TemplateResponse(request, tmpl_name, {"request": request, "menu": menu or {"kode_menu": menu_id, "nama_menu": "Paket"}, "bahan": bahan_list, "resep": resep_list, "bom": bom_items})
                except:
                    return templates.TemplateResponse(tmpl_name, {"request": request, "menu": menu or {}, "bahan": bahan_list, "resep": resep_list, "bom": bom_items})
        except: continue
    return HTMLResponse(f"<h1>Paket BOM {menu_id}</h1><a href='/dashboard/admin/menu'>Back</a>")

# === API BAHAN SAVE JSON - untuk inventory_stock.html tombol Save ===
@app.post("/api/bahan/save")
async def api_bahan_save(request: Request):
    if not supabase: raise HTTPException(500,"No supabase")
    try:
        data = await request.json()
    except:
        form = await request.form()
        data = dict(form)
    try:
        stock_qty = safe_float(data.get("stock_qty"), 0)
        if data.get("stock_awal") is not None:
            stock_qty = safe_float(data.get("stock_awal"),0) + safe_float(data.get("tambah"),0) - safe_float(data.get("terpakai"),0) or stock_qty
        payload = {
            "kode_bahan": data.get("kode_bahan"),
            "nama_bahan": (data.get("nama_bahan") or "").lower(),
            "kategori_utama": data.get("kategori_utama"),
            "kode_kategori": data.get("kode_kategori"),
            "satuan_default": data.get("satuan_default") or data.get("satuan") or "Kg",
            "stock_qty": stock_qty,
            "harga_per_satuan": safe_float(data.get("harga_per_satuan"),0),
            "id_halal": data.get("id_halal"),
            "updated_at": datetime.now().isoformat()
        }
        # hapus None
        payload = {k:v for k,v in payload.items() if v is not None and v != ""}
        if data.get("id"):
            supabase.table("bahan_inventory").update(payload).eq("id", data.get("id")).execute()
            return {"ok": True, "id": data.get("id")}
        else:
            payload["id"] = str(uuid.uuid4())
            if not payload.get("kode_bahan"):
                # auto gen kode
                kat = (payload.get("kategori_utama") or "nbt").lower()
                sub = (payload.get("kode_kategori") or "rmp").lower()
                payload["kode_bahan"] = f"hall-{kat}-{sub}-001".lower()
            supabase.table("bahan_inventory").insert(payload).execute()
            return {"ok": True, "id": payload["id"]}
    except Exception as e:
        raise HTTPException(500, str(e))

# === API KATEGORI SAVE ===

@app.post("/dashboard/admin/menu/save")
async def menu_save(request: Request):
    if not supabase: raise HTTPException(500,"No supabase")
    form = await request.form()
    data = dict(form)
    try:
        payload = {
            "kode_menu": data.get("kode_menu") or data.get("kode"),
            "nama_menu": (data.get("nama_menu") or data.get("nama") or "").lower(),
            "kategori_menu": data.get("kategori_menu") or data.get("kategori") or "Nasi Box",
            "tipe_menu": data.get("tipe_menu") or data.get("tipe") or "resep_masakan",
            "porsi": safe_float(data.get("porsi"), 10),
            "satuan": data.get("satuan") or "porsi",
            "hpp": safe_float(data.get("hpp"),0),
            "harga_jual": safe_float(data.get("harga_jual"),0),
            "updated_at": datetime.now().isoformat()
        }
        if data.get("id"):
            supabase.table("menu_master").update(payload).eq("id", data.get("id")).execute()
        else:
            payload["id"] = str(uuid.uuid4())
            supabase.table("menu_master").insert(payload).execute()
        return RedirectResponse("/dashboard/admin/menu", status_code=303)
    except Exception as e:
        raise HTTPException(500,str(e))

@app.delete("/api/menu/delete/{menu_id}")
async def delete_menu(menu_id: str):
    if not supabase: raise HTTPException(500,"No supabase")
    supabase.table("menu_master").delete().eq("id", menu_id).execute()
    # hapus bom terkait
    for tbl in ["menu_bom","kamus_bom","resep_bom","paket_bom"]:
        try:
            supabase.table(tbl).delete().eq("menu_id", menu_id).execute()
        except: pass
    return {"ok":True}

# === API BOM SAVE ===
@app.post("/api/bom/add")
async def add_bom(request: Request):
    if not supabase: raise HTTPException(500,"No supabase")
    data = await request.json()
    try:
        payload = {
            "id": str(uuid.uuid4()),
            "menu_id": data.get("menu_id"),
            "bahan_id": data.get("bahan_id"),
            "qty": safe_float(data.get("qty"),0),
            "satuan": data.get("satuan") or "Kg",
            "created_at": datetime.now().isoformat()
        }
        # simpan ke menu_bom kalau ada, fallback kamus_bom
        for tbl in ["menu_bom","kamus_bom","resep_bom"]:
            try:
                supabase.table(tbl).insert(payload).execute()
                # update hpp di menu_master = sum qty*harga
                try:
                    # hitung hpp baru
                    res_bom = supabase.table(tbl).select("qty,bahan_id").eq("menu_id", payload["menu_id"]).execute()
                    total_hpp = 0
                    for b in (res_bom.data or []):
                        try:
                            rb = supabase.table("bahan_inventory").select("harga_per_satuan").eq("id", b.get("bahan_id")).single().execute()
                            if rb.data:
                                total_hpp += safe_float(b.get("qty")) * safe_float(rb.data.get("harga_per_satuan"))
                        except: pass
                    supabase.table("menu_master").update({"hpp": total_hpp, "updated_at": datetime.now().isoformat()}).eq("id", payload["menu_id"]).execute()
                except: pass
                break
            except: continue
        return {"ok":True, "id": payload["id"]}
    except Exception as e:
        raise HTTPException(500,str(e))

@app.delete("/api/bom/{bom_id}")
async def delete_bom(bom_id: str):
    if not supabase: raise HTTPException(500,"No supabase")
    for tbl in ["menu_bom","kamus_bom","resep_bom","paket_bom"]:
        try:
            supabase.table(tbl).delete().eq("id", bom_id).execute()
        except: pass
    return {"ok":True}

