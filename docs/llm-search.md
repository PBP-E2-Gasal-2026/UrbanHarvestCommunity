# LLM Search: integrasi dan operasi

## Cakupan

Pencarian bahasa natural untuk pengguna login, memakai OpenRouter
`google/gemma-3-27b-it`. LLM mengembalikan filter; backend melakukan SELECT ke
produk/category marketplace. Hanya kandidat hasil database yang boleh menjadi
suggestion. Penjelasan dibentuk dari fakta produk dan alasan terstruktur tervalidasi.
Kartu memakai `/marketplace/products/<id>/`, ID angka, sementara tanpa nama merchant.

Marketplace dikembangkan terpisah. Modul ini **tidak menyediakan katalog atau model
produk produksi pengganti**. Pada checkout yang belum memiliki dependency tersebut,
job berakhir dengan `marketplace_unavailable`, bukan produk contoh atau hasil kosong.
Test fixture bukan bukti integrasi akhir dengan implementasi marketplace nyata.

## Menjalankan

```bash
python -m pip install -r requirements.txt
python manage.py migrate
npm ci
npm run build:css
python manage.py runserver
```

Isi `OPENROUTER_API_KEY` di environment server. Jalankan command berikut pada proses
terpisah yang tetap hidup, termasuk ketika RabbitMQ tidak digunakan:

```bash
python manage.py run_llm_worker
```

Login melalui `/auth/login/`, lalu buka `/llm-search/`. Login memerlukan sesi aplikasi
yang valid, sesuai `SingleSessionMiddleware`. Halaman meminta CSRF dan mempoll status
setiap 2 detik. Akses job milik orang lain mengembalikan 404.

`run_llm_worker --once` menjalankan satu siklus, berguna untuk pemeriksaan operasi.
`--poll-interval` default 1 detik, minimum 0,05 detik. SIGTERM/SIGINT menghentikan
admission dan menunggu pekerjaan thread selesai; beri grace period setidaknya
180 detik sebelum force kill. Gunakan process supervisor untuk restart command.

## Konfigurasi

| Variabel | Default | Arti |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | kosong | Kunci server; jangan dimasukkan ke JavaScript/log |
| `LLM_RABBITMQ_URL` | kosong | Kosong mengaktifkan fallback lokal serial |
| `LLM_WORKERS` | 4 | Pool saat broker sehat; dibatasi 1–16 |
| `LLM_MAX_ACTIVE_JOBS` | 3 | Job pending/processing maksimum per akun |
| `LLM_LEASE_SECONDS` | 180 | Minimum 180 detik, token/expiry memagari finalisasi |

Prompt maksimum 2.000 karakter, hasil default 20 dan maksimum 50. Timeout OpenRouter
5 detik connect dan 30 detik read; body dibatasi 64 KiB dan waktu pembacaan diperiksa
setiap chunk. Endpoint OpenRouter dan model ditetapkan server. Respons JSON berduplikat
key, field/lookup tak dikenal, angka invalid, atau skema salah ditolak.

Untuk development SQLite gunakan `LLM_WORKERS=1` bila memakai broker. PostgreSQL
lebih sesuai untuk concurrency produksi; SQLite dapat mengalami database lock saat
beberapa writer berjalan, meski conditional claim mencegah dua token sukses.

## RabbitMQ dan recovery

Contoh URL untuk broker lokal: `amqp://guest:guest@127.0.0.1:5672/%2F`.
Gunakan kredensial/vhost deployment sendiri untuk produksi; URL disimpan hanya di server.
Antrean `llm.search` durable, pesan persistent hanya membawa ID job, publisher confirms,
manual ack, dan prefetch 1. Setiap thread membuka/menutup koneksi AMQP dan DB sendiri;
koneksi publisher dipelihara coordinator. Client dipin ke Pika 1.3.2.

**Jalankan satu coordinator aktif per deployment.** Jangan menjalankan command ini
otomatis dalam setiap proses Gunicorn. Pool paralel berada di coordinator tersebut.
Saat broker mati, coordinator menunggu inflight selesai lalu memproses satu job lokal
per siklus. Reconnect memakai backoff 1–30 detik; pool pulih otomatis saat broker sehat.
Tidak perlu restart web server saat broker mati/pulih.

Database job adalah sumber kebenaran. Publish dengan konfirmasi ambigu tidak
menghilangkan job; pesan terlambat/duplikat tak dapat menggandakan hasil terminal.
Jika worker mati, job dapat diambil lagi setelah lease kedaluwarsa. Crash setelah
OpenRouter menjawab tetapi sebelum hasil tersimpan **dapat menyebabkan panggilan API
ulang**; exactly-once API dan biaya tunggal tidak dijanjikan.

Command worker wajib hidup agar antrean maju, walaupun broker tersedia. Supervisor
proses dan cluster broker tetap tanggung jawab deployment; RabbitMQ sendiri bukan
jaminan high availability untuk keseluruhan aplikasi.

## Kontrak pencarian

Filter yang didukung: `keyword`, `categories` (list slug), `min_price`, `max_price`,
`location`, `in_stock`, `sort` (`newest`, `price_asc`, `price_desc`), `limit`.
Harga adalah Rupiah per satuan produk. Produk arsip selalu dikecualikan. Stok nol
boleh tampil dengan label Habis kecuali `in_stock=true`. Sorting harga memakai ID
sebagai tie-break; terbaru memakai updated_at dan ID.

