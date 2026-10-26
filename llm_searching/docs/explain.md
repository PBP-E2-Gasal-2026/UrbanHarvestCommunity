* GOAL: ini adalah apps module llm searching. tujuan utamanya adalah melakukan koneksi dengan local database, jadi llm dapat mengembalikan query database dari prompt user untuk mencari barang-barang yang dijual di marketplace, sekaligus juga penjelasan untuk jawaban dari permintaan user

* LIMITATION: setiap prompt user yang dimasukkan ke server pastiin agar sudah di santize dengan benar sehingga llm hanya bisa readonly db, hanya bisa akses ke table marketplace tanpa bisa mengakakses table table seperti user atau table lainnhya yang scopenya diluar marketplace (jika ada query `update`, `delete` ataupun apapun yang sifatnya non readonly pastiin keluarin Exception)

* FLOW: saya ingin kamu menerapkan flow tdd dengan red commit, green commit dan juga refactor secara clean dan bersih untuk worktreenya nanti

* model llm yang digunakan adalah gemma 27 dengan provider openrouter

* untuk high availability, kita bisa gunakan message passing dengan rabbit mq agar setiap request yang masuk nantinya diproses secara atomic multithreading sehingga user tidak terlalu menunggu lama gilirannya untuk mendapatkan jawaban dari AInya

* contract besar dan utama dari module ini berada di root README.md

* pasttin dokumentasi untuk pengerjaan ini lengkap dan juga clean

* untuk saat ini bisa buat model etalase di marketplace module dan nanti setiap query ke table ini dilakukan akan mengembalikan card yang mengarah ke /product/id:UUID/ cardnya bisa berupa single card ataupun multiple tergantung return dari llm tersebut

* jika rabbit mq mati atau missing app tetap bisa berjalan dengan single worker dan saat rabbit mq available lagi bisa kembali idupin workernya