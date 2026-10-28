[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 5: Sensor Time-Series Anomaly Detection

**Status: Selesai di branch `project-5-build` (menunggu review sebelum digabung ke `main`).**

Halaman rancangan dan Report: https://bagusbernadi.github.io/Project-5-Sensor-Anomaly-Detection/

| | |
|---|---|
| Kategori | Manufaktur (sensor mesin industri) |
| Tingkat | Menengah |
| Data | Dataset publik NAB v1.1, `machine_temperature_system_failure` (repositori berlisensi AGPL v3) |
| Tools | SQL (DuckDB), Python (pandas, NumPy, scikit-learn, statsmodels), Jupyter, Streamlit + Plotly, GitHub |

## 1. Problem

Kapan alarm suhu harus berbunyi agar kegagalan mesin bisa ditangkap lebih awal, dengan alarm palsu yang masih bisa diterima? Dipecah menjadi 12 pertanyaan (8 prioritas utama); jawabannya ada di tab Report pada halaman project.

## 2. Data

- 22.695 titik suhu satu mesin, interval 5 menit, 79 hari, 4 jendela anomali berlabel NAB.
- Sumber: [NAB v1.1](https://github.com/numenta/NAB/tree/v1.1), tanggal akses 25 Oktober 2026. Data tidak di-commit; `01_download_data.py` mengunduhnya (lihat `project/data/README.md`).
- Tidak ada celah waktu. Ada 1 timestamp mundur (55 menit) dan 12 timestamp ganda; ditandai di `gap_flag`, jendela bergulir mengikuti urutan baris.

## 3. Analysis

- Pola harian lemah: jam dalam sehari hanya menjelaskan 1,3% variasi suhu.
- Tiga metode dibandingkan: ambang tetap, rolling z-score (288 titik, window function SQL), dan Isolation Forest (5 kombinasi fitur). Ambang dan model dipilih dari data sebelum 2014-01-01 saja, diuji pada data sesudahnya.
- Aturan terpilih: ambang tetap ±35 derajat dari median, 6 titik berturut-turut: **4 dari 4 kejadian** terdeteksi, **0,45 alarm palsu per minggu** (uji: 0,70), lead time rata-rata 13,3 jam.
- Pembanding: rolling z-score 3 dari 4 kejadian dengan 3,06 per minggu; Isolation Forest (value+z+std) 4 dari 4 dengan 1,26 per minggu. Isolation Forest dengan suhu saja memberi 4 dari 4 kejadian lebih awal (0,72 per minggu), jadi selisih dengan aturan sederhana belum cukup sebagai bukti.
- Validasi: 8 pemeriksaan kebocoran data masa depan PASS; 7 pemeriksaan fitur dan 996 pemeriksaan alarm SQL vs pandas PASS.

## 4. Recommendation

Mulai dari aturan ambang tetap sebagai alarm awal, sepakati batas alarm palsu dengan tim maintenance, dan periksa alarm di luar jendela terhadap catatan operasional. Pakai Isolation Forest hanya jika data lebih banyak tersedia. Laporkan kinerja per kejadian, bukan akurasi per titik.

## 5. Impact

Estimated: sekitar 56 sampai 167 jam downtime per tahun bisa dicegah (asumsi 4 sampai 12 jam per kegagalan; 3 dari 4 kejadian mendapat peringatan minimal 2 jam; kegagalan per tahun diekstrapolasi dari 4 kejadian).

## Batasan

- Hanya 4 kejadian (2 latih, 2 uji): satu kejadian mengubah recall 25 poin; hasil indikatif.
- Titik tengah jendela dipakai sebagai perkiraan waktu kegagalan; alarm di luar jendela belum tentu palsu (NAB hanya melabeli 4 kejadian).
- Batas alarm palsu 2 per minggu dan downtime per kegagalan adalah asumsi. Satu mesin tidak mewakili semua mesin.
- Dashboard belum di-deploy.

## Menjalankan

```
pip install -r project/requirements.txt
cd project/code/1-data-preparation/python && python 01_download_data.py && python 02_profile_data.py && python 03_build_db.py
cd ../../2-analysis/python && for s in 04 05 06 07 08; do python ${s}_*.py; done
cd ../../3-presentation/python && for s in 09 10 11 12; do python ${s}_*.py; done
streamlit run ../streamlit/app.py
python design-and-report/src/build_report.py   # dari root repo
```

## Struktur repository

```
index.html                 Pengalihan ke design-and-report/
design-and-report/         Halaman Design dan Report (src/ berisi generator)
project/
  code/1-data-preparation  Unduh data, profil, database (python, sql)
  code/2-analysis          Fitur SQL, evaluasi metode, pemilihan ambang, lead time
  code/3-presentation      Data dashboard, aturan alarm, notebook, Streamlit
  results/                 CSV hasil per tahap, aturan alarm, notebook
  docs/                    Definisi dan kamus data
  data/                    README sumber data (data mentah dan bersih tidak di-commit)
```
