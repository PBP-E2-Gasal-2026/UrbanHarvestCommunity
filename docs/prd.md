# Product Requirements Document — Urban Harvest Community

**Versi:** 1.0  
**Status:** Rancangan pengembangan  
**Sumber utama:** [README proyek](../README.md)  
**Cakupan rilis:** MVP lima modul inti

## 1. Ringkasan produk

Urban Harvest Community adalah platform web untuk menghubungkan petani urban, warga, komunitas, dan calon pembeli. Produk ini menyatukan forum berbagi pengetahuan, katalog hasil dan kebutuhan pertanian, pencarian komoditas dengan bahasa sehari-hari, serta peta kebun dan titik pengambilan. Tujuan rilis awal adalah membuat informasi komunitas, produk, dan lokasi dapat ditemukan dari satu tempat.

Dokumen ini menerjemahkan rencana pada README menjadi kebutuhan yang dapat dikerjakan dan diperiksa. Fitur yang disebut sebagai **MVP** adalah target rilis awal; bagian **lanjutan** adalah arah pengembangan, bukan janji pada rilis awal. Implementasi repo saat ini baru berupa halaman awal Django dengan Tailwind CSS v4.

### 1.1 Masalah pengguna

- Informasi kebun, komunitas, dan hasil panen tersebar di tempat berbeda.
- Calon pembeli sulit menemukan produk lokal berdasarkan kebutuhan, harga, stok, dan lokasi.
- Petani urban membutuhkan tempat untuk berbagi pengalaman serta menawarkan produk.
- Pencarian dengan kata kunci kaku tidak selalu cocok dengan cara pengguna menjelaskan kebutuhan.

### 1.2 Tujuan dan hasil yang diharapkan

1. Pengunjung dapat menemukan produk dan kebun tanpa harus membuat akun.
2. Anggota dapat berdiskusi dan mengelola identitasnya.
3. Penjual yang disetujui dapat menampilkan dan menjaga data produk yang akurat.
4. Pengguna terdaftar dapat mencari produk dengan bahasa natural; hasil selalu berasal dari katalog.
5. Pengguna dapat memahami lokasi kebun, merchant, dan titik pengambilan.

**Ukuran keberhasilan awal:** seluruh alur utama pada §4 dapat diselesaikan; daftar produk tidak menampilkan data fiktif; tindakan tulis mengikuti hak akses; pencarian biasa tetap berfungsi saat layanan LLM gagal; peta tetap bisa dijelajahi tanpa izin lokasi. Belum ada target angka trafik atau konversi yang ditetapkan dalam README.

## 2. Pengguna dan ruang lingkup

| Peran | Kebutuhan utama | Akses MVP |
| --- | --- | --- |
| Guest | Membaca informasi dan mengeksplorasi produk/kebun | Halaman publik, katalog, detail produk, forum baca, peta publik, pencarian biasa |
| Petani | Berpartisipasi dan mencari produk | Akses Guest, profil, post/like/komentar, pencarian LLM, detail peta lengkap, pengajuan penjual |
| Petani–Penjual | Memasarkan hasil atau kebutuhan pertanian | Akses Petani, etalase dan manajemen produk/stok |
| Admin | Menjaga data dan hak akses | Tinjau pengajuan penjual, kelola data inti dan ringkasan metrik |

**Keputusan cakupan MVP:** istilah “membeli produk” pada README diperlakukan sebagai niat pengguna untuk menemukan produk dan lokasi/kontak penjual. Checkout, pembayaran, pesanan, dan transaksi belum masuk MVP karena README menempatkan marketplace pada *product discovery* dan pembayaran online di luar cakupan awal. Jika transaksi menjadi kebutuhan rilis, alur dan datanya perlu PRD tersendiri.

**Cakupan lanjutan:** poin kontribusi, pengurutan berdasarkan jarak untuk produk, moderasi otomatis, pembayaran, pelacakan pengiriman, chat, rating/review, rekomendasi, notifikasi waktu nyata, analitik panen, integrasi cuaca, dan rekomendasi tanaman.

