# Urban Harvest Community

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

Buka `http://127.0.0.1:8000/` untuk melihat halaman **Hello world!**. Selama mengubah kelas Tailwind di template, jalankan `npm run watch:css` di terminal lain agar CSS dibangun ulang otomatis.

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
  "category": "sayuran",
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
* Jumlah produk.
* Preferensi lainnya.

Contoh:

> "Cari bibit cabai maksimal Rp25.000."

Dapat diterjemahkan menjadi:

```json
{
  "product": "bibit cabai",
  "max_price": 25000
}
```

### Database Grounding

LLM tidak berfungsi sebagai sumber data marketplace.

LLM hanya menginterpretasikan permintaan.

Data hasil pencarian harus berasal dari database aplikasi.

Hal ini penting untuk menghindari kasus ketika LLM memberikan rekomendasi produk yang sebenarnya tidak tersedia.

### Result Display

Setelah query database selesai, hasil ditampilkan menggunakan komponen marketplace yang sama dengan pencarian reguler.

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

Apabila LLM gagal memahami permintaan pengguna, sistem dapat:

* Memberikan pesan bahwa pencarian tidak dapat dipahami.
* Menggunakan keyword dari prompt sebagai pencarian biasa.
* Meminta pengguna memperjelas kebutuhan.

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
| LLM Search                | Terbatas | ✅      | ✅                | ✅     |
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
