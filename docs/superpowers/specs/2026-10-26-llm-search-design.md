# Desain integrasi LLM Search

Status: disetujui pengguna melalui pesan “acc”; siap menjadi dasar plan implementasi.

## Tujuan dan sumber kebutuhan

Membantu pengguna yang sudah login mencari dan memahami pilihan produk marketplace
melalui bahasa natural. Hasil dan suggestion harus berasal dari database marketplace.

Sumber lokal:

- `README.md`, terutama Searching LLM, database grounding, fallback, dan hak akses.
- `llm_searching/docs/explain.md`: pembatasan baca, OpenRouter, RabbitMQ, TDD,
  worktree, dan dokumentasi.
- `llm_searching/docs/api_contract.pdf`: kontrak dependency marketplace yang
  dikembangkan terpisah, bukan permintaan membangun fitur marketplace.
- Klarifikasi pengguna dalam percakapan tanggal 2026-10-26.

Jika bertentangan, klarifikasi pengguna diutamakan. Untuk struktur produk dan URL,
PDF menjadi acuan. Keputusan PRD lama yang belum dikonfirmasi bukan persetujuan baru.

## Keputusan yang telah disetujui

1. Cakupan pekerjaan adalah integrasi searching dan suggestion, bukan implementasi
   katalog, CRUD produk, etalase, pembayaran, atau statistik marketplace.
2. Marketplace dikembangkan terpisah; integrasi dan pengujiannya berdasarkan PDF.
3. ID produk berupa angka (`BigAutoField`), URL `/marketplace/products/<id>/`.
4. LLM mengekstrak filter terstruktur. Backend memvalidasi dan menerjemahkannya
   menjadi query baca database lokal. Tidak fetch seluruh katalog untuk disaring LLM
   dan tidak mengeksekusi SQL buatan LLM.
5. Provider OpenRouter, model `google/gemma-3-27b-it`.
6. Semua akses LLM Search wajib login.
7. Hasil kosong meminta pengguna memperjelas pencarian. Jangan otomatis melonggarkan
   harga, lokasi, atau kriteria lain untuk menawarkan alternatif.
8. Proses pengembangan memakai worktree terpisah dan siklus commit red, green,
   refactor yang mempunyai bukti pengujian.
9. Kartu LLM sementara boleh tanpa nama merchant sampai marketplace menyediakan
   interface nama publik; pencarian tidak membaca nama seller dari tabel akun.
10. Syarat pencarian yang belum didukung meminta klarifikasi dan menjelaskan
    keterbatasannya. Tidak menghapus atau mengabaikan syarat tersebut diam-diam.

## Kondisi repositori

Backend Django 5.0, template Django dan Tailwind. SQLite untuk pengembangan,
PostgreSQL untuk produksi. `marketplace` dan `llm_searching` masih berupa kerangka
dan belum terdaftar di settings. Auth memakai user kustom dan pemeriksaan sesi
melalui `SingleSessionMiddleware`; login bukan sekadar `force_login` dalam tes.

Tidak tersedia model Product/Category atau implementasi serializer marketplace.
Halaman produk nyata hanya akan tersedia setelah dependency marketplace terpasang.
Pengujian terisolasi tidak membuktikan integrasi akhir dengan modul yang belum ada.

## Pendekatan yang dibahas

| Pendekatan | Pertimbangan | Keputusan |
| --- | --- | --- |
| Ambil seluruh produk lalu filter | Membaca data berlebihan dan membesarkan konteks LLM | Tidak dipilih |
| LLM menghasilkan SQL | Memerlukan pembatasan SQL yang kompleks, termasuk SELECT lintas tabel dan query mahal | Tidak dipilih |
| Filter terstruktur, query backend, suggestion dari hasil | Membatasi operasi, field, dan jumlah data secara eksplisit | Dipilih pengguna |

## Batas dan kriteria kegagalan

Pencarian hanya membaca field marketplace yang disetujui. LLM tidak mendapat
kredensial DB, nama tabel auth, akses tool SQL, atau akses ORM bebas. Tidak ada
penambahan model produk produksi, migrasi tabel marketplace, atau endpoint marketplace
palsu untuk menggantikan tim pemilik dependency.

Kegagalan desain: hasil fiktif, data produk privat/arsip ikut tampil, model mengakses
data akun, constraint pengguna dilonggarkan diam-diam, request hilang saat broker
mati, atau job milik pengguna lain dapat dibaca.

## Rancangan alur