## 3. Prinsip produk dan aturan bersama

- Halaman baca publik tersedia tanpa login. Aksi membuat, mengubah, menghapus, menyukai, dan berkomentar memerlukan akun sesuai izin.
- Otorisasi diperiksa di server untuk setiap aksi, termasuk saat pengguna memanggil URL secara langsung.
- Data katalog dan lokasi berasal dari database aplikasi. LLM hanya menafsirkan permintaan menjadi filter terstruktur.
- Lokasi pengguna digunakan hanya setelah izin browser diberikan. Penolakan izin tidak menghalangi peta dasar.
- Antarmuka memakai Django template dan Tailwind CSS v4 sesuai setup repo; URL, formulir, dan data dimiliki oleh modul masing-masing.
- Pesan kesalahan harus menjelaskan tindakan yang dapat dilakukan pengguna, termasuk input tidak valid, hasil kosong, dan layanan eksternal gagal.

## 4. Alur utama dan kriteria produk

| Alur | Langkah pengguna | Hasil yang diharapkan |
| --- | --- | --- |
| Daftar dan masuk | Daftar → isi nama/email/password → masuk | Akun Petani dibuat; pengguna diarahkan ke halaman yang relevan |
| Berpartisipasi | Masuk → buka forum → buat post → like/komentar | Post tampil di feed dan interaksi tercatat satu kali per pengguna |
| Temukan produk | Buka katalog → cari/filter → buka detail | Produk aktif yang sesuai tampil bersama harga, stok, merchant, dan lokasi |
| Cari dengan LLM | Masuk → tulis kebutuhan → lihat hasil | Prompt diubah menjadi filter tervalidasi; hasil memakai kartu katalog yang sama |
| Menjadi penjual | Petani mengajukan → admin meninjau → disetujui → buat etalase/produk | Hak akses penjual aktif hanya setelah persetujuan |
| Temukan kebun | Buka peta → pilih marker; opsional izinkan lokasi | Detail kebun tampil; jarak dan urutan terdekat tersedia jika lokasi diberikan |

## 5. Spesifikasi modul

### 5.1 Autentikasi, profil, dan peran

**Tujuan:** menyediakan identitas pengguna dan menjadi sumber hak akses bagi modul lain.

**MVP dan pengembangan:**

1. Registrasi meminta nama, email unik, dan password minimal 8 karakter dengan sedikitnya satu karakter khusus. Password disimpan memakai mekanisme hashing Django.
2. Login menggunakan email dan password; logout mengakhiri sesi. Pesan gagal tidak membocorkan apakah email terdaftar.
3. Pengguna baru memperoleh peran Petani. Guest adalah kondisi belum login; Admin dikelola melalui hak administratif.
4. Profil dapat dilihat dan diedit oleh pemiliknya: nama, foto, bio, lokasi, informasi komunitas. Informasi merchant tampil setelah pengguna menjadi penjual.
5. Petani dapat mengajukan status penjual. Pengajuan memiliki status `pending`, `approved`, atau `rejected`; hanya Admin yang dapat mengubah status akhir. Pengajuan berulang yang masih `pending` ditolak.
6. Penjual yang telah disetujui dapat membuat atau memperbarui profil merchant/etalase. Hak akses penjual tidak cukup diperoleh dengan mengubah formulir atau URL di klien.

**Data inti:** `User` (id, nama, email, password hash, status aktif), `Profile` (foto, bio, lokasi, komunitas), `SellerApplication` (pemohon, status, waktu, catatan admin), `Merchant` (pemilik, nama, deskripsi, lokasi/kontak yang boleh tampil). Bentuk model final ditetapkan saat implementasi; relasi harus memungkinkan satu pengguna memiliki satu profil dan satu status pengajuan aktif.

**Antarmuka modul:** halaman daftar/masuk/keluar, halaman profil, formulir pengajuan, antrean tinjauan Admin, serta fungsi pemeriksaan peran yang dipakai forum dan marketplace.

