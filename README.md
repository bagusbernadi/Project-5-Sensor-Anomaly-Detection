[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 5: Sensor Time-Series Anomaly Detection

**Status: Design (rancangan).**

**Tujuan:** Membangun deteksi anomali pada data suhu mesin yang dicatat setiap 5 menit, untuk menemukan aturan alarm yang memberi peringatan cukup awal sebelum kegagalan dengan jumlah alarm palsu yang masih bisa diterima tim maintenance, sehingga perbaikan bisa dijadwalkan sebelum mesin berhenti.

| | |
|---|---|
| Kategori | Sensor industri / time series |
| Tingkat | Menengah |
| Data | Dataset publik: Numenta Anomaly Benchmark (NAB), machine_temperature_system_failure |
| Tools | DuckDB + SQL, Python (pandas, NumPy, scikit-learn), Jupyter, Streamlit + Plotly |

## 1. Problem
Apakah pola abnormal pada data suhu mesin bisa dideteksi cukup awal sebelum kegagalan, dengan alarm palsu yang masih bisa diterima tim maintenance?

## 2. Data
Numenta Anomaly Benchmark, file `data/realKnownCause/machine_temperature_system_failure.csv` dan label `labels/combined_windows.json`. Sumber data: [here](https://github.com/numenta/NAB/blob/v1.1/data/realKnownCause/machine_temperature_system_failure.csv) (Versi: NAB v1.1, Tanggal akses: 25 Oktober 2026). Lisensi MIT. Sitasi: Lavin, A. & Ahmad, S. (2015). Evaluating Real-time Anomaly Detection Algorithms: the Numenta Anomaly Benchmark. Ukuran: 22.695 titik data, interval 5 menit, 2 Desember 2013 sampai 19 Februari 2014, 4 jendela anomali berlabel (perkiraan, belum diverifikasi terhadap tag v1.1). File data tidak disimpan di repo.

## 3. Analysis
Rencana: profil pola harian, fitur bergulir dengan window function SQL, perbandingan ambang tetap, rolling z-score, dan Isolation Forest (recall per kejadian, precision, alarm palsu per minggu, lead time), pemilihan ambang dengan pemisahan data berdasarkan waktu. Belum dikerjakan.

## 4. Recommendation
Belum dikerjakan.

## 5. Impact
Belum dikerjakan. Angka dampak akan diberi label `estimated` / `simulated`.

## Batasan yang sudah diketahui
- Hanya 4 kejadian berlabel; satu kejadian yang terlewat mengubah recall 25 poin.
- Jendela label NAB adalah rentang, bukan waktu kegagalan pasti.
- Satu sensor dari satu mesin tidak mewakili semua mesin.
- Akurasi menyesatkan karena hampir semua titik normal; evaluasi memakai recall dan alarm palsu per minggu.

## Struktur repository (rencana)
```
docs/            # definisi kejadian, alarm, lead time
data/README.md   # sumber, versi, cara mengunduh
sql/             # pemuatan data dan fitur bergulir
notebooks/       # analisis dan evaluasi metode
outputs/         # evaluasi metode, aturan alarm usulan
dashboard/       # aplikasi Streamlit
index.html       # halaman rancangan (GitHub Pages)
README.md
```
