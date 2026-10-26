# Modul Peta Kebun (`map_module`)

Penanggung jawab: Muhammad Wisnu Jaya Wardana. Spesifikasi sumber: `docs/prd.md` §5.5, §6, §9, README §2.3, dan
desain Figma "peta-kebun-desktop" (halaman "Draf SVG (v0.1)") beserta komponen `Card / Location`, `Badge`, `Chip`,
`Button`, `Input` di halaman "Components".

## Yang disediakan

| Halaman | URL | Akses |
| --- | --- | --- |
| Peta publik (marker, filter, "dekat saya" + radius) | `/map/` | Semua orang |
| Peta yang membuka titik pengambilan produk | `/map/?product=<id>` | Semua orang |
| Peta yang memfokuskan satu lokasi | `/map/?focus=<id>` | Semua orang |
| Detail lokasi | `/map/locations/<id>/` | Semua orang (lokasi nonaktif: pemilik/Admin) |
| Lokasi saya | `/map/mine/` | Petani, Petani–Penjual, Admin |
| Tambah / ubah / hapus | `/map/locations/new/`, `…/<id>/edit/`, `…/<id>/delete/` (POST) | Lihat hak akses |
| API daftar | `GET /map/api/locations/?q=&kind=` | Semua orang |
| API terdekat | `POST /map/api/nearby/` (body JSON `lat`, `lng`, opsional `q`, `kind`, `radius_km`) | Semua orang (CSRF wajib) |

## Model `Location`

**Ringkasan publik** (selalu tampil, juga untuk Guest): `kind` (`community_garden`, `farmer_garden`, `merchant`,
`pickup_point`), `name`, `latitude`/`longitude` (DecimalField 9,6; divalidasi −90..90 dan −180..180; (0, 0) ditolak),
`area` (wilayah, mis. "Beji, Depok"), `description` (≤300 karakter), `commodities` (komoditas, dipisah koma),
`schedule` (jadwal buka/pengambilan, mis. "Sabtu 08.00–11.00"),
`managed_by` (nama pemilik/komunitas; kosong = username pemilik), `photo_url`.

**Detail** (mengikuti `detail_visibility`): `address` (alamat lengkap), `contact_info`.

Lainnya: `owner` (FK `authentication.User`, nullable), `detail_visibility` (`private` / `members` / `public`,
default `members`), `is_active`, `created_at`, `updated_at`.

Pemetaan ke README §2.3: nama kebun → `name`; koordinat → `latitude`/`longitude`; alamat atau deskripsi lokasi →
`area` + `address` + `description`; foto kebun → `photo_url`; nama pemilik atau komunitas → `managed_by`;
deskripsi singkat → `description`; jenis komoditas yang tersedia → `commodities`; kontak jika diperbolehkan →
`contact_info` + `detail_visibility`. "Lokasi pengambilan bibit atau kompos" memakai jenis `pickup_point`.

## Hak akses

| Peran | Boleh membuat jenis | Boleh ubah/hapus |
| --- | --- | --- |
| Guest | – (hanya melihat) | – |
| `user`, `farmer` | `community_garden`, `farmer_garden` | Milik sendiri |
| `farmer-seller` | Semua jenis | Milik sendiri |
| `admin` / `is_staff` / `is_superuser` | Semua jenis | Semua lokasi |

`user` disamakan dengan Petani karena registrasi saat ini memberi peran `user`, sedangkan PRD §5.1 menyebut
pengguna baru = Petani. Aturannya ada di satu konstanta, `MEMBER_ROLES` di `map_module/permissions.py`.

Alamat lengkap & kontak: `public` → semua orang; `members` → pengguna yang sudah masuk; `private` → pemilik dan Admin.
Detail yang tidak boleh dilihat tidak pernah ikut ke HTML/JSON. Pencarian teks tidak mencari di alamat lengkap,
supaya alamat yang disembunyikan tidak bisa ditebak lewat pencarian.

## Kontrak untuk modul lain

**Marketplace → Peta** (PRD §5.5 butir 5: "halaman detail produk dapat membuka lokasi yang sama pada peta")

Marketplace menyimpan titik pengambilan di `Product` (`latitude`, `longitude`, `location`, `pickup_address`).
Peta membacanya lewat `apps.get_model('marketplace', 'Product')`, tanpa import dan tanpa foreign key.

```python
from map_module.services import product_map_url, locations_for_owner

product_map_url(product)            # "/map/?product=<id>": peta membuka titik pengambilan produk itu
location.get_map_url()              # "/map/?focus=<id>": peta memfokuskan satu Location
locations_for_owner(product.seller) # Location aktif milik merchant
```