**Spesifikasi singkat / selesai bila:** email duplikat dan password lemah ditolak; akun baru bisa masuk sebagai Petani; pemilik hanya mengubah profilnya; akses penjual aktif sesudah persetujuan Admin; pengguna tanpa izin mendapat respons akses ditolak atau diarahkan masuk.

### 5.2 Forum komunitas

**Tujuan:** menyediakan ruang berbagi pengalaman, pertanyaan, dan informasi urban farming.

**MVP dan pengembangan:**

1. Feed publik menampilkan post terbaru beserta penulis, waktu, isi, jumlah like, dan jumlah komentar; daftar diberi pagination agar tetap nyaman dibaca.
2. Petani dan Penjual dapat membuat post teks hingga **1000 kata**, lalu mengedit atau menghapus post miliknya. Waktu pembuatan dan pembaruan disimpan.
3. Pengguna login dapat like/unlike post. Satu pasangan pengguna–post hanya memiliki satu like aktif.
4. Pengguna login dapat menambah komentar teks. Komentar mengacu pada post dan penulis; komentar kosong ditolak.
5. Guest hanya membaca. Konten pengguna ditampilkan sebagai teks yang di-escape agar HTML berbahaya tidak dieksekusi.
6. Admin dapat menghapus konten yang melanggar aturan melalui kemampuan administratif dasar; penyaringan otomatis di luar MVP.

**Data inti:** `Post` (penulis, isi, dibuat, diperbarui), `PostLike` (post, pengguna, dibuat; unik per pasangan), `Comment` (post, penulis, isi, dibuat). Jumlah like/komentar dihitung dari relasi atau disinkronkan secara aman.

**Antarmuka modul:** feed, detail/daftar komentar, formulir buat/edit, aksi hapus dan like; semua aksi perubahan memakai metode HTTP yang sesuai dan perlindungan CSRF.

**Spesifikasi singkat / selesai bila:** post 1001 kata ditolak; post baru muncul di feed; pemilik dapat edit/hapus dan pengguna lain tidak; like dua kali kembali ke kondisi awal; Guest tidak dapat menulis atau berinteraksi.

### 5.3 Marketplace discovery dan merchant

**Tujuan:** membantu pengguna menemukan produk lokal yang tersedia serta memberi Penjual cara memelihara katalog.

**MVP dan pengembangan:**

1. Katalog publik menampilkan produk aktif dengan foto, nama, harga dalam rupiah, stok, kategori, lokasi, dan nama merchant. Detail menampilkan deskripsi dan informasi titik pengambilan bila tersedia.
2. Pencarian biasa mencocokkan nama/keyword produk. Filter kategori, rentang harga, lokasi, dan ketersediaan stok dapat digabungkan; input filter tidak valid ditangani tanpa galat server.
3. Pengurutan MVP meliputi terbaru dan harga naik/turun. Urutan berdasarkan jarak menunggu lokasi produk/merchant yang konsisten.
4. Penjual hanya dapat membuat, mengubah, menyembunyikan, dan menghapus produk milik merchant sendiri. Harga harus tidak negatif; stok berupa bilangan bulat tidak negatif.
5. Stok nol diberi label **Habis** dan tidak dianggap tersedia. Secara bawaan produk tetap dapat ditemukan agar statusnya jelas; filter “tersedia” mengecualikannya.
6. Etalase menampilkan informasi merchant dan produk aktifnya. Produk dapat ditautkan ke lokasi merchant atau titik pengambilan pada peta.

**Data inti:** `Category`, `Product` (merchant, kategori, nama, deskripsi, foto, harga, stok, status aktif, lokasi/titik pengambilan, dibuat, diperbarui), dan `Merchant` dari modul akun. Data produk memiliki identitas stabil agar hasil LLM dan tautan peta mengarah ke detail yang sama.

**Antarmuka modul:** katalog, detail, etalase, formulir kelola produk, dan layanan pencarian internal yang menerima keyword/filter terstruktur. Layanan pencarian ini dipakai ulang oleh pencarian LLM.