1. Pengguna login membuka halaman LLM Search dan mengirim prompt dengan CSRF.
2. Backend memvalidasi input dan menyimpan job milik pengguna.
3. Worker mengambil job melalui RabbitMQ, atau satu worker lokal saat broker gagal.
4. OpenRouter mengembalikan filter JSON atau kebutuhan klarifikasi.
5. Validator menolak output di luar skema; adapter menjalankan SELECT terbatas.
6. Hasil kosong menghasilkan pesan klarifikasi tanpa panggilan suggestion.
7. Untuk hasil yang ada, hanya kandidat terbatas dan field publik yang diproyeksikan
   dikirim ke tahap suggestion. LLM memilih/meranking ID dari kandidat tersebut dan
   alasan terstruktur. Backend memvalidasi bahwa semua ID adalah subset kandidat.
8. Backend membentuk penjelasan dari alasan tervalidasi dan fakta produk. Kartu
   dibentuk dari data produk, bukan dari teks model.
9. UI melakukan polling status job milik pengguna dan merender hasil atau pesan galat.

Hanya tahap 4 dan 7 menghubungi OpenRouter. Teks produk diperlakukan sebagai data
yang tidak dipercaya, bukan instruksi. Usulan alasan berupa kode terkontrol seperti
`matches_keyword`, `within_budget`, `matches_location`, dan `available`; backend
mengecek buktinya sebelum membentuk kalimat. Klaim kesehatan, kecocokan budidaya,
atau manfaat lain tidak disimpulkan dari nama produk saja.

## Kontrak filter dan adapter marketplace

Usulan skema filter: `keyword`, `categories` (slug), `min_price`, `max_price`,
`location`, `in_stock`, `sort`, dan `limit`. `sort` hanya terbaru/harga naik/harga
turun dengan tie-break ID. Tidak menerima nama field, lookup ORM, nama tabel,
ekspresi query, path relasi, atau SQL dari model. Field tidak dikenal ditolak.

Harga berupa bilangan bulat nonnegatif, rentang harga konsisten, boolean bukan
pengganti integer, kategori berupa daftar string terbatas, dan limit dibatasi server.
Permintaan tanpa kriteria yang dapat digunakan meminta klarifikasi, bukan mengambil
seluruh katalog. Query selalu mengecualikan `is_active=False`; stok nol mengikuti
filter dan ditandai habis bila ditampilkan. Tidak mengklaim jarak terdekat tanpa
dukungan koordinat/filter yang disepakati; kebutuhan ambigu meminta klarifikasi.

**Cakupan yang disetujui setelah builder check:** MVP hanya menangani filter di atas.
Jika pengguna menyertakan kondisi yang belum terwakili (jumlah kebutuhan, total
anggaran berdasarkan satuan/min_order, tanggal panen, pengecualian, atau OR kompleks),
meminta klarifikasi dan menyebut keterbatasannya, bukan menghapus syarat itu
diam-diam. Pengguna telah menyetujui perilaku ini.

Adapter produksi memuat Product/Category marketplace yang benar secara lazy.
Jika dependency belum tersedia atau kontraknya tidak cocok, kembalikan status
`marketplace_unavailable` yang jelas. Jangan membuat model produksi pengganti atau
mengembalikan data uji saat runtime.

Adapter menggunakan proyeksi eksplisit dari kolom produk/category. Pencarian dan
enumerasi kategori tidak membaca tabel akun, ulasan, transaksi, atau foto tambahan.
Tidak memakai properti atau default manager dependency tanpa memeriksa query yang
dihasilkannya. Foto kartu berasal dari image/image_url sesuai prioritas PDF, bukan
gallery atau statistik. Nama model dan tabel final yang tidak disebut eksplisit PDF
harus diperiksa ketika dependency tersedia.

Produk untuk kartu: ID, nama, deskripsi singkat, foto, harga, satuan, stok, kategori,
lokasi, dan URL detail yang dibentuk dari ID valid. Field lain di PDF bukan kewajiban
membangun ulang endpoint detail. `is_available` diturunkan dari aktif dan stok.

**Keputusan yang disetujui:** PDF memberikan `merchant` sebagai nama publik, tetapi sumber
modelnya adalah `seller` FK ke User. Membaca nama seller melalui join auth bertentangan
dengan batas tabel. Kartu LLM sementara tanpa nama merchant telah diizinkan pengguna.
Nama merchant baru dapat ditambahkan melalui interface nama publik yang disediakan
tim pemilik. Jangan mengasumsikan tabel/field merchant baru atau membuka join auth.

