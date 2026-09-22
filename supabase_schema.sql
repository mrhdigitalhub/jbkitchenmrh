
-- JB KITCHEN MRH - Schema
-- Enable UUID
create extension if not exists "uuid-ossp";

-- PROFILES / USERS with Roles
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  role text check (role in ('admin','owner','produksi','delivery')) not null,
  full_name text,
  created_at timestamp with time zone default now()
);

-- MASTER BAHAN
create table public.kategori_bahan (
  id serial primary key,
  kode_kategori text unique not null,
  nama_kategori text not null
);

create table public.bahan_inventory (
  id uuid primary key default uuid_generate_v4(),
  kode_bahan text unique not null,
  nama_bahan text not null,
  kategori_id int references public.kategori_bahan(id),
  satuan_default text,
  merek text,
  produsen text,
  supplier text,
  id_halal text,
  stock_qty numeric default 0,
  stock_minimum numeric default 0,
  harga_per_satuan numeric default 0,
  aset_value numeric generated always as (stock_qty * harga_per_satuan) stored,
  created_at timestamptz default now()
);

-- CUSTOMER
create table public.customers (
  id uuid primary key default uuid_generate_v4(),
  nama text not null,
  alamat text,
  hp text,
  is_active boolean default true
);

-- MASTER MENU & RESEP (BOM)
create table public.master_menu (
  id uuid primary key default uuid_generate_v4(),
  nama_menu text not null,
  kategori_menu text,
  harga_jual numeric not null,
  foto_url text,
  is_best_seller boolean default false,
  created_at timestamptz default now()
);

create table public.resep_bom (
  id uuid primary key default uuid_generate_v4(),
  menu_id uuid references public.master_menu(id) on delete cascade,
  bahan_id uuid references public.bahan_inventory(id),
  qty_need numeric not null,
  satuan text,
  cost numeric
);

-- ORDERS
create table public.orders (
  id uuid primary key default uuid_generate_v4(),
  kode_order text unique not null,
  customer_id uuid references public.customers(id),
  tanggal_order date default current_date,
  tanggal_kirim date,
  status text check (status in ('draft','masuk','proses_produksi','packing','pickup','delivery','diterima','closed','cancel')) default 'draft',
  total_hpp numeric default 0,
  total_jual numeric default 0,
  food_cost_percent numeric,
  created_by uuid,
  created_at timestamptz default now()
);

create table public.order_items (
  id uuid primary key default uuid_generate_v4(),
  order_id uuid references public.orders(id) on delete cascade,
  menu_id uuid references public.master_menu(id),
  qty int not null,
  hpp_item numeric,
  jual_item numeric
);

-- PRODUKSI LOG
create table public.produksi_log (
  id uuid primary key default uuid_generate_v4(),
  order_id uuid references public.orders(id),
  stage text check (stage in ('pesanan_masuk','draft','proses_produksi','packing')),
  note text,
  updated_by uuid,
  updated_at timestamptz default now()
);

-- DELIVERY LOG
create table public.delivery_log (
  id uuid primary key default uuid_generate_v4(),
  order_id uuid references public.orders(id),
  stage text check (stage in ('pickup','delivery','diterima','closed')),
  bukti_foto_url text,
  penerima text,
  updated_at timestamptz default now()
);

-- WASTE / REJECT, UTILITY, MANPOWER
create table public.waste_log (
  id uuid primary key default uuid_generate_v4(),
  bahan_id uuid references public.bahan_inventory(id),
  qty numeric,
  alasan text,
  tanggal date default current_date
);

create table public.utility_log (
  id uuid primary key default uuid_generate_v4(),
  jenis text,
  qty numeric,
  biaya numeric,
  tanggal date default current_date
);

-- Enable RLS
alter table public.profiles enable row level security;
alter table public.bahan_inventory enable row level security;
alter table public.orders enable row level security;
-- For MVP, allow all authenticated
create policy "allow all auth" on public.profiles for all using (auth.role() = 'authenticated');
create policy "allow all auth" on public.bahan_inventory for all using (auth.role() = 'authenticated');
create policy "allow all auth" on public.kategori_bahan for all using (true);
create policy "allow all auth" on public.master_menu for all using (true);
create policy "allow all auth" on public.resep_bom for all using (true);
create policy "allow all auth" on public.orders for all using (true);
create policy "allow all auth" on public.order_items for all using (true);
create policy "allow all auth" on public.customers for all using (true);

-- Seed kategori
insert into public.kategori_bahan (kode_kategori, nama_kategori) values
('PROT','Protein'),('CARB','Karbohidrat'),('VEG','Sayuran'),('BUMBU','Bumbu'),('PACK','Packaging'),('OTHER','Lain-lain');