**Spesifikasi singkat / selesai bila:** Guest dapat melihat katalog/detail; kombinasi filter menghasilkan produk yang tepat; stok nol diberi status Habis; hanya pemilik merchant atau Admin dapat mengubah listing; tidak ada alur checkout atau pembayaran pada MVP.

### 5.4 Pencarian komoditas berbasis LLM

**Tujuan:** menerjemahkan kebutuhan dalam bahasa sehari-hari menjadi pencarian terhadap katalog nyata.

**MVP dan pengembangan:**

1. Pengguna login menulis prompt, misalnya “cari bibit cabai maksimal Rp25.000”. Guest menggunakan pencarian biasa; batas penggunaan Guest untuk LLM pada README belum ditentukan, sehingga akses LLM MVP dibatasi pada pengguna login.
2. Backend mengirim prompt ke OpenRouter sebagai penyedia yang direncanakan. Kunci API hanya berada di konfigurasi server, bukan template atau JavaScript browser.
3. Respons model dinormalisasi ke skema filter yang diizinkan: keyword/produk, kategori, harga minimum/maksimum, lokasi, dan stok. Nilai salah tipe, harga negatif, rentang terbalik, atau kategori tak dikenal ditolak atau diabaikan dengan pesan yang jelas.
4. Backend menjalankan filter melalui layanan katalog; LLM tidak boleh menambah produk, menghasilkan ID produk sebagai sumber kebenaran, atau menampilkan rekomendasi di luar hasil database.
5. Hasil memakai kartu katalog biasa dan menampilkan ringkasan filter yang ditafsirkan agar pengguna bisa memperbaiki pencarian.
6. Jika layanan gagal, timeout, atau respons tidak valid, sistem menawarkan pencarian keyword biasa dari prompt dan menjelaskan bahwa pencarian cerdas sedang tidak tersedia.

**Data/kontrak inti:** input `prompt` teks; output internal `SearchFilters` dengan field yang tervalidasi; output layar berupa daftar `Product` dari modul marketplace. Log operasional tidak menyimpan kunci API dan membatasi pencatatan prompt yang mungkin memuat data pribadi.

**Antarmuka modul:** formulir pencarian natural di marketplace, adapter OpenRouter, parser/validator respons, dan pemanggil layanan katalog. Pemilihan model, batas prompt, timeout, dan batas pemakaian dikonfigurasi saat implementasi sesuai anggaran layanan.

**Spesifikasi singkat / selesai bila:** prompt contoh menghasilkan filter harga dan komoditas yang benar; produk hasil selalu ada di katalog; kegagalan OpenRouter tidak mematikan pencarian biasa; respons model yang tidak sesuai skema tidak dieksekusi sebagai query mentah.

### 5.5 Peta kebun dan lokasi

**Tujuan:** memperlihatkan kebun urban, komunitas, merchant, dan titik pengambilan serta membantu pengguna menemukannya.

**MVP dan pengembangan:**

1. Peta publik menampilkan marker lokasi aktif. Klik marker membuka nama, jenis lokasi, deskripsi singkat, alamat, foto jika ada, dan tautan detail terkait.
2. Data lokasi mencakup kebun komunitas, kebun petani, merchant, dan titik pengambilan. Koordinat latitude/longitude divalidasi sebelum disimpan.
3. Informasi kontak dan detail lokasi mengikuti izin publikasi pemilik; Guest melihat ringkasan publik, sedangkan pengguna login dapat melihat detail yang memang diizinkan.
4. Browser meminta izin lokasi hanya saat pengguna memilih fitur “dekat saya”. Bila izin diberikan, daftar lokasi dapat diurutkan berdasarkan jarak dan menampilkan jarak perkiraan. Bila ditolak/tidak tersedia, peta dan pencarian manual tetap berfungsi.
5. Marker merchant atau titik pengambilan dapat membuka etalase atau produk terkait; halaman detail produk dapat membuka lokasi yang sama pada peta.
6. Penyedia peta, sumber tile, dan ketentuan pemakaiannya ditetapkan sebelum implementasi peta; modul harus tetap mengelola lokasi di database sendiri.