## Keamanan

- Validasi panjang, tipe, teks kosong, karakter kontrol, dan batas ukuran input.
  Normalisasi teks bukan jaminan perlindungan terhadap prompt injection.
- Prompt dan output LLM selalu tidak dipercaya. Keamanan utama adalah skema
  allowlist, penerjemah query tetap, proyeksi field, dan pengujian query aktual.
- Adapter pencarian hanya mempunyai operasi baca; payload dengan SQL/operasi
  tulis sebagai instruksi ditolak. Kata yang kebetulan sama dengan keyword SQL di
  nama barang tidak menjadi alasan memodifikasi query.
- Tidak ada `raw`, `extra`, eval, atau eksekusi lookup arbitrer dari input model.
- Pisahkan akses autentikasi dan penyimpanan job dari akses pencarian marketplace.
  Sistem tetap membaca sesi/user untuk login dan menulis tabel operasional LLM;
  batas readonly berlaku pada jalur pencarian marketplace, bukan seluruh aplikasi.
- Kredensial OpenRouter/RabbitMQ hanya di server. Log tidak berisi secret, prompt
  lengkap, atau isi produk lengkap. Output model dirender sebagai teks yang di-escape.
- ID job bukan otorisasi: pengambilan status/result wajib mengecek pemilik.

## RabbitMQ dan fallback: usulan teknis untuk ditinjau

Gunakan Pika dan management command worker yang disupervisi deployment. Data job
durable disimpan di `llm_searching`, pesan RabbitMQ hanya membawa ID job. Ini
menghindari dependency Redis/result backend tambahan.

Satu coordinator per deployment mempublikasikan job pending dan menjalankan pool
thread terbatas saat RabbitMQ sehat. Masing-masing thread memiliki koneksi DB dan
AMQP sendiri; koneksi/channel tidak dibagi sembarangan antarthread. Publish memakai
publisher confirms, pesan persistent, antrean durable, prefetch terbatas, manual ack
setelah status hasil tersimpan. Tidak membuka transaksi DB selama panggilan LLM.

Claim job melalui conditional update dengan token lease dan batas waktu. Hanya
pemegang token yang boleh menyimpan hasil. Job terminal tidak dijalankan ulang.
Delivery ulang ditangani secara idempoten. Exactly-once panggilan OpenRouter tidak
dijanjikan: crash setelah API selesai tetapi sebelum hasil tersimpan bisa menyebabkan
panggilan ulang. Lease lebih lama dari batas pemrosesan dan dapat dipulihkan.

Saat broker tidak dikonfigurasi, koneksi gagal, publish ambigu, atau broker terputus,
coordinator berhenti menambah pekerjaan paralel dan memproses job durable melalui
satu worker lokal. Job yang telah di-claim thread lain dibiarkan selesai/expire,
bukan dijalankan bersamaan. Status job mencegah pesan terlambat menggandakan hasil.
Coordinator mencoba koneksi ulang dengan backoff terbatas. Setelah koneksi dan
deklarasi antrean berhasil, kapasitas pool dipulihkan otomatis.

Memerlukan command worker tetap hidup, tetapi tidak memerlukan RabbitMQ agar job
diproses. Single fallback berarti satu coordinator aktif per deployment, bukan satu
thread fallback baru per web process. Dokumentasi deploy harus menyebutkan batas ini.
Supervisor worker, clustering RabbitMQ, dan scale-out coordinator bukan fitur baru
yang dijanjikan oleh implementasi ini.

## Status job, HTTP, dan UI: usulan

Job: `pending`, `processing`, `succeeded`, `needs_clarification`, `failed`; metadata
berupa owner, prompt, filter valid, hasil terstruktur, waktu, lease, dan error code.
Tidak menyimpan API key atau respons mentah LLM. Job disimpan untuk polling, bukan
fitur riwayat percakapan; usulan retensi 24 jam dengan command cleanup.

- `GET /llm-search/`: halaman formulir, redirect login untuk Guest.
- `POST /llm-search/api/jobs/`: buat job, 202 untuk request valid.
- `GET /llm-search/api/jobs/<uuid>/`: status/result milik pengguna.
- API Guest: 401; CSRF tetap aktif; job bukan milik pengguna: 404.
- Input invalid: 400; kuota antrean terlampaui: 429; galat konfigurasi/dependency
  tersedia sebagai kode aman tanpa traceback atau secret.

