# Urban Harvest Community

## Tautan

* **Deployment PWS:** https://adrian-nathanael-midterm-project.pws.cs.ui.ac.id
* **Desain Figma:** https://www.figma.com/design/uW8pusibGXhxVVTBWcD7JE/Untitled

## Design System

Design system disepakati di Figma (page **Foundations** dan **Components**) dan diimplementasikan di `static/css/input.css` lewat blok `@theme` Tailwind CSS v4. Nama token di kode **sama persis** dengan nama Figma Variables, misalnya variable `brand` di Figma menjadi `--color-brand` di CSS dan class `bg-brand` / `text-brand` di template.

**Aturan pakai**

* Jangan menulis warna hex langsung di template (mis. `bg-[#080c09]`). Pakai token (`bg-canvas`) atau tambahkan token baru di `@theme` dan di Figma.
* Tipografi: `font-display` (Playfair Display) untuk judul besar, `font-sans` (Plus Jakarta Sans, default) untuk teks dan UI.
* Satu tombol `btn-primary` per area; sisanya `btn-secondary` atau `btn-ghost`.

**Token utama**

| Token | Nilai | Dipakai untuk |
| --- | --- | --- |
| `canvas` | `#080C09` | Latar halaman |
| `surface` / `surface-2` | `#0A0A0A` / `#171717` | Kartu, panel / hover, disabled |
| `line` | `#262626` | Border kartu, divider |
| `brand` / `brand-hover` | `#059669` / `#10B981` | Aksi utama hijau |
| `brand-soft` | `#6EE7B7` | Link, harga, status sukses |
| `body` / `muted` | `#D4D4D4` / `#A3A3A3` | Paragraf / keterangan |
| `glass` / `glass-border` | putih 8% / 25% | Latar dan border input, tombol secondary |
| `focus` | `#34D399` | Garis fokus |
| `danger` / `warning` | `#FDA4AF` / `#FCD34D` | Error / peringatan, titik ambil |

Radius: `rounded-lg` (input, 8px), `rounded-2xl` (kartu, 16px), `rounded-pill` (tombol, badge, chip). Spasi mengikuti skala bawaan Tailwind (kelipatan 4px).

**Komponen**

| Komponen Figma | Class | Contoh |
| --- | --- | --- |
| Button | `.btn` + `.btn-primary` \| `.btn-brand` \| `.btn-secondary` \| `.btn-danger` \| `.btn-ghost` (opsional `.btn-sm`) | `<button class="btn btn-primary">Simpan</button>` |
| Input | `.field` (membungkus label + input bawaan Django), `.input`, `.field-error`, `.field-help` | `<div class="field"><label>…</label>{{ form.email }}</div>` |
| Badge | `.badge` + `.badge-brand` \| `.badge-warning` \| `.badge-danger` \| `.badge-neutral` | `<span class="badge badge-warning">Titik ambil</span>` |
| Chip | `.chip` (+ `.chip-active` atau `aria-pressed="true"`) | `<button class="chip chip-active">Semua</button>` |
| Card | `.card` (+ `.card-selected`) | `<article class="card">…</article>` |
| Link | `.link` | `<a class="link" href="…">Daftar</a>` |

Contoh pemakaian lengkap ada di `templates/login.html` dan `templates/register.html`.

## Menjalankan halaman awal

