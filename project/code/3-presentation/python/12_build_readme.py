"""Membuat README.md di root repo; semua angka dibaca dari CSV hasil."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ACCESS_DATE, FA_LIMIT, ROOT, TRAIN_END, result  # noqa: E402

R = lambda n: pd.read_csv(result(n))
f = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")
pc = lambda v, d=0: f(v * 100, d) + "%"
n = lambda v: f"{int(round(float(v))):,}".replace(",", ".")

dq = R("data_quality.csv").set_index("ukuran").nilai
ps = R("profile_summary.csv").set_index("ukuran").nilai.astype(float)
fr = R("final_rule.csv").iloc[0]
best = R("selection_best_per_method.csv").set_index("method")
fx, zs, itf = best.loc["fixed"], best.loc["zscore"], best.loc["iforest"]
imp = R("impact.csv").set_index(["downtime_per_kegagalan_h", "skenario"])
i4, i12 = imp.loc[(4, "titik")], imp.loc[(12, "titik")]
xf, xa, leak, lt = R("crosscheck_features.csv"), R("crosscheck_alarms.csv"), R("leakage_check.csv"), R("lead_time.csv").set_index("method").loc["fixed"]
ifv = R("selection.csv")
ifv = ifv[ifv.method == "iforest"].set_index("feature_set").loc["value"]
eta = ps["varians dijelaskan jam dalam sehari (eta^2)"]

md = f"""[← Back to portfolio](https://bagusbernadi.github.io/)

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

- {n(dq["titik data (baris)"])} titik suhu satu mesin, interval 5 menit, {n(float(dq["rentang (hari)"]))} hari, 4 jendela anomali berlabel NAB.
- Sumber: [NAB v1.1](https://github.com/numenta/NAB/tree/v1.1), tanggal akses {ACCESS_DATE}. Data tidak di-commit; `01_download_data.py` mengunduhnya (lihat `project/data/README.md`).
- Tidak ada celah waktu. Ada {n(dq["timestamp mundur"])} timestamp mundur ({n(dq["mundur sebesar (menit)"])} menit) dan {n(dq["timestamp ganda (kemunculan kedua)"])} timestamp ganda; ditandai di `gap_flag`, jendela bergulir mengikuti urutan baris.

## 3. Analysis

- Pola harian lemah: jam dalam sehari hanya menjelaskan {pc(eta, 1)} variasi suhu.
- Tiga metode dibandingkan: ambang tetap, rolling z-score (288 titik, window function SQL), dan Isolation Forest (5 kombinasi fitur). Ambang dan model dipilih dari data sebelum {TRAIN_END} saja, diuji pada data sesudahnya.
- Aturan terpilih: ambang tetap ±{f(fr.threshold, 0)} derajat dari median, {n(fr.persistence)} titik berturut-turut: **{n(fr.events_detected_all)} dari {n(fr.events_total_all)} kejadian** terdeteksi, **{f(fr.fa_per_week_all, 2)} alarm palsu per minggu** (uji: {f(fr.fa_per_week_test, 2)}), lead time rata-rata {f(fr.lead_mean_h_all, 1)} jam.
- Pembanding: rolling z-score {n(zs.events_detected_all)} dari 4 kejadian dengan {f(zs.fa_per_week_all, 2)} per minggu; Isolation Forest (value+z+std) {n(itf.events_detected_all)} dari 4 dengan {f(itf.fa_per_week_all, 2)} per minggu. Isolation Forest dengan suhu saja memberi {n(ifv.events_early_all)} dari 4 kejadian lebih awal ({f(ifv.fa_per_week_all, 2)} per minggu), jadi selisih dengan aturan sederhana belum cukup sebagai bukti.
- Validasi: {n(len(leak))} pemeriksaan kebocoran data masa depan PASS; {n(len(xf))} pemeriksaan fitur dan {n(len(xa))} pemeriksaan alarm SQL vs pandas PASS.

## 4. Recommendation

Mulai dari aturan ambang tetap sebagai alarm awal, sepakati batas alarm palsu dengan tim maintenance, dan periksa alarm di luar jendela terhadap catatan operasional. Pakai Isolation Forest hanya jika data lebih banyak tersedia. Laporkan kinerja per kejadian, bukan akurasi per titik.

## 5. Impact

Estimated: sekitar {f(i4.jam_downtime_dicegah_per_tahun, 0)} sampai {f(i12.jam_downtime_dicegah_per_tahun, 0)} jam downtime per tahun bisa dicegah (asumsi 4 sampai 12 jam per kegagalan; {n(lt.events_with_lead_ge_min)} dari 4 kejadian mendapat peringatan minimal 2 jam; kegagalan per tahun diekstrapolasi dari 4 kejadian).

## Batasan

- Hanya 4 kejadian (2 latih, 2 uji): satu kejadian mengubah recall 25 poin; hasil indikatif.
- Titik tengah jendela dipakai sebagai perkiraan waktu kegagalan; alarm di luar jendela belum tentu palsu (NAB hanya melabeli 4 kejadian).
- Batas alarm palsu {f(FA_LIMIT, 0)} per minggu dan downtime per kegagalan adalah asumsi. Satu mesin tidak mewakili semua mesin.
- Dashboard belum di-deploy.

## Menjalankan

```
pip install -r project/requirements.txt
cd project/code/1-data-preparation/python && python 01_download_data.py && python 02_profile_data.py && python 03_build_db.py
cd ../../2-analysis/python && for s in 04 05 06 07 08; do python ${{s}}_*.py; done
cd ../../3-presentation/python && for s in 09 10 11 12; do python ${{s}}_*.py; done
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
"""
(ROOT.parent / "README.md").write_text(md, encoding="utf-8")
print("README.md ditulis")