UI memakai base template repo: prompt, status proses, ringkasan filter, penjelasan,
dan kartu. Kondisi kosong meminta klarifikasi. Tidak membuat halaman detail produk.
Kartu menggunakan partial reusable yang dapat diselaraskan dengan komponen tim
marketplace setelah tersedia. Scope tampilan ini perlu ditinjau bersama spec.

Usulan batas yang dapat dikonfigurasi: prompt 2.000 karakter, hasil default 20 dan
maksimum 50 sesuai PDF, pool 4 thread ketika broker sehat, polling 2 detik,
OpenRouter connect timeout 5 detik dan read timeout 30 detik per panggilan,
maksimal 3 job aktif per pengguna, serta cleanup job setelah 24 jam.
Angka ini berasal dari usulan implementer yang termasuk dalam persetujuan dokumen.

## Penanganan kegagalan

Output tidak valid/instruksi terlarang ditolak sebelum query. Permintaan ambigu
meminta klarifikasi. OpenRouter timeout/error menampilkan kegagalan yang dapat
dicoba ulang, dengan opsi pencarian biasa di marketplace; tidak menambahkan
interpretasi keyword diam-diam. Bila tahap suggestion gagal setelah query berhasil,
tampilkan produk hasil query dengan penjelasan deterministik dan status keterbatasan.
Ketidaktersediaan marketplace dibedakan dari hasil pencarian kosong.

## Verifikasi dan keluaran pekerjaan

- Tes filter, injection, tipe salah, unknown field, batas hasil, kategori/harga/stok.
- Contract test terhadap tabel marketplace test-only sesuai PDF; uji query benar-benar
  SELECT dan tidak menjangkau tabel auth. Fake/mocked repository untuk tes layanan.
- Tes grounding: ID asing/duplikat, alasan tidak terbukti, teks produk berisi instruksi,
  hasil kosong, respons rusak, timeout, dan fallback suggestion.
- Tes auth dengan sesi aplikasi, CSRF, kepemilikan job, dan input invalid.
- Tes worker: atomic claim, redelivery, lease, broker hilang/pulih, fallback satu
  worker, serta publish yang hasilnya ambigu. Verifikasi broker nyata bila tersedia;
  laporkan eksplisit jika hanya transport test double yang dapat dijalankan.
- Tes regresi Django, system checks, pemeriksaan migrasi, lint perubahan, dan build CSS
  bila template memerlukan kelas baru. Tes PostgreSQL aktual bila infrastrukturnya
  tersedia; jangan mengklaim SQLite membuktikan concurrency PostgreSQL.
- Dokumentasi setup, environment, worker, kontrak adapter, runbook gangguan, command
  cleanup, keputusan keamanan, dan bukti red/green/refactor.

## Yang tetap perlu diperiksa saat integrasi marketplace

Implementasi Product/Category, nama tabel final, manager default, storage foto,
interface nama merchant, routing produk, dan kompatibilitas serializer. Sampai
dependency hadir, runtime tanpa marketplace harus gagal dengan pesan terkendali;
pengujian fixture membuktikan kontrak internal, bukan integrasi end-to-end final.

## Referensi teknis

- Django queries: https://docs.djangoproject.com/en/5.0/topics/db/queries/
- Django QuerySet: https://docs.djangoproject.com/en/5.0/ref/models/querysets/
- OpenRouter structured outputs:
  https://openrouter.ai/docs/guides/features/structured-outputs
- Model: https://openrouter.ai/google/gemma-3-27b-it
- RabbitMQ reliability: https://www.rabbitmq.com/docs/reliability
- RabbitMQ confirms: https://www.rabbitmq.com/docs/confirms

## Langkah berikutnya

Builder check selesai. Dua pertanyaan material mengenai sumber nama merchant dan
batas kemampuan filter telah dijawab pengguna dan dimasukkan ke keputusan 9–10.
Tidak ada pertanyaan kebutuhan material yang tersisa dari pemeriksaan tersebut.
Berikutnya adalah persetujuan dokumen lengkap, termasuk proposal teknis dan batasnya.
Setelah disetujui, gunakan skill writing-plans untuk menulis rencana implementasi.
Detail teknis di atas disetujui sebagai bagian dokumen. Instruksi pengguna berikutnya
meminta pengerjaan dilanjutkan di checkout utama dan history commit dipertahankan;
lihat execution log untuk transfer fast-forward serta perbaikan hasil review.