**Data inti:** `Location` (jenis, nama, koordinat, alamat, deskripsi, foto, pemilik/merchant, status aktif, visibilitas kontak) dan relasi opsional ke produk/merchant. Koordinat pengguna bersifat sementara untuk perhitungan jarak dan tidak perlu disimpan pada MVP.

**Antarmuka modul:** halaman peta, data marker, detail lokasi, fungsi jarak/urutan, tautan dua arah dengan marketplace.

**Spesifikasi singkat / selesai bila:** marker aktif tampil di posisi yang benar; marker membuka detail; izin lokasi ditolak tidak menyebabkan halaman gagal; urutan “dekat saya” memakai koordinat pengguna yang diberikan; tautan dari produk membuka lokasi terkait.

### 5.6 Administrasi dasar

Administrasi adalah kemampuan lintas modul, bukan modul produk terpisah pada pembagian kerja README. Admin meninjau pengajuan penjual, mengelola data pengguna/produk/lokasi, dan dapat menghapus konten forum. Dashboard ringkas menampilkan jumlah pengguna, penjual, produk, post, dan kebun. Metrik transaksi hanya tersedia bila modul transaksi kelak dibangun. Aksi admin harus tercatat dengan pelaku dan waktu bila mengubah status pengajuan atau menghapus konten.

**Selesai bila:** non-Admin tidak dapat mengakses aksi administratif; keputusan pengajuan tercermin pada hak akses penjual; metrik dihitung dari data aplikasi dan tidak menampilkan angka transaksi palsu.

## 6. Hubungan modul dan kontrak integrasi

| Penyedia | Pemakai | Kontrak minimum |
| --- | --- | --- |
| Akun | Forum | ID pengguna, nama/foto publik, status login |
| Akun | Marketplace | Identitas merchant, status persetujuan penjual, izin mengubah produk |
| Marketplace | LLM Search | Fungsi pencarian dengan filter tervalidasi dan keluaran daftar produk |
| Marketplace | Peta | ID merchant/produk dan ID lokasi terkait |
| Peta | Marketplace | Koordinat/alamat dan tautan detail lokasi/etalase |
| Semua modul | Admin | Data ringkasan dan aksi administratif sesuai peran |

**Urutan dependensi:** fondasi akun dan kontrak data → forum/marketplace/peta secara paralel setelah kontraknya jelas → LLM Search setelah layanan pencarian katalog tersedia → integrasi, akses, dan administrasi.

## 7. Arsitektur pengembangan

- **Backend dan render:** Django; app dapat dipisah per domain saat modul dikembangkan. Template global berada di `templates/`, aset di `static/`.
- **Tampilan:** Tailwind CSS v4; sumber gaya `static/css/input.css`, hasil build `static/css/style.css`. Komponen halaman menjaga pola `base.html` dan blok konten.
- **Penyimpanan:** model relasional Django untuk akun, forum, katalog, dan lokasi. Database pengembangan boleh SQLite; database produksi harus dipilih dan disiapkan sesuai lingkungan deploy.
- **Integrasi eksternal:** OpenRouter untuk interpretasi prompt; penyedia peta belum diputuskan. Keduanya berada di balik adapter agar kegagalan eksternal tidak merusak fungsi dasar.
- **Konfigurasi:** kredensial API, secret Django, host, database, dan mode debug melalui variabel lingkungan saat deployment; tidak ditaruh di repo.
- **Akses dan keamanan:** autentikasi sesi Django, CSRF untuk formulir, validasi server, pembatasan kepemilikan data, escape teks pengguna, dan penyimpanan password melalui Django.

## 8. Tahapan pengembangan dan keluaran