Proyek memakai Django dengan app `main`, template global di `templates/`, dan aset CSS di `static/css/`, mengikuti pola repo [myportofolio](https://github.com/Adriannathan89/myportofolio). Tailwind CSS v4 dibangun dari `static/css/input.css` ke `static/css/style.css`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm ci
npm run build:css
python manage.py runserver
```

Buka `http://127.0.0.1:8000/` untuk melihat landing page. Selama mengubah kelas Tailwind di template, jalankan `npm run watch:css` di terminal lain agar CSS dibangun ulang otomatis.

## Checkpoint 1

## 1. Deskripsi Aplikasi

### Urban Harvest Community

**Urban Harvest Community** adalah platform komunitas berbasis web yang ditujukan untuk mendukung aktivitas **urban farming** dan pertanian komunitas di wilayah perkotaan.

Aplikasi ini menjadi ruang digital yang mempertemukan petani urban, warga, komunitas, dan calon pembeli dalam satu platform. Pengguna dapat berbagi pengalaman mengenai urban farming, menawarkan hasil panen atau kebutuhan pertanian, menemukan kebun urban di sekitar mereka, serta mencari komoditas menggunakan pencarian berbasis **Large Language Model (LLM)**.

Permasalahan yang ingin diselesaikan aplikasi ini adalah masih terpisahnya informasi mengenai komunitas urban farming, lokasi kebun, hasil panen yang tersedia, serta komunikasi antarpetani dan masyarakat. Urban Harvest Community menggabungkan fungsi-fungsi tersebut ke dalam satu platform.

### Tujuan Aplikasi

Urban Harvest Community memiliki beberapa tujuan utama:

* Mempermudah masyarakat menemukan dan membeli hasil pertanian lokal.
* Memberikan tempat bagi petani urban untuk menjual atau membagikan hasil panen.
* Membangun komunitas tempat pengguna dapat berbagi pengalaman dan pengetahuan mengenai urban farming.
* Mempermudah pengguna menemukan lokasi kebun urban maupun lokasi pengambilan produk.
* Memberikan pengalaman pencarian marketplace yang lebih natural melalui penggunaan LLM.
* Mendorong partisipasi masyarakat dalam aktivitas pertanian perkotaan dan ekonomi berbasis komunitas.

---

# 2. Fitur Utama Aplikasi

## 2.1 Marketplace Sederhana

Marketplace menjadi tempat pengguna menemukan produk yang disediakan oleh petani atau merchant pada platform.

Produk yang dapat ditampilkan antara lain:

* Hasil panen seperti sayuran, buah, dan tanaman herbal.
* Bibit tanaman.
* Benih.
* Kompos.
* Pupuk organik.
* Media tanam.
* Produk pendukung urban farming lainnya.
* Energi atau sumber daya surplus jika nantinya dibutuhkan oleh pengembangan aplikasi.

Setiap produk memiliki informasi utama berupa:

* Nama produk.
* Foto produk.
* Deskripsi.
* Harga.
* Stok tersedia.
* Kategori produk.
* Lokasi penjual atau merchant.
* Nama merchant.
* Informasi waktu unggah atau pembaruan produk.

Pengguna dapat menjelajahi katalog marketplace dan melakukan pencarian menggunakan beberapa filter seperti:

* Kategori produk.
* Rentang harga.
* Lokasi.
* Ketersediaan stok.

Marketplace pada tahap awal difokuskan pada **product discovery**, yaitu membantu pengguna menemukan produk yang tersedia pada platform.

---

## 2.2 Forum Komunitas

Forum komunitas merupakan tempat komunikasi antaranggota Urban Harvest Community.

Pengguna yang telah login dapat membuat posting berbasis teks untuk:

* Membagikan pengalaman berkebun.
* Membagikan tips urban farming.
* Bertanya mengenai permasalahan tanaman.
* Mendiskusikan teknik bercocok tanam.
* Membagikan informasi kegiatan komunitas.
* Membagikan informasi hasil panen.
* Bertukar informasi bibit, kompos, atau perlengkapan pertanian.

Setiap posting dapat menerima interaksi berupa:

* **Like**
* **Comment**

Pemilik posting dapat:

* Membuat posting baru.
* Melihat posting.
* Mengedit posting sendiri.
* Menghapus posting sendiri.

Ketentuan posting:

* Konten berbasis teks.
* Panjang maksimal **1000 kata**.
* Pada tahap awal belum terdapat filtering otomatis terhadap isi teks.

Guest dapat membaca posting tetapi tidak dapat membuat posting maupun memberikan interaksi.

---

## 2.3 Peta Kebun Urban

Fitur peta berfungsi sebagai pusat informasi berbasis lokasi.

Peta digunakan untuk menampilkan beberapa jenis lokasi, misalnya:

* Kebun urban komunitas.
* Kebun milik petani.
* Lokasi merchant.
* Lokasi pengambilan hasil panen.
* Lokasi pengambilan bibit atau kompos.

Setiap titik pada peta dapat memiliki informasi berupa:

* Nama kebun.
* Koordinat.
* Alamat atau deskripsi lokasi.
* Foto kebun.
* Nama pemilik atau komunitas.
* Deskripsi singkat.
* Jenis komoditas yang tersedia.
* Informasi kontak jika diperbolehkan.

Apabila pengguna memberikan izin akses lokasi, sistem dapat menggunakan koordinat GPS pengguna untuk:

* Menampilkan kebun di sekitar pengguna.
* Menghitung jarak pengguna dengan lokasi kebun.
* Mengurutkan kebun berdasarkan jarak terdekat.
* Membantu pengguna menemukan lokasi pengambilan barang.

Guest hanya mendapatkan akses terbatas terhadap informasi yang ditampilkan pada peta.

---

## 2.4 Searching Komoditas Berbasis LLM

Fitur **LLM Search** digunakan untuk memberikan pengalaman pencarian yang lebih fleksibel dibandingkan pencarian berbasis keyword biasa.

Pengguna dapat menuliskan kebutuhan menggunakan bahasa natural.

Contoh:

> "Cari tomat yang harganya di bawah Rp30.000 dan lokasinya tidak terlalu jauh."

atau:

> "Saya mau cari bibit tanaman yang cocok untuk pemula dan harganya murah."

Sistem kemudian menginterpretasikan kebutuhan tersebut dan mengubahnya menjadi parameter pencarian yang sesuai dengan data marketplace.

Parameter yang dapat diekstraksi misalnya:

* Nama komoditas.
* Kategori.
* Harga minimum.
* Harga maksimum.
* Lokasi.
* Stok.
* Kata kunci tambahan.

LLM **tidak membuat produk baru yang tidak terdapat pada database**. Produk yang ditampilkan tetap berasal dari data marketplace Urban Harvest Community.

Dengan demikian, fungsi LLM digunakan sebagai lapisan interpretasi antara bahasa pengguna dan sistem pencarian database.

Alur sederhananya:

**Prompt Pengguna → LLM → Interpretasi Query → Pencarian Database → Produk Marketplace → Hasil Pencarian**

---

# 3. Daftar Modul Rencana

## 3.1 Modul Autentikasi & Pengguna

**Auth & Profile Module**

Modul ini bertanggung jawab terhadap identitas, autentikasi, profil, serta hak akses pengguna.

### Fitur Registrasi

Pengguna baru dapat membuat akun menggunakan:

* Nama.
* Email.
* Password.

Ketentuan password:

* Minimal **8 karakter**.
* Memiliki minimal satu karakter khusus atau **special character**.
* Password disimpan secara aman dalam bentuk hasil hashing, bukan plain text.

Email harus bersifat unik sehingga satu alamat email tidak dapat digunakan untuk beberapa akun.

### Fitur Login

Pengguna dapat melakukan login menggunakan:

* Email.
* Password.

Setelah autentikasi berhasil, sistem memberikan akses berdasarkan role pengguna.

### Manajemen Profil

Pengguna dapat melihat dan memperbarui informasi profil seperti:

* Nama.
* Foto profil.
* Deskripsi atau bio.
* Lokasi.
* Informasi komunitas.
* Informasi merchant untuk pengguna yang telah menjadi penjual.

### Role-Based Access Control

Modul autentikasi juga menentukan fitur yang dapat digunakan berdasarkan role.

Role utama:

* Guest.
* Petani.
* Petani - Penjual.
* Admin.

Sebagai contoh, hanya Petani - Penjual yang dapat membuat listing marketplace, sedangkan Guest hanya dapat melihat konten tertentu.

### Pengajuan Menjadi Penjual

Petani dapat melakukan pengajuan untuk mendapatkan status **Petani - Penjual**.

Setelah disetujui, pengguna mendapatkan fitur tambahan berupa:

* Nama merchant.
* Etalase merchant.
* Pembuatan produk.
* Pengeditan produk.
* Penghapusan produk.
* Pengelolaan stok.

---

# 3.2 Modul Community Posting

Modul ini mengelola seluruh aktivitas forum komunitas.

### Membuat Post

Pengguna yang telah login dapat membuat posting berbasis teks.

Informasi posting meliputi:

* ID post.
* ID pembuat post.
* Isi post.
* Waktu dibuat.
* Waktu diperbarui.
* Jumlah like.
* Jumlah comment.

Posting memiliki batas maksimum **1000 kata**.

### Edit Post

Pengguna hanya dapat mengedit posting yang dibuat oleh dirinya sendiri.

Setelah diperbarui, sistem dapat menyimpan informasi waktu terakhir perubahan.

### Delete Post

Pengguna dapat menghapus posting yang dibuat sendiri.

Admin dapat memiliki hak akses tambahan untuk melakukan moderasi jika fitur tersebut dikembangkan.

### Like

Pengguna dapat memberikan like terhadap posting.

Idealnya satu pengguna hanya dapat memberikan satu like pada satu posting. Apabila tombol like ditekan kembali, like dapat dibatalkan.

### Comment

Pengguna dapat memberikan komentar terhadap sebuah post.

Data komentar dapat berisi:

* ID komentar.
* ID post.
* ID pengguna.
* Isi komentar.
* Waktu komentar dibuat.

### Feed Komunitas

Posting terbaru dapat ditampilkan dalam sebuah feed.

Informasi yang ditampilkan misalnya:

* Foto profil.
* Nama pengguna.
* Isi posting.
* Waktu posting.
* Jumlah like.
* Jumlah komentar.

---

# 3.3 Modul Marketplace Discovery

Modul Marketplace Discovery bertugas mengelola proses pencarian dan penampilan produk.

### Product Catalog

Marketplace menampilkan seluruh produk aktif yang masih dapat ditemukan oleh pengguna.

Setiap card produk dapat menampilkan:

* Foto produk.
* Nama produk.
* Harga.
* Stok.
* Lokasi.
* Merchant.
* Kategori.

### Product Detail

Pengguna dapat membuka halaman detail produk untuk melihat informasi lebih lengkap seperti:

* Foto.
* Deskripsi.
* Harga.
* Stok.
* Lokasi merchant.
* Informasi merchant.
* Informasi pengambilan produk.

### Search

Pengguna dapat mencari produk berdasarkan nama atau keyword tertentu.

Contoh:

> "tomat"

Sistem akan menampilkan produk yang memiliki hubungan dengan keyword tersebut.

### Filter

Pengguna dapat mempersempit hasil pencarian berdasarkan:

**Kategori**

Contoh:

* Sayuran.
* Buah.
* Bibit.
* Kompos.
* Media tanam.

**Lokasi**

Produk dapat difilter berdasarkan lokasi merchant atau kebun.

**Harga**

Pengguna dapat menentukan:

* Harga minimum.
* Harga maksimum.

### Sorting

Sebagai pengembangan, katalog dapat mendukung pengurutan berdasarkan:

* Harga termurah.
* Harga tertinggi.
* Produk terbaru.
* Lokasi terdekat.

### Stock Management

Produk hanya dapat dibeli apabila stok masih tersedia.

Ketika stok mencapai 0, produk dapat:

* Ditandai sebagai habis, atau
* Tidak ditampilkan pada hasil pencarian aktif.

---

# 3.4 Modul Searching LLM

Modul ini merupakan pengembangan dari fungsi pencarian marketplace.

Perbedaannya dengan pencarian biasa adalah pengguna tidak harus mengetahui keyword atau filter yang tepat.

### Natural Language Query

Pengguna memasukkan kebutuhan menggunakan bahasa sehari-hari.

Contoh:

> "Saya butuh sayuran di bawah Rp20.000."

LLM menganalisis prompt kemudian menentukan kebutuhan pencarian.

Hasil interpretasi dapat berbentuk parameter seperti:

```json
{
  "categories": ["sayuran"],
  "max_price": 20000
}
```

Parameter tersebut kemudian diteruskan ke backend untuk melakukan query terhadap database marketplace.

### Query Extraction

Informasi yang dapat diambil dari prompt antara lain:

* Nama komoditas.
* Kategori.
* Harga maksimum.
* Harga minimum.
* Lokasi.
* Batas jumlah hasil (`limit`).
* Preferensi lain yang didukung filter pencarian.

Contoh:

> "Cari bibit cabai maksimal Rp25.000."

Dapat diterjemahkan menjadi:

```json
{
  "keyword": "bibit cabai",
  "max_price": 25000
}
```

### Database Grounding

LLM tidak berfungsi sebagai sumber data marketplace.

LLM menafsirkan permintaan dan menyusun suggestion hanya dari kandidat yang diberikan backend.

Data hasil pencarian harus berasal dari database aplikasi.

Hal ini penting untuk menghindari kasus ketika LLM memberikan rekomendasi produk yang sebenarnya tidak tersedia.

### Result Display

Setelah query database selesai, hasil ditampilkan sebagai kartu produk yang mengambil data dari marketplace dan mengarah ke halaman detail produk.

Contohnya:

```text
User Prompt
     ↓
LLM API
     ↓
Structured Search Query
     ↓
Backend
     ↓
Marketplace Database
     ↓
Product Results
     ↓
Marketplace UI
```

### Fallback

* Permintaan ambigu, syarat yang belum didukung, atau hasil kosong meminta pengguna memperjelas pencarian.
* Jika OpenRouter gagal saat interpretasi, sistem menampilkan pesan aman dan menyediakan tautan untuk menjelajahi marketplace.
* Jika hanya tahap suggestion yang gagal, hasil query tetap ditampilkan dengan penjelasan berdasarkan data produk.
* Jika RabbitMQ tidak tersedia, coordinator memproses job melalui satu worker lokal dan mencoba menghubungkan broker kembali.

Panduan implementasi, setup, contoh prompt, dan API tersedia pada [Dokumentasi Modul Searching LLM](#dokumentasi-modul-searching-llm).

---

# 3.5 Modul Peta Kebun

Modul Peta Kebun mengelola data lokasi geografis dalam Urban Harvest Community.

### Map Display

Sistem menampilkan peta interaktif dengan marker untuk lokasi:

* Kebun urban.
* Merchant.
* Lokasi pengambilan produk.
* Komunitas urban farming.

### Garden Marker

Marker dapat ditekan untuk membuka informasi mengenai kebun.

Informasi dapat berupa:

* Nama kebun.
* Foto.
* Deskripsi.
* Lokasi.
* Komoditas.
* Merchant atau pemilik.

### User Location

Dengan izin pengguna, sistem dapat mengambil koordinat pengguna.

Informasi tersebut digunakan untuk menentukan lokasi kebun di sekitar pengguna.

### Nearest Garden

Sistem dapat menghitung jarak antara:

**Lokasi pengguna → Lokasi kebun**

Data kemudian dapat diurutkan berdasarkan jarak.

Contohnya:

```text
Kebun A — 0.8 km
Kebun B — 1.5 km
Kebun C — 3.2 km
```

### Integrasi Marketplace

Lokasi merchant pada marketplace dapat dihubungkan dengan peta.

Pengguna yang sedang melihat sebuah produk dapat membuka lokasi merchant atau titik pengambilan barang melalui peta.

---

# 4. Public API / External API

## OpenRouter API

Referensi:

`https://openrouter.ai/models`

OpenRouter direncanakan sebagai gateway untuk mengakses model bahasa yang digunakan oleh fitur **LLM Search**.

Fungsi utama penggunaan API adalah mengubah natural-language prompt pengguna menjadi parameter pencarian terstruktur.

Contoh:

```text
User:
"Cari tomat di bawah 30 ribu"

↓ OpenRouter / LLM

{
  "keyword": "tomat",
  "max_price": 30000
}

↓ Backend Query

SELECT produk yang sesuai

↓ Marketplace

Menampilkan produk nyata yang tersedia.
```

Dengan arsitektur tersebut, LLM tidak memiliki kewenangan langsung untuk menentukan data produk yang ditampilkan.

---

# 5. Peran Pengguna

## 5.1 Guest

Guest merupakan pengguna yang belum melakukan login.

Hak akses:

* Melihat landing page.
* Melihat katalog marketplace.
* Melihat detail produk.
* Membaca forum.
* Melihat sebagian informasi peta kebun.
* Melakukan pencarian produk secara terbatas.

Guest tidak dapat:

* Membuat post.
* Memberikan like.
* Memberikan komentar.
* Membeli produk.
* Menjual produk.
* Mengelola profil.

---

## 5.2 Petani

Petani merupakan role utama setelah pengguna membuat akun.

Hak akses:

* Seluruh akses Guest.
* Membuat posting forum.
* Mengedit posting sendiri.
* Menghapus posting sendiri.
* Like posting.
* Comment posting.
* Membeli produk marketplace.
* Menggunakan pencarian LLM.
* Melihat lokasi kebun secara lebih lengkap.
* Mengumpulkan poin kontribusi.

### Contribution Point

Poin kontribusi dapat diberikan berdasarkan aktivitas pengguna.

Contohnya:

* Membuat posting.
* Berpartisipasi dalam komunitas.
* Melakukan aktivitas tertentu dalam marketplace.

Poin tersebut dapat digunakan sebagai mekanisme gamification untuk mendorong partisipasi komunitas.

---

# 5.3 Petani - Penjual

Petani - Penjual merupakan Petani yang telah mendapatkan akses merchant setelah proses pengajuan.

Role ini mendapatkan seluruh fitur Petani ditambah kemampuan marketplace.

Fitur tambahan:

* Membuat merchant.
* Memiliki nama merchant.
* Memiliki halaman etalase.
* Menambahkan produk.
* Mengedit produk.
* Menghapus produk.
* Mengatur harga.
* Mengatur stok.
* Mengunggah foto produk.
* Menentukan lokasi pengambilan barang.

Contoh struktur:

```text
Petani
  ↓
Pengajuan Merchant
  ↓
Persetujuan
  ↓
Petani - Penjual
  ↓
Merchant + Etalase + Product Management
```

---

# 5.4 Admin

Admin memiliki akses tertinggi pada aplikasi.

Admin dapat:

* Melihat seluruh pengguna.
* Melihat data marketplace.
* Melihat forum komunitas.
* Melihat data kebun.
* Mengakses dashboard metric.
* Mengelola atau melakukan moderasi data apabila diperlukan.
* Mengelola pengajuan merchant.
* Mengakses fungsi administratif lainnya.

### Admin Metrics

Dashboard admin dapat menampilkan informasi seperti:

* Jumlah pengguna.
* Jumlah Petani.
* Jumlah merchant.
* Jumlah produk.
* Jumlah posting.
* Jumlah transaksi atau aktivitas marketplace.
* Jumlah kebun yang terdaftar.

---

# 6. Matriks Hak Akses

| Fitur                     | Guest    | Petani | Petani - Penjual | Admin |
| ------------------------- | -------- | ------ | ---------------- | ----- |
| Melihat Marketplace       | ✅        | ✅      | ✅                | ✅     |
| Search Produk             | ✅        | ✅      | ✅                | ✅     |
| LLM Search                | ❌        | ✅      | ✅                | ✅     |
| Membaca Forum             | ✅        | ✅      | ✅                | ✅     |
| Membuat Post              | ❌        | ✅      | ✅                | ✅     |
| Like Post                 | ❌        | ✅      | ✅                | ✅     |
| Comment                   | ❌        | ✅      | ✅                | ✅     |
| Membeli Produk            | ❌        | ✅      | ✅                | -     |
| Membuat Produk            | ❌        | ❌      | ✅                | ✅     |
| Mengelola Etalase         | ❌        | ❌      | ✅                | ✅     |
| Melihat Peta              | Terbatas | ✅      | ✅                | ✅     |
| Dashboard Metric          | ❌        | ❌      | ❌                | ✅     |
| Kelola Pengguna           | ❌        | ❌      | ❌                | ✅     |
| Kelola Pengajuan Merchant | ❌        | ❌      | ❌                | ✅     |

---

# 7. Hubungan Antar Modul

Meskipun pengembangan dibagi berdasarkan modul, beberapa modul memiliki dependency satu sama lain.

```text
                   ┌─────────────────┐
                   │ Authentication  │
                   │   & Profile     │
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              ↓             ↓             ↓
         Community      Marketplace    Garden Map
           Forum         Discovery
                            │
                            ↓
                       LLM Search
```

### Auth → Forum

Forum membutuhkan data pengguna untuk mengetahui siapa pembuat post, komentar, dan like.

### Auth → Marketplace

Marketplace membutuhkan role pengguna untuk menentukan apakah pengguna hanya dapat membeli atau juga dapat menjual produk.

### Marketplace → LLM Search

LLM Search menggunakan katalog Marketplace sebagai sumber data pencarian.

### Marketplace → Map

Lokasi merchant atau lokasi pengambilan barang dapat ditampilkan pada Map.

### Map → Marketplace

Pengguna dapat menemukan merchant terdekat dan melihat produk yang ditawarkan oleh merchant tersebut.

---

# 8. Pembagian Modul Per Anggota

## 1. Adrian Nathanael Setiawan — 2506591053

**Modul:** Searching LLM

Tanggung jawab utama:

* Integrasi API LLM.
* Prompt processing.
* Natural language query parsing.
* Konversi prompt menjadi structured query.
* Integrasi hasil LLM dengan database marketplace.
* Fallback apabila model gagal memahami query.
* Menampilkan hasil pencarian dalam UI marketplace.

### Dokumentasi Modul Searching LLM

Kode modul berada di `llm_searching/`, template di `templates/llm_searching/`, dan interaksi halaman di `static/js/llm_search.js`. Pengguna **wajib login** untuk mengakses `/llm-search/` dan API job pencarian. Modul menggunakan **OpenRouter** dengan model **`google/gemma-3-27b-it:free`** untuk menerjemahkan bahasa natural menjadi filter terstruktur dan menyusun suggestion dari kandidat yang ditemukan.

#### Fitur yang tersedia

* **Pencarian bahasa natural:** nama produk, kategori, harga minimum/maksimum, lokasi, stok, jumlah hasil, serta urutan terbaru/harga termurah/harga tertinggi. Nama produk saja, seperti “carikan saya tomat”, sudah cukup; pengguna tidak wajib mengisi seluruh filter.
* **Pencarian kategori dan rekomendasi:** “sayuran termurah” menjadi kategori `sayuran` dengan `price_asc`. Backend mempertahankan urutan harga dari database agar suggestion tidak membalik urutan atau menghilangkan kandidat termurah.
* **Normalisasi bahasa:** menangani typo ringan yang jelas, variasi kapitalisasi, dan bentuk kategori seperti “buah buahan”. Keyword kategori yang redundan dihapus sebelum query, sementara nama spesifik seperti “buah naga” tetap dipertahankan.
* **Pemisahan kategori dan sifat produk:** “sayuran segar di sekitar depok” menjadi kategori `sayuran`, keyword `segar`, dan lokasi Depok. Kata “segar” dicocokkan pada nama/deskripsi; ini tidak membuktikan tanggal panen atau menjamin kualitas yang tidak diverifikasi.
* **Hasil berdasarkan katalog nyata:** kartu menampilkan foto, nama, harga/satuan, stok, kategori, lokasi, dan tautan `/marketplace/products/<id>/`. Produk arsip dikecualikan; stok nol diberi label Habis kecuali filter hanya-stok-tersedia diminta.
* **Status job tanpa reload:** halaman mempoll status setiap 2 detik. Status tampil dekat tombol pencarian; kartu bertambah ke bawah dan tinggi section mengikuti isi, sementara posisi area prompt tetap stabil.
* **Worker dengan pemulihan:** job disimpan di database, diproses paralel melalui RabbitMQ ketika broker sehat, dan beralih ke pemrosesan lokal serial saat broker tidak tersedia.

#### Env dan Script yang berkaitan dengan Modul

Buat atau perbarui `.env` dengan mengacu pada `.env.example`. Isi API key **sebelum menjalankan perintah Django**, karena konfigurasi aplikasi memeriksa keberadaannya saat startup:

```dotenv
OPENROUTER_API_KEY=isi_dengan_api_key_anda # strict env
LLM_RABBITMQ_URL= # optional env
LLM_WORKERS=4 
LLM_MAX_ACTIVE_JOBS=3
LLM_LEASE_SECONDS=180
```

Di terminal terpisah, jalankan worker:

```bash
source .venv/bin/activate
python manage.py run_llm_worker
```

Kemudian login melalui `/auth/login/` dan buka `/llm-search/`. **Worker tetap wajib berjalan ketika RabbitMQ tidak digunakan** agar job diproses. Jalankan satu proses coordinator per deployment; pool thread dikelola di dalam proses tersebut. Hentikan dengan `Ctrl+C`, lalu jalankan kembali setelah mengubah kode atau instruksi prompt. Untuk pengembangan tampilan, jalankan `npm run watch:css` di terminal lain.

#### Contoh prompt

| Prompt | Interpretasi yang diharapkan |
| --- | --- |
| `carikan saya tomat` | Keyword `tomat`, tanpa mengarang kategori, harga, atau lokasi |
| `cari tomat di Depok di bawah 30 ribu` | Keyword `tomat`, lokasi Depok, harga maksimum Rp30.000 |
| `rekomendasikan sayuran kepada saya dengan harga termurah` | Kategori `sayuran`, keyword kosong, urutan harga naik |
| `carikan saya buah buahan dibawah 70 roibu` | Kategori `buah`, keyword kosong, harga maksimum Rp70.000 |
| `tolong cariin tomta di dpok maksimal 30 ribu` | Normalisasi typo menjadi keyword `tomat`, lokasi Depok, batas harga tetap Rp30.000 |
| `sayuran segar di sekitar depok` | Kategori `sayuran`, keyword `segar`, lokasi Depok; kapitalisasi `Depok` tidak mengubah interpretasi |
| `cari tomat 3 kg dengan total maksimal Rp50.000` | Meminta klarifikasi karena perhitungan total anggaran berdasarkan berat belum didukung |

Harga filter selalu mengacu pada **harga tercantum per satuan produk**. Kata “murah” menentukan pengurutan, bukan menambahkan anggaran buatan. Koreksi typo hanya untuk maksud yang cukup jelas; model tetap dapat meminta klarifikasi ketika terdapat beberapa tafsir.

#### Alur pemrosesan dan keamanan

```text
Prompt pengguna login → job pending → worker
    → OpenRouter: ekstraksi filter JSON
    → validasi dan normalisasi backend
    → SELECT produk/kategori marketplace
    → suggestion dari kandidat hasil query
    → simpan hasil/status → polling browser → kartu produk
```

Adapter `llm_searching/marketplace.py` membaca model `Product` dan `Category` lokal sesuai [kontrak marketplace](llm_searching/docs/api_contract.pdf). Model tidak menghasilkan SQL yang dieksekusi langsung dan tidak menerima seluruh katalog untuk difilter. Jalur query pencarian memakai proyeksi field eksplisit, tanpa membaca tabel akun, transaksi, atau ulasan; nama merchant belum ditampilkan pada kartu LLM.

Backend memvalidasi nama field, tipe, rentang harga, kategori, sort, dan limit. ID suggestion harus berasal dari kandidat database dan alasannya harus didukung fakta produk. API menggunakan sesi login, CSRF untuk POST, pemeriksaan pemilik job, dan rendering teks yang di-escape. Kredensial tetap di server.

#### Konfigurasi dan worker

| Variabel/batas | Default | Keterangan |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | Wajib diisi | Kunci server untuk OpenRouter |
| `LLM_RABBITMQ_URL` | Kosong | Kosong memakai fallback lokal; isi URL AMQP untuk menggunakan RabbitMQ |
| `LLM_WORKERS` | 4 | Thread paralel saat broker sehat; dibatasi 1–16 |
| `LLM_MAX_ACTIVE_JOBS` | 3 | Maksimum job pending/processing per pengguna |
| `LLM_LEASE_SECONDS` | 180 detik | Minimum 180 detik; token dan expiry memagari penyimpanan hasil |
| Panjang prompt | Maksimum 500 kata dan 5.000 karakter termasuk spasi | Penghitung kata dan pesan validasi pada textarea serta validasi backend; request JSON maksimum 12.000 byte |
| Jumlah hasil | Default 20, maksimum 50 | Dibatasi sebelum mengambil hasil database |

Pada SQLite, gunakan `LLM_WORKERS=1` bila memakai broker untuk mengurangi konflik writer; PostgreSQL lebih sesuai untuk concurrency produksi. RabbitMQ memakai antrean durable dan pesan berisi ID job. Jika broker mati, coordinator menunggu pekerjaan paralel yang sedang berjalan selesai, kemudian memproses job secara serial. Reconnect memakai backoff dan pool dipulihkan otomatis saat broker kembali sehat.

Job terminal tidak diproses ulang; token lease mencegah worker lama menimpa hasil. Crash setelah panggilan OpenRouter tetapi sebelum hasil disimpan masih dapat menyebabkan panggilan API ulang. Untuk memeriksa satu siklus worker, gunakan `python manage.py run_llm_worker --once`.

#### Halaman dan API

| Method | URL | Hasil |
| --- | --- | --- |
| GET | `/llm-search/` | Halaman pencarian; Guest diarahkan login |
| POST | `/llm-search/api/jobs/` | JSON `{"prompt":"carikan saya tomat"}` dengan CSRF; respons 202 berisi `id`, `status`, dan `status_url` |
| GET | `/llm-search/api/jobs/<uuid>/` | Status/hasil job milik pengguna yang sedang login |

Status job: `pending`, `processing`, `succeeded`, `needs_clarification`, atau `failed`. Hasil terminal memuat filter, produk, penjelasan, dan penanda `degraded`. API mengembalikan 400 untuk input salah, 401 untuk Guest, 403 untuk CSRF, 404 untuk job yang tidak tersedia/bukan milik pengguna, dan 429 jika kuota job aktif tercapai.

#### Fallback dan batasan

* Hasil kosong atau syarat di luar kemampuan meminta klarifikasi; sistem tidak diam-diam menghapus syarat atau melonggarkan harga/lokasi.
* Total harga berdasarkan jumlah/berat, tanggal panen, pengecualian, OR kompleks, dan pencarian radius/jarak terdekat belum didukung. “Sekitar Depok” memakai filter teks lokasi, bukan perhitungan GPS.
* Kegagalan interpretasi OpenRouter menghasilkan pesan aman dan tautan marketplace. Kegagalan tahap suggestion tetap menampilkan hasil query beserta penjelasan berdasarkan data, dengan `degraded=true`.
* Dependency marketplace yang belum tersedia atau tidak sesuai kontrak menghasilkan `marketplace_unavailable`, bukan dianggap hasil kosong.
* Job menyimpan prompt dan hasil untuk pemrosesan/polling. Jadwalkan `python manage.py cleanup_llm_jobs` untuk menghapus job terminal yang selesai lebih dari 24 jam lalu; job aktif tidak dihapus oleh command ini.

#### Pengujian dan dokumentasi lanjutan

```bash
python manage.py test llm_searching
python manage.py check
ruff check . --exclude migrations
```

Tes mencakup validasi filter, pembatasan query baca, grounding suggestion, urutan harga, akses dan CSRF, lease job, broker/fallback, deadline provider, serta render template. Tes PostgreSQL khusus concurrency dilewati pada SQLite. Evaluasi prompt terhadap model asli bersifat opt-in dan memakai kuota OpenRouter:

```bash
LLM_RUN_LIVE_TESTS=1 python manage.py test llm_searching.tests.test_live_prompts
```

Runbook, kontrak adapter, serta detail operasional tersedia di [docs/llm-search.md](docs/llm-search.md). Desain, plan, dan bukti pengerjaan tersimpan di [docs/superpowers](docs/superpowers/).

## AI Disclosure
Saya menggunakan llm untuk membatu saya dalam membatu saya menulis code dan membentuk prompt engineering dalam mengirimkan request ke llm pencarian. tujuan prompt engineeringnya adalam memastikan bahwa LLM yang digunakan tidak menjawab sesuatu yang berada di luar context marketplace searching. 

Sebelum llm mulai menulis code, saya membuatkan dokumen spec dan juga execution plan sehingga llm tidak bekerja dengan contract yang mengada-ada. AI yang menulis code ini juga melakukan pengerjaan dengan flow tdd dengan evidence red commit, green commit, dan refactor commit. 

perbaikan manual dilakukan untuk bagian design searching page yang designnya terlalu generic dan sulit dibaca, serta ux dan interaksi dengan pengguna yang sangat minim.

Seperti saat assignment, AI memang sangat membantu dalam pengerjaan backend, tetapi masih perlu perbaikan manual dalam pengerjaan UI. 

Model yang digunakan: GPT-6.1-Sol (medium)

---

## 2. Khairani Hanifah Putri — 2506587371

**Modul:** Forum Komunitas

Tanggung jawab utama:

* Membuat halaman community feed.
* Create post.
* Edit post.
* Delete post.
* Like.
* Unlike.
* Comment.
* Integrasi data post dengan profil pengguna.
* Validasi batas maksimal posting.

---

## 3. Adriana Ainurrahmah Damanik — 2506656375

**Modul:** Marketplace Discovery

Tanggung jawab utama:

* Product catalog.
* Product card.
* Product detail.
* Search produk.
* Filter kategori.
* Filter lokasi.
* Filter harga.
* Data stok.
* Integrasi marketplace dengan merchant.
* Menyediakan endpoint/data yang dibutuhkan modul LLM Search.

### Dokumentasi Modul Marketplace

Kode modul berada di app `marketplace/` dengan template di `templates/marketplace/`. Tampilan memakai design system tim (`static/css/input.css`).

#### Menjalankan dengan data contoh

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_marketplace
npm run build:css
python manage.py runserver
```

`seed_marketplace` mengisi 5 kategori, 18 produk dengan foto contoh dari Wikimedia Commons (lisensi terbuka, kredit tercantum di file seed), serta akun demo lokal berikut:

| Peran | Username | Password |
| --- | --- | --- |
| Petani - Penjual | `petani_penjual` | `petani-123!` |
| Petani - Penjual | `kebun_sinta` | `sinta-123!` |
| Pembeli | `pembeli_demo` | `pembeli-123!` |

#### Model data

| Model | Field utama |
| --- | --- |
| `Category` | `name`, `slug`, `description` |
| `Product` | `seller` (FK ke `User`), `category`, `name`, `description`, `image`, `image_url`, `price` (Rupiah per satuan), `unit`, `stock`, `min_order`, `harvested_at`, `location`, `pickup_address`, `pickup_notes`, `latitude`, `longitude`, `is_active`, `created_at`, `updated_at` |
| `ProductImage` | `product`, `image`, `position` (maksimal 4 foto tambahan per produk) |
| `CartItem` | `user`, `product`, `quantity`, `selected` |
| `Order` | `buyer`, `seller`, `status`, `note`, `cancel_reason`, `total`, `created_at`, `updated_at` |
| `OrderItem` | `order`, `product`, `product_name`, `price`, `quantity`, `pickup_location` (salinan saat checkout) |
| `Review` | `order_item`, `product`, `buyer`, `rating` (1–5), `comment` |

#### Halaman

| URL | Akses | Fungsi |
| --- | --- | --- |
| `/marketplace/` | Publik | Katalog: cari, filter kategori (bisa lebih dari satu), harga, lokasi, stok, urutan, mode **Daftar / Peta** |
| `/marketplace/products/<id>/` | Publik | Detail produk: galeri, harga per satuan, rating, terjual, peta titik ambil, ulasan, produk terkait |
| `/marketplace/sellers/<username>/` | Publik | Halaman toko: rating, terjual, cari dan urutkan di dalam toko |
| `/marketplace/my-products/` | Petani - Penjual | Kelola produk: tambah, edit, arsipkan, tampilkan lagi, hapus permanen |
| `/marketplace/products/new/`, `/products/<id>/edit/` | Petani - Penjual (pemilik) | Form produk dengan foto, harga per satuan, minimal beli, dan titik pengambilan di peta |
| `/marketplace/cart/` | Login | Keranjang per toko, pilih item, checkout |
| `/marketplace/orders/` | Login | Pesanan saya dan detail pesanan |
| `/marketplace/sales/` | Petani - Penjual | Pesanan masuk |

#### API JSON (untuk modul LLM Search dan Peta)

| Endpoint | Keterangan |
| --- | --- |
| `GET /marketplace/api/search/` | Pencarian produk aktif. Parameter: `q`/`keyword`, `category` (slug atau nama, bisa berulang), `price_range` (`under-10k`, `10k-25k`, `25k-50k`, `over-50k`), `min_price`, `max_price`, `location`, `in_stock`, `sort` (`relevance`, `newest`, `price_asc`, `price_desc`), `limit` (maks. 50). Mengembalikan `params`, `count`, `results` |
| `GET /marketplace/api/products/<id>/` | Detail satu produk aktif: field yang sama dengan item pencarian, ditambah `url`, `gallery`, `pickup_address`, `pickup_notes`, `harvested_at`, `sold_count`, `rating_avg`, `rating_count`. Produk tidak ada atau diarsipkan menghasilkan `404` |

Seluruh hasil berasal dari database katalog (grounded). Parameter yang tidak valid diabaikan, bukan menimbulkan error. Fungsi yang sama tersedia untuk dipanggil langsung dari Python: `marketplace.services.search_products(params)`.

#### Alur pesanan

1. Pembeli menambahkan produk ke keranjang (jumlah mengikuti stok dan minimal pembelian) atau memakai **Beli sekarang**.
2. Checkout membuat **satu pesanan per penjual** dan mengurangi stok secara atomik.
3. Penjual: **Menunggu konfirmasi → Disiapkan → Siap diambil → Selesai**. Penjual dapat menolak pesanan selama belum siap diambil.
4. Pembeli dapat membatalkan selama pesanan belum dikonfirmasi, dan menekan **Pesanan diterima** saat siap diambil.
5. Setelah selesai, pembeli dapat memberi ulasan satu kali per produk. Pembatalan mengembalikan stok.

Pembayaran dilakukan saat pengambilan; pembayaran online berada di luar scope awal.

#### Hak akses

* Guest dapat melihat katalog, detail, dan halaman toko.
* Pengguna login dapat membeli, melihat pesanannya, dan memberi ulasan.
* Hanya `Petani - Penjual` (dan admin) yang dapat mengelola produk, dan hanya produk miliknya.
* Penjual tidak dapat membeli produknya sendiri. Pesanan hanya dapat dilihat dan diubah oleh pembeli dan penjualnya.

#### Layanan eksternal

* Peta: Leaflet dengan tile OpenStreetMap dan citra satelit Esri.
* Pencarian alamat dan pengisian alamat otomatis: Nominatim (OpenStreetMap).

#### Pengujian

```bash
python manage.py test marketplace
```

#### Ketergantungan dengan modul lain

* **Autentikasi (Vania):** `Product.seller` sementara merujuk ke `User`. Setelah model `Merchant` tersedia, nama toko dan etalase akan memakai data merchant.
* **Peta Kebun (Wisnu):** produk menyimpan `latitude`/`longitude`. Urutan berdasarkan jarak terdekat menunggu layanan jarak dari modul peta.
* **LLM Search (Adrian):** memakai adapter baca `llm_searching/marketplace.py` untuk mencari model produk/kategori lokal sesuai kontrak marketplace, sehingga hasil tetap berasal dari katalog.

#### Catatan deployment

Foto yang diunggah disimpan di `media/` dan hanya disajikan otomatis saat `DEBUG=True`. Untuk lingkungan produksi diperlukan penyimpanan media terpisah; sementara itu produk dapat memakai URL foto.

#### AI Disclosure

Dalam pengerjaan modul ini saya menggunakan asisten AI untuk membantu menganalisis alur marketplace, menyusun rancangan, menulis sebagian kode dan pengujian, serta meninjau tampilan. Seluruh hasil telah saya periksa, jalankan, uji, dan sesuaikan dengan kebutuhan proyek, dan saya bertanggung jawab atas kode yang dikumpulkan.

---

## 4. Vania Apsari Nailah Putri Difa — 2506615103

**Modul:** Autentikasi & Pengguna

Tanggung jawab utama:

* Registrasi.
* Login.
* Logout.
* Password validation.
* Profile management.
* Role-based access control.
* Petani role.
* Merchant/Penjual role.
* Admin role.
* Proses pengajuan menjadi penjual.

---

## 5. Muhammad Wisnu Jaya Wardana — 2506615236

**Modul:** Peta Kebun

Tanggung jawab utama:

* Integrasi API atau library peta.
* Menampilkan marker kebun.
* Mengelola koordinat lokasi.
* User geolocation.
* Perhitungan jarak.
* Pencarian kebun terdekat.
* Informasi detail lokasi.
* Integrasi lokasi merchant dengan marketplace.

---

# 9. Contoh User Flow

## Flow Registrasi

```text
Landing Page
    ↓
Register
    ↓
Input Email + Password
    ↓
Validasi
    ↓
Account Created
    ↓
Login
    ↓
Home
```

## Flow Membeli Produk

```text
Home
    ↓
Marketplace
    ↓
Search / Filter
    ↓
Product Detail
    ↓
Pilih Produk
    ↓
Purchase Flow
```

## Flow LLM Search

```text
Marketplace
    ↓
LLM Search
    ↓
"Sayur murah di bawah 20 ribu"
    ↓
LLM Processing
    ↓
Structured Query
    ↓
Database Search
    ↓
Matching Products
    ↓
Marketplace Display
```

## Flow Menjadi Penjual

```text
Petani
    ↓
Ajukan Menjadi Penjual
    ↓
Pengajuan
    ↓
Admin Review
    ↓
Approved
    ↓
Petani - Penjual
    ↓
Create Merchant
    ↓
Create Product
```

## Flow Mencari Kebun Terdekat

```text
User
    ↓
Buka Map
    ↓
Allow Location
    ↓
Ambil GPS
    ↓
Hitung Jarak
    ↓
Urutkan Kebun
    ↓
Tampilkan Kebun Terdekat
```

---

# 10. Batasan Scope Awal

Agar pengembangan proyek tetap realistis, beberapa fitur dapat ditempatkan di luar scope awal.

Fokus utama versi awal:

1. Authentication dan profile.
2. Community post.
3. Product discovery.
4. LLM-based search.
5. Garden map.
6. Role Petani dan Merchant.
7. Basic admin functionality.

Beberapa fitur lanjutan yang dapat dikembangkan setelah fitur utama selesai antara lain:

* Sistem pembayaran online.
* Delivery tracking.
* Chat langsung antara pembeli dan penjual.
* Rating dan review merchant.
* Moderasi konten otomatis.
* Recommendation system.
* Notifikasi real-time.
* Sistem reward yang lebih kompleks.
* Analisis statistik hasil panen.
* Integrasi cuaca untuk kebun.
* Recommendation tanaman berdasarkan lokasi.

---

# 11. Kesimpulan

**Urban Harvest Community** dirancang sebagai platform yang menghubungkan tiga kebutuhan utama dalam ekosistem urban farming:

**Community + Marketplace + Location**

Forum membangun interaksi antarpengguna, marketplace membantu distribusi hasil pertanian, sedangkan peta membantu menghubungkan aktivitas tersebut dengan lokasi nyata.

Fitur **LLM Search** menjadi nilai tambah aplikasi karena memungkinkan pengguna mencari komoditas menggunakan bahasa sehari-hari tanpa harus memahami struktur filter marketplace.

Arsitektur fitur dibuat modular sehingga setiap anggota dapat mengembangkan modul secara terpisah, tetapi tetap terhubung melalui kontrak data dan API yang disepakati bersama.

## Implementasi LLM Search

Panduan fitur, setup, worker, contoh prompt, API, dan pengujian tersedia pada
[Dokumentasi Modul Searching LLM](#dokumentasi-modul-searching-llm) di bagian modul
Adrian. Runbook detail tersedia di [docs/llm-search.md](docs/llm-search.md).