Syarat yang belum didukung (misalnya total 3 kg di bawah anggaran tertentu, tanggal
panen, pengecualian, OR kompleks, jarak terdekat, atau kecocokan budidaya) meminta
klarifikasi. Tidak ada pelonggaran kriteria atau pencarian keyword otomatis ketika
interpretasi gagal. Kemampuan model mengenali semua kondisi memerlukan evaluasi
prompt nyata; validasi skema tidak membuktikan kesetiaan semantik terhadap prompt.

Tidak ada hasil: minta pengguna memperjelas produk/lokasi/harga. Gagal pada tahap
suggestion: tampilkan hasil query dengan penjelasan fakta dan `degraded=true`.
Gagal interpretasi/provider: beri pesan aman dan tautan marketplace.

### API

- `GET /llm-search/`: halaman, login wajib.
- `POST /llm-search/api/jobs/`: JSON `{"prompt":"Cari tomat di bawah 30 ribu"}`,
  header CSRF; 202 dengan `id`, `status`, dan `status_url`.
- `GET /llm-search/api/jobs/<uuid>/`: status milik akun. Status terminal:
  `succeeded`, `needs_clarification`, `failed`. Hasil memuat `filters`, `products`,
  `explanation`, `degraded`; galat mempunyai `error_code` yang aman.

API menggunakan 400 untuk input salah, 401 Guest, 403 CSRF, 404 ownership/ID tidak
tersedia, 405 method salah, 429 kuota, 503 gangguan DB saat admission. Respons status
job tidak menyertakan prompt, token lease, atau detail DB/provider.

## Handoff marketplace

Sumber kontrak: `llm_searching/docs/api_contract.pdf`. Adapter lazy mengharapkan
`marketplace.Product`, `marketplace.Category`, tabel `marketplace_product` dan
`marketplace_category`. Saat tim marketplace memasang modulnya, register app tersebut
melalui integrasi mereka dan jalankan migrasi milik marketplace; migrasi LLM tidak
membuat tabel produk.

Checklist integrasi:

1. Verifikasi nama model/tabel, FK category, dan kolom yang diproyeksikan: id, name,
   description, image, image_url, price, unit, stock, location, is_active, updated_at;
   category.name/slug. Samakan adapter bila kontrak final berbeda.
2. Verifikasi query hanya membaca tabel produk/category. Adapter memakai QuerySet
   eksplisit untuk menghindari manager default yang dapat menambah join ke akun.
3. Verifikasi prioritas foto unggahan melalui storage field, lalu image_url cadangan.
   URL gambar hanya http/https atau path root lokal. Konfigurasikan media storage di
   modul pemiliknya; jangan mengandalkan properti produk yang bisa memicu query tambahan.
4. Pastikan route `/marketplace/products/<id>/` dan katalog `/marketplace/` tersedia.
5. Selaraskan partial kartu LLM dengan komponen marketplace. Nama merchant tetap tidak
   diambil dari auth; butuh interface publik yang disepakati terlebih dahulu.
6. Jalankan tes end-to-end nyata dengan produk marketplace dan API OpenRouter sesudah
   dependency/kredensial tersedia. Jangan menganggap fixture sudah memverifikasinya.

## Retensi, privasi, dan runbook

Prompt tersimpan sementara di job untuk diproses; bukan riwayat chat. Jadwalkan:

```bash
python manage.py cleanup_llm_jobs
```

Command menghapus job terminal yang selesai lebih dari 24 jam lalu. Job aktif tidak
terhapus otomatis; job processing akan dipulihkan setelah lease jika worker hidup.
Tanpa scheduler cleanup, job terminal tetap tersimpan. Log aplikasi tidak memuat
prompt lengkap, token, respons mentah LLM atau detail exception upstream.

- Antrean tidak maju: periksa proses worker dan koneksi DB sebelum memeriksa broker.
- `marketplace_unavailable`: periksa app/migrasi/model/kontrak dependency.
- `provider_unavailable`: periksa key, kuota, dukungan JSON Schema endpoint model,
  dan konektivitas; jangan menaruh token di output diagnosis.
- Broker putus: biarkan coordinator fallback/reconnect; jangan menyalakan fallback
  tambahan pada web process. Cek status job, bukan hanya jumlah pesan broker.
- Job tertahan: periksa lease dan kesehatan worker. Jangan mereset token job yang
  masih diproses; tunggu lease/recovery agar tidak menggandakan panggilan model.

## Pengujian

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check llm_searching --exclude migrations --exclude admin.py
npm run build:css
node --check static/js/llm_search.js
```

`admin.py` masih stub bawaan dan tidak diubah. Test contract memakai tabel test-only
sesuai PDF, tidak model marketplace produksi. Tes OpenRouter memakai HTTP transport
fake; tes worker memodelkan gangguan/recovery dengan transport double. Tes race
PostgreSQL hanya dijalankan pada backend PostgreSQL dan diskip pada SQLite.
Lihat execution log untuk bukti pengujian aktual dan keterbatasannya.

Desain: `docs/superpowers/specs/2026-10-26-llm-search-design.md`.
Plan: `docs/superpowers/plans/2026-10-26-llm-search.md`.
Bukti TDD: `docs/superpowers/execution/2026-10-26-llm-search.md`.
