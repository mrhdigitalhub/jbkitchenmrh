
# JB KITCHEN-MRH - Aplikasi Digital Jasa Boga FREE 100%

Stack: Python FastAPI + Supabase + Vercel + VS Code

## Fitur sesuai draft:
- 4 Role Auth: Admin (full), Owner (live view), Produksi (Masuk/Draft/Proses/Packing), Delivery (Pickup/Delivery/Diterima/Closed)
- Dashboard Admin: Total Bahan Baku, Order Aktif/Closed, Total Aset Inventory, Kondisi Stock Minimum, Kategori Bahan, Customer Aktif, Food Cost% vs Target, Performance Produksi/Delivery/Utility/ManPower, Bahan Reject/Waste, Menu Best Seller & Slow
- Inventory Stock dengan Kode Halal 10 digit, Satuan, Merek, Produsen, Supplier
- Master Menu & Resep (BOM)
- Kalkulator Order BOM & HPP otomatis
- Proses Produksi & Delivery tracking

## Setup di VS Code
1. Clone / unzip
2. python -m venv venv && source venv/bin/activate (windows: venv\Scripts\activate)
3. pip install -r requirements.txt
4. Copy .env.example ke .env isi SUPABASE_URL & KEY
5. Jalankan SQL di supabase_schema.sql di Supabase SQL Editor
6. Buat 4 user di Supabase Auth, lalu insert ke public.profiles dengan role masing-masing
7. uvicorn app.main:app --reload

## Deploy Vercel
vercel --prod
Set ENV di Vercel Dashboard.

## Next Step yang bisa saya bantu:
- Integrasi Supabase Auth asli (bukan cookie)
- Upload bukti delivery ke Supabase Storage
- Export PDF Invoice & Surat Jalan
- WA Gateway untuk notifikasi produksi & delivery