| Tahap | Pekerjaan | Keluaran yang dapat diperiksa |
| --- | --- | --- |
| 0. Fondasi | Struktur Django, template global, Tailwind, navigasi awal | Halaman awal termuat dan CSS aktif; status ini sudah tersedia |
| 1. Akun | Registrasi, login, profil, peran, pengajuan penjual | Alur akun dan keputusan Admin bekerja |
| 2. Konten inti | Forum; katalog/etalase; data lokasi dan peta | Guest dapat menjelajah; anggota dan penjual dapat mengelola konten sesuai peran |
| 3. Pencarian cerdas | Kontrak filter, integrasi OpenRouter, fallback | Prompt menghasilkan hanya produk katalog; kegagalan layanan tertangani |
| 4. Integrasi rilis | Tautan marketplace–peta, administrasi, kualitas dan deployment | Alur §4 dapat diselesaikan dari antarmuka dan batas akses terpenuhi |

Tiap modul dikembangkan dengan migrasi data, halaman dan URL, validasi, pemeriksaan izin, keadaan kosong/galat, serta dokumentasi kontrak yang dipakai modul lain. Perubahan lintas modul perlu menyepakati nama field dan bentuk data sebelum diintegrasikan.

## 9. Kebutuhan nonfungsional

- **Kegunaan:** halaman dapat dipakai pada layar ponsel dan desktop; formulir memberi kesalahan per field; keadaan kosong memberi petunjuk langkah berikutnya.
- **Aksesibilitas:** label formulir, struktur heading, teks alternatif gambar, navigasi keyboard, dan kontras warna yang memadai.
- **Performa:** feed dan katalog memakai pagination; query daftar tidak mengambil relasi satu per satu; gambar dibatasi ukuran dan dioptimalkan saat implementasi.
- **Keandalan:** pencarian biasa dan peta dasar tetap dapat digunakan saat layanan eksternal gagal; respons kegagalan tidak membocorkan rahasia konfigurasi.
- **Privasi:** hanya data profil/lokasi yang dinyatakan publik ditampilkan; geolokasi pengguna tidak disimpan pada MVP; kredensial API tidak masuk ke klien.
- **Observabilitas:** galat integrasi, kegagalan validasi penting, dan aksi admin dicatat tanpa password, token, atau rahasia lain.

## 10. Batasan, asumsi, dan keputusan terbuka

| Topik | Keputusan untuk PRD ini | Perlu diputuskan sebelum implementasi terkait |
| --- | --- | --- |
| Transaksi | Di luar MVP; marketplace berfokus pada penemuan produk | Apakah kontak/pemesanan manual perlu tombol khusus |
| Guest dan LLM | LLM untuk akun login; Guest memakai pencarian biasa | Apakah Guest diberi kuota LLM terbatas |
| Stok nol | Tetap terlihat dengan label Habis | Apakah listing habis perlu disembunyikan secara default |
| Kontak/lokasi publik | Pemilik memilih informasi yang boleh ditampilkan | Tingkat detail alamat untuk Guest |
| Peta | Penyedia belum dipilih | Lisensi, kuota, dan biaya tile/geocoding |
| OpenRouter | Penyedia yang direncanakan README | Model, biaya, batas pemakaian, dan strategi timeout |
| Poin kontribusi | Lanjutan | Aturan poin dan manfaatnya |
| Admin | Administrasi dasar pada MVP | Detail kebijakan moderasi dan retensi jejak audit |

## 11. Pembagian penanggung jawab awal

Pembagian ini mengikuti README dan menunjukkan pemilik modul, bukan batas eksklusif perubahan kode:

| Modul | Penanggung jawab |
| --- | --- |
| Autentikasi dan pengguna | Vania Apsari Nailah Putri Difa |
| Forum komunitas | Khairani Hanifah Putri |
| Marketplace discovery | Adriana Ainurrahmah Damanik |
| Pencarian LLM | Adrian Nathanael Setiawan |
| Peta kebun | Muhammad Wisnu Jaya Wardana |

Integrasi antarmodul, administrasi, dan kesiapan rilis adalah tanggung jawab bersama. Untuk rincian konteks awal dan contoh alur, lihat README proyek.
