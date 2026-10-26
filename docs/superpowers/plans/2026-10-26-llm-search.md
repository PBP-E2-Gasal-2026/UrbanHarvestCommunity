# LLM Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasikan pencarian bahasa natural dan suggestion berbasis produk marketplace nyata untuk pengguna login, sesuai kontrak PDF.

**Architecture:** LLM mengekstrak filter allowlist; adapter backend menerapkannya ke database lokal. Suggestion hanya merujuk kandidat hasil query. Job durable diproses melalui RabbitMQ dengan coordinator tunggal yang otomatis beralih ke satu worker lokal saat broker tidak tersedia.

**Tech Stack:** Django 5.0, Python, requests, Pika, SQLite development/PostgreSQL production, Django templates, Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-10-26-llm-search-design.md` — baca spec dan PDF sebelum menjalankan plan.

## Global Constraints

- Marketplace dikembangkan terpisah; jangan menambah model, migrasi, atau endpoint marketplace produksi pengganti.
- Produk memakai `BigAutoField` dan URL `/marketplace/products/<id>/`.
- Model `google/gemma-3-27b-it`, provider OpenRouter, semua akses LLM Search wajib login.
- Tidak fetch semua produk, tidak SQL dari LLM, tidak query pencarian ke tabel akun.
- Kartu sementara tanpa nama merchant; nama hanya ditambahkan melalui interface publik marketplace kelak.
- Hasil kosong atau syarat yang belum didukung meminta klarifikasi, tanpa melonggarkan kriteria.
- Prompt maksimum 2.000 karakter; hasil default 20, maksimum 50; maksimal 3 job aktif per pengguna.
- RabbitMQ sehat: pool 4 thread; fallback: satu worker lokal pada satu coordinator aktif per deployment.
- Connect timeout OpenRouter 5 detik, read timeout 30 detik per panggilan; polling 2 detik; retensi job 24 jam.
- Worktree terpisah dan commit red → green → refactor; jangan push, merge, atau deploy sebagai bagian pengerjaan ini.
- Tes DB fixture tidak membuktikan integrasi akhir dengan marketplace yang belum tersedia.

## Review Focus

1. Output valid JSON yang menghilangkan syarat pengguna: ekstraksi harus memiliki jalur klarifikasi untuk syarat tak didukung (Task 2).
2. Nama/deskripsi produk berisi instruksi model: produk tetap data, ID/alasan suggestion harus divalidasi (Task 2).
3. Publish berhasil tetapi konfirmasi hilang: job tidak hilang dan pesan terlambat tidak menggandakan hasil (Task 5).
4. Worker mati setelah claim atau API call: lease dapat dipulihkan, hasil hanya ditulis pemilik lease; tidak menjanjikan exactly-once API (Task 3/5).
5. Marketplace belum terpasang atau kontrak berubah: status unavailable dibedakan dari pencarian kosong (Task 1/4).

## Struktur file dan batas antarmuka

- `llm_searching/exceptions.py`: exception domain dan kode galat aman.
- `llm_searching/filters.py`: validasi prompt dan `SearchFilters` immutable.
- `llm_searching/marketplace.py`: adapter baca dan proyeksi `ProductCard`.
- `llm_searching/openrouter.py`: HTTP dan skema ekstraksi/suggestion.
- `llm_searching/service.py`: orchestration pencarian dan grounding.
- `llm_searching/models.py`, `jobs.py`, `migrations/0001_initial.py`: persistensi, kuota, lease, penyimpanan hasil.
- `llm_searching/transport.py`, `worker.py`: RabbitMQ dan coordinator/fallback.
- `llm_searching/management/commands/run_llm_worker.py`, `cleanup_llm_jobs.py`: entry point operasi.
- `llm_searching/views.py`, `urls.py`, `templates/llm_searching/`: HTTP dan tampilan.
- `llm_searching/tests/`: test per domain; ubah `tests.py` kosong menjadi package.
- `llm_searching/tests/contract_app/`: model marketplace test-only, tanpa migrasi/registrasi produksi.
- `config/settings.py`, `config/urls.py`, `.env.example`, `requirements.txt`: konfigurasi modul.
- `static/js/llm_search.js`: submit/polling dan render melalui DOM aman.
- `docs/llm-search.md`, `docs/superpowers/execution/2026-10-26-llm-search.md`: setup/runbook dan bukti pengerjaan.

## Persiapan eksekusi

- [ ] Gunakan skill using-git-worktrees; periksa git-dir/common-dir, branch, status, dan tools worktree native sebelum fallback Git.
- [ ] Jika belum ada preferensi path, pakai `.worktrees/llm-search`; pastikan di-ignore sebelum `git worktree add -b feat/llm-search`.
- [ ] Bawa spec dan plan yang baru dibuat ke worktree tanpa menghapus perubahan pengguna. Commit dokumentasi awal di branch fitur; bersihkan hanya salinan dokumen yang dibuat agent di checkout awal setelah salinan aman.
- [ ] Gunakan venv repo yang tersedia atau venv terisolasi. Periksa dependensi; jangan membaca/menyalin secret `.env` ke output.
- [ ] Jalankan `python manage.py test` dan `python manage.py check` sebagai baseline. Catat jumlah tes dan kegagalan sebelum perubahan.
- [ ] Buat execution log berisi branch/path, baseline, dan tabel siklus red/green/refactor.

### Task 1: Filter dan adapter marketplace baca

**Files:** create `exceptions.py`, `filters.py`, `marketplace.py`, `tests/test_filters.py`, `tests/test_marketplace.py`, `tests/contract_app/`; modify konfigurasi test bila diperlukan.

**Interfaces:**
- `validate_prompt(value: object) -> str`.
- `parse_filters(payload: dict) -> SearchFilters`; field sesuai spec, `sort` berupa `newest`, `price_asc`, `price_desc`.
- `MarketplaceRepository.search(filters: SearchFilters) -> list[ProductCard]`.
- `MarketplaceRepository.category_slugs() -> list[str]`; query eksplisit dan berbatas, tidak full Product scan.
- Exception `InvalidSearch`, `UnsafeSearch`, `MarketplaceUnavailable` dibedakan.

- [ ] **RED:** tambahkan tes batas prompt, unknown key/lookup/SQL payload, bool sebagai harga, rentang terbalik, limit >50, kategori salah tipe, dan sort tak dikenal. Contoh assertion: `parse_filters({"max_price": 30000}).max_price == 30000`; payload `{"seller__email": "x"}` wajib ditolak.
- [ ] **RED:** fixture produk aktif/nonaktif, stock nol, kategori, dua harga sama. Assert hasil filter, batas 20/50, urutan stabil, URL angka, prioritas image, dan tidak ada nama merchant. Capture query aktual dan assert SELECT hanya product/category, tanpa tabel auth.
- [ ] Jalankan `python manage.py test llm_searching.tests.test_filters llm_searching.tests.test_marketplace -v 2`; pastikan kegagalan mencerminkan fitur yang belum ada. Commit `test(llm-search): red filter and marketplace contract`.
- [ ] **GREEN:** implementasikan filter allowlist dan adapter lazy dengan proyeksi kolom eksplisit. Missing model/schema mismatch menjadi `MarketplaceUnavailable`; jangan menyamarkannya menjadi hasil kosong. Jangan menggunakan manager/properti yang melakukan join tersembunyi.
- [ ] Jalankan tes Task 1 dan suite repo. Commit `feat(llm-search): green validated marketplace search`.
- [ ] **REFACTOR:** rapikan konstanta dan pemetaan field/ordering tanpa mengubah perilaku; jalankan tes kembali dan commit bila ada perubahan nyata. Rekam bukti di execution log.

### Task 2: OpenRouter, ekstraksi, dan suggestion grounded

**Files:** create `openrouter.py`, `service.py`, `tests/test_openrouter.py`, `tests/test_service.py`; modify `.env.example`, `config/settings.py`.

**Interfaces:**
- `OpenRouterClient.extract(prompt: str, categories: list[str]) -> dict`: output `{status, filters, clarification}`; status `search` atau `needs_clarification`.
- `OpenRouterClient.suggest(prompt: str, filters: SearchFilters, candidates: list[ProductCard]) -> dict`: output ID kandidat terurut dan reason codes per ID.
- `SearchService.run(prompt: str) -> dict`: hasil JSON-serializable dengan `status`, `filters`, `products`, `explanation`, dan `degraded`.

- [ ] **RED:** tes HTTP adapter melalui transport mock: model tepat, auth header hanya server, connect/read timeout `(5, 30)`, respons invalid/oversized, missing choices, HTTP error, serta schema-invalid JSON ditolak.
- [ ] **RED:** tes pencarian fixture dan pipeline: kosong meminta klarifikasi, prompt jumlah kilogram/tanggal panen di luar kemampuan masuk jalur klarifikasi tanpa query produk, suggestion ID asing/duplikat ditolak, alasan harus dapat dibuktikan. Sisipkan instruksi palsu di deskripsi produk dan pastikan tidak menjadi akses tool/query bebas.
- [ ] Jalankan `python manage.py test llm_searching.tests.test_openrouter llm_searching.tests.test_service -v 2`; commit `test(llm-search): red extraction and grounded suggestions`.
- [ ] **GREEN:** gunakan HTTP requests dan JSON Schema saat endpoint mendukungnya; validasi lokal tetap wajib. Skema menolak field tambahan. Jangan fallback dari output invalid menjadi query lebih luas. Jangan mengirim seluruh katalog, data akun, atau secret ke model.
- [ ] **GREEN:** validasi subset kandidat/reason codes; bentuk kalimat penjelasan dari fakta dan kode yang valid. Bila suggestion gagal, kembalikan kandidat hasil query dan penjelasan deterministik dengan `degraded=true`. Hasil kosong tidak memanggil suggestion.
- [ ] Jalankan tes Task 2 dan suite repo. Commit `feat(llm-search): green OpenRouter grounded search`.
- [ ] **REFACTOR:** satukan parsing/error mapping tanpa menyimpan output mentah; tes ulang dan commit perubahan nyata.

### Task 3: Job durable, kuota, dan lease

**Files:** modify `models.py`, `config/settings.py`; create `jobs.py`, migrasi, `tests/test_jobs.py`, command cleanup dan tesnya.

**Interfaces:**
- `submit_job(user_id: int, prompt: str) -> SearchJob`.
- `claim_job(job_id: UUID, *, now: datetime) -> UUID | None`: token lease.
- `finish_job(job_id: UUID, token: UUID, result: dict) -> bool`.
- `process_job(job_id: UUID, service: SearchService) -> bool`.
- Status `pending`, `processing`, `succeeded`, `needs_clarification`, `failed`.

- [ ] **RED:** tes submit, batas 3 job aktif atomik per pengguna, conditional claim, lease belum kedaluwarsa tak dapat diambil, recovery lease, token lama tak dapat menulis, terminal job tak diulang, prompt/hasil tidak memuat secret, cleanup >24 jam hanya job terminal.
- [ ] Jalankan `python manage.py test llm_searching.tests.test_jobs -v 2`; commit `test(llm-search): red durable jobs and leases`.
- [ ] **GREEN:** register app LLM, tambahkan model/migrasi dan helper job. Serialisasi kuota per owner memakai transaksi pendek; tidak ada transaksi panjang saat HTTP LLM. Gunakan lease minimal 120 detik dengan deadline pemrosesan yang konsisten dan token fencing untuk finalisasi.
- [ ] **GREEN:** cleanup memakai cutoff 24 jam; jangan menghapus job aktif/lease yang masih digunakan. Dokumentasikan perbedaan SQLite dan PostgreSQL dan lakukan tes race backend aktual bila tersedia.
- [ ] Jalankan tes Task 3, `python manage.py makemigrations --check --dry-run`, dan suite repo. Commit `feat(llm-search): green durable job lifecycle`.
- [ ] **REFACTOR:** ekstrak transisi status berulang, pertahankan tes claim/ownership; commit perubahan nyata.

### Task 4: API login, UI pencarian, dan kartu

**Files:** modify `views.py`, `config/urls.py`, navbar; create `urls.py`, templates halaman/card, `static/js/llm_search.js`, `tests/test_views.py`.

**Interfaces:** halaman `/llm-search/`, POST `/llm-search/api/jobs/`, GET `/llm-search/api/jobs/<uuid>/`. JSON API mengikuti nama field hasil Task 2 dan status Task 3.

- [ ] **RED:** tes Guest redirect/401, user login dengan sesi aplikasi valid, POST CSRF, input 400, kuota 429, job orang lain 404, UUID invalid, method 405, dan status marketplace_unavailable dibedakan dari kebutuhan klarifikasi.
- [ ] **RED:** tes HTML memuat form berlabel dan kartu dengan URL kontrak; string produk/model berisi HTML harus di-escape; tidak ada API key, nama merchant, atau detail internal di respons.
- [ ] Jalankan `python manage.py test llm_searching.tests.test_views -v 2`; commit `test(llm-search): red authenticated search interface`.
- [ ] **GREEN:** implementasikan view tipis, partial kartu reusable, dan polling 2 detik. Polling berhenti di status terminal, menangani logout/network failure, dan memakai textContent untuk teks dinamis. Payload model tidak dirender sebagai HTML. Jangan membangun detail produk marketplace.
- [ ] Verifikasi tes Task 4, suite repo, dan `npm run build:css`; commit `feat(llm-search): green authenticated search interface`.
- [ ] **REFACTOR:** satukan formatter kartu/status tanpa mengubah kontrak; tes ulang dan commit perubahan nyata.

### Task 5: RabbitMQ, coordinator, dan pemulihan fallback

**Files:** create `transport.py`, `worker.py`, command `run_llm_worker.py`, `tests/test_worker.py`, `tests/test_transport.py`; modify requirements/settings/env.

**Interfaces:**
- `RabbitTransport.publish(job_id: UUID) -> None`, `receive() -> Delivery | None`, `ack(delivery) -> None`, `close() -> None`.
- `WorkerCoordinator.tick() -> None`: satu siklus dispatch/consume/fallback, jam dan transport dapat diinjeksi saat tes.
- `python manage.py run_llm_worker`: loop terbatas oleh stop event/signal, satu coordinator aktif per deployment.

- [ ] **RED:** transport test double memodelkan broker sehat, publish-confirm ambigu, putus sesudah delivery, redelivery, reconnect, dan shutdown. Assert job durable tetap dapat selesai, ID message saja, lease mencegah finalisasi ganda, maksimal satu pekerjaan baru lokal ketika broker mati, dan pool dipulihkan setelah reconnect.
- [ ] **RED:** tes bounded inflight/pending dispatch, backoff reconnect, expired lease recovery, poison message, dan kehilangan koneksi yang tidak menghentikan worker command.
- [ ] Jalankan `python manage.py test llm_searching.tests.test_worker llm_searching.tests.test_transport -v 2`; commit `test(llm-search): red broker recovery and serial fallback`.
- [ ] **GREEN:** tambahkan Pika versi kompatibel, verifikasi API dari dokumentasi primer sebelum memakainya. Durable queue, persistent message, publisher confirms, manual ack, prefetch bounded, dan koneksi DB/AMQP per thread.
- [ ] **GREEN:** coordinator mempertahankan job DB sebagai sumber kebenaran, mengekang publish ulang, memakai deadline/lease Task 3, membiarkan inflight selesai sebelum serial fallback mengambil pekerjaan lain. Reconnect dengan backoff 1–30 detik; success memulihkan pool 4 thread. Tidak membuat fallback di setiap web process.
- [ ] Jalankan tes Task 5 dan suite repo. Bila broker lokal tersedia, lakukan smoke broker sehat → stop → fallback → start → recovery. Catat jika hanya transport double dapat diverifikasi. Commit `feat(llm-search): green resilient RabbitMQ worker`.
- [ ] **REFACTOR:** rapikan lifecycle resource/signal dan hilangkan duplikasi recovery; verifikasi ulang failure scenarios dan commit perubahan nyata.

### Task 6: Dokumentasi, verifikasi akhir, dan review

**Files:** create `docs/llm-search.md`; update README, `.env.example`, execution log, serta status checkbox plan.

- [ ] Dokumentasikan pemasangan dependency, migrasi LLM, API, variabel konfigurasi, menjalankan worker tanpa/dengan RabbitMQ, cleanup, retensi, kuota, sumber data, dan batas satu coordinator.
- [ ] Dokumentasikan kontrak adapter dan checklist handoff marketplace: model/field/tabel/manager aktual, foto storage, route angka, dan interface merchant. Runtime saat dependency belum hadir harus dijelaskan sebagai unavailable, bukan demo produk nyata.
- [ ] Catat hash red/green/refactor, command dan hasil tes, batas pengujian nyata OpenRouter/RabbitMQ/PostgreSQL, serta risiko retry API setelah crash.
- [ ] Jalankan `python manage.py test`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, lint file Python yang berubah, `npm run build:css`, dan `git diff --check`.
- [ ] Gunakan skill requesting-code-review untuk review branch keseluruhan; tindaklanjuti temuan dengan tes gagal sebelum perbaikan perilaku. Gunakan verification-before-completion sebelum mengklaim selesai.
- [ ] Commit dokumentasi/verifikasi; pastikan worktree bersih. Gunakan finishing-a-development-branch untuk melaporkan hasil dan pilihan integrasi tanpa push/merge/deploy otomatis.

## Self-review plan

Kebutuhan spec dipetakan: query/filter/privacy/contract Task 1; model, suggestion,
clarification, fallback LLM Task 2; persistensi/kuota/retensi Task 3; login/CSRF/owner/UI
Task 4; broker/recovery/concurrency Task 5; dokumentasi, handoff, bukti TDD dan validasi
Task 6. Lima review focus memiliki tes pada task pemiliknya. Antarmuka service/job/UI
menggunakan hasil JSON yang sama; fixture tidak dimasukkan ke runtime produksi.

## Execution handoff

Plan menunggu review pengguna. Rekomendasi: native, implementer tetap dalam sesi ini
karena task bergantung pada antarmuka filter, service, job, dan worker yang sama;
reviewer independen memeriksa branch di akhir. Alternatif: subagent-driven dengan
implementer dan reviewer terpisah per task, dengan biaya konteks lebih tinggi.
