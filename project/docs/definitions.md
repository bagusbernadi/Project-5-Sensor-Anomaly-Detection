# Definisi dan keputusan (Project 5)

Semua parameter ada di `code/common.py`. Dokumen ini menjelaskan arti tiap istilah dan keputusan yang diambil.

## Data dan urutan waktu
- **Titik data (bacaan sensor):** satu nilai suhu per 5 menit dari file NAB `machine_temperature_system_failure.csv`.
- **Kunci urutan = `seq`** (urutan baris asli), bukan timestamp. Alasan: timestamp mundur 55 menit satu kali (2014-01-07 02:55 kembali ke 02:00), sehingga 12 timestamp muncul dua kali. Semua jendela bergulir dihitung menurut `seq`, bukan menurut waktu jam dinding.
- **`gap_flag`:** `ok`, `ts_mundur` (baris pertama setelah waktu mundur), `ts_ganda` (timestamp yang sudah pernah muncul), `celah` (selisih lebih dari 5 menit; tidak ada di data ini).
- Data tidak dibuang atau diubah: baris yang ditandai tetap dipakai.

## Jendela anomali
- **Jendela berlabel:** rentang waktu dari `labels/combined_windows.json` NAB v1.1, empat jendela, sekitar 48 jam masing-masing.
- **Waktu kegagalan (perkiraan) = titik tengah jendela.** NAB menyusun jendela mengelilingi kejadian; titik tengah dipakai sebagai pendekatan. Ini asumsi, bukan waktu kegagalan sebenarnya.

## Fitur bergulir (view SQL `features`)
- **Jendela rata-rata = 288 titik sebelum titik sekarang** (24 jam, titik sekarang tidak ikut), diurutkan menurut `seq`. Fitur kosong untuk 288 titik pertama (warm-up).
- `roll_mean_24h`, `roll_std_24h` (simpangan baku sampel), `z_score = (value - roll_mean_24h) / roll_std_24h`, `dev_mean = value - roll_mean_24h`.
- `slope_6h`: kemiringan regresi linear 72 titik terakhir (6 jam), dalam derajat per jam.

## Alarm
- **Titik melampaui ambang:** skor titik lebih besar dari ambang.
  - Ambang tetap: `|value - median data latih| > h` derajat.
  - Rolling z-score: `|z_score| > ambang`.
  - Isolation Forest: skor anomali (`-score_samples`) di atas ambang, yaitu persentil tertentu dari skor data latih.
- **Syarat persistence k:** alarm menyala jika k titik berturut-turut melampaui ambang (k = 1, 3, atau 6).
- **Episode alarm:** deretan titik alarm yang berjarak paling lama 12 titik (1 jam) dihitung satu alarm. Waktu episode = titik pertama alarm menyala.
- **Kejadian terdeteksi:** minimal satu episode mulai di dalam jendela berlabel (dari awal sampai akhir jendela).
- **Peringatan dini:** episode pertama di dalam jendela muncul sebelum titik tengah jendela.
- **Alarm palsu:** episode yang mulai di luar semua jendela berlabel. Catatan: titik di luar jendela belum tentu normal; NAB hanya melabeli empat kejadian, jadi sebagian "alarm palsu" bisa gangguan nyata yang tidak dilabeli.
- **Lead time (jam) = waktu tengah jendela dikurangi waktu episode pertama di dalam jendela.** Negatif berarti alarm baru menyala setelah perkiraan waktu kegagalan.
- **Recall per kejadian = kejadian terdeteksi / jumlah kejadian.** **Precision (tingkat episode) = episode di dalam jendela / semua episode.** **Alarm palsu per minggu = alarm palsu / lama periode evaluasi dalam minggu.** Akurasi per titik tidak dipakai karena hampir semua titik normal.

## Pemisahan waktu (tanpa kebocoran)
- **Data latih:** sebelum 2014-01-01 (dua kejadian pertama). **Data uji:** sejak 2014-01-01 (dua kejadian terakhir).
- Pusat ambang tetap, model Isolation Forest, dan ambang persentil Isolation Forest hanya memakai data latih. Ambang dan persistence dipilih dari data latih saja, lalu diuji pada data uji.
- **Aturan pemilihan:** dari konfigurasi dengan alarm palsu per minggu pada data latih tidak lebih dari batas, pilih yang mendeteksi kejadian terbanyak; lalu alarm palsu paling sedikit; lalu lead time rata-rata terbesar.
- **Batas alarm palsu = 2 per minggu** (asumsi; belum disepakati dengan tim maintenance). Sensitivitas batas 1 dan 5 per minggu ada di `results/2-analysis/selection_limits.csv`.

## Dampak (estimated)
- Kegagalan per tahun diekstrapolasi dari 4 kejadian dalam rentang data (kurang dari 3 bulan).
- Downtime darurat per kegagalan 4, 8, atau 12 jam (asumsi). Peringatan dianggap berguna jika lead time minimal 2 jam (asumsi).
- Jam downtime yang bisa dicegah = kegagalan per tahun x proporsi kejadian dengan peringatan cukup x downtime per kegagalan. Semua angka dampak berlabel `estimated`.