Di template marketplace cukup: `<a href="{% url 'map_module:map' %}?product={{ product.pk }}">Lihat di peta</a>`.
Produk nonaktif atau tanpa koordinat → peta tetap terbuka dengan pesan "titik pengambilan tidak tersedia".

Field `Product` yang dibaca: `pk, name, location, pickup_address, latitude, longitude, is_active`. Bila nama field
ini berubah, pin produk tidak tampil (tanpa galat 500). Kabari pemilik modul peta.

**Peta → Marketplace.** Lokasi `merchant`/`pickup_point` yang punya `owner` menautkan ke
`reverse('marketplace:seller_store', args=[owner.username])`; pin produk menautkan ke
`reverse('marketplace:product_detail', args=[pk])`. Bila URL belum ada, tautan disembunyikan tanpa galat.
**Nama kedua URL ini harus dipertahankan** oleh pemilik marketplace.

**Peta → Admin dashboard** (PRD §5.6): `map_module.services.summary_counts()` →
`{'gardens', 'merchants', 'pickup_points', 'total'}` (lokasi aktif saja).

Bentuk JSON satu lokasi: `id, kind, kind_label, kind_short, badge_tone, name, lat, lng, area, description,
commodities, schedule, managed_by,
photo_url, detail_url, store_url, address, contact, detail_locked, detail_login_required, detail_owner_only,
distance_km, distance_label`. `address`/`contact` kosong bila tidak berhak; `distance_*` hanya terisi pada
`api/nearby/`.

## Keputusan dan asumsi (menutup butir "Peta" dan "Kontak/lokasi publik" di PRD §10)

- **Penyedia peta:** Leaflet 1.9.4 (dari unpkg, dengan SRI yang dihitung dari paket npm resmi) + tile gelap
  CARTO `dark_all` (data OpenStreetMap), tanpa API key, agar serasi dengan tema gelap di draf Figma. Atribusi
  OpenStreetMap dan CARTO wajib tampil (sudah ada). Layanan basemap CARTO gratis untuk pemakaian non-komersial dengan
  batas kuota; untuk produksi bertrafik tinggi, ganti URL tile di `static/js/map.js` dan `static/js/map-point.js`.
- **Tampilan:** mengikuti draf Figma. Penyimpangan yang disengaja: (1) ada chip & legenda "Kebun petani" karena PRD
  meminta 4 jenis lokasi, sedangkan draf hanya punya 3; (2) titik posisi pengguna memakai token `focus` (hijau),
  bukan biru, karena warna biru tidak ada di design system.
- **Gaya Leaflet** ada di `static/css/map.css` (bukan `input.css` bersama). Isinya memakai `var(--color-*)`; Tailwind
  v4 hanya mengeluarkan variabel token yang dipakai sebagai utility, jadi token yang dirujuk di sana juga dipakai di
  template peta.
- **Tingkat detail untuk Guest:** jenis, nama, wilayah, komoditas, deskripsi, pengelola, foto, dan posisi marker
  (ringkasan publik). Alamat lengkap dan kontak mengikuti pilihan pemilik (default: pengguna yang sudah masuk).
  Catatan: posisi marker tetap publik, jadi pemilik kebun di rumah sebaiknya menaruh titik di lokasi umum terdekat.
- **Foto lokasi** memakai `photo_url` (tautan), bukan unggahan, agar modul ini tidak bergantung pada Pillow/`MEDIA_ROOT`
  sebelum modul marketplace di-merge.
- **Geolokasi pengguna:** izin hanya diminta saat tombol "Dekat saya" ditekan. Koordinat dan radius dikirim lewat
  body POST, dipakai menghitung jarak (haversine) pada request itu, tidak disimpan dan tidak masuk URL.
- Batas pengaman 500 marker per respons (`MAX_MARKERS`); radius API 0 < r ≤ 500 km.

## Menjalankan tes

```
python manage.py test map_module
```

## Catatan merge

- `config/settings.py` dan `config/urls.py` masing-masing diubah satu baris (app dan route `map/`), dan
  `templates/includes/navbar.html` dua tautan. Branch marketplace mengubah area yang sama, jadi konflik kecil yang
  tinggal digabung: pertahankan baris kedua belah pihak.
- `static/css/style.css` adalah hasil build. Bila konflik, selesaikan dengan menjalankan `npm run build:css` ulang.
