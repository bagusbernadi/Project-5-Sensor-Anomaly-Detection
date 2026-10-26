"""Profil data (Q1, Q2): kualitas timestamp, pola harian dan mingguan, rentang suhu normal.
Menulis data/clean/sensor_readings.csv (urutan baris asli + gap_flag) dan CSV profil di results/1-data-preparation/."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

C.CLEAN_DIR.mkdir(parents=True, exist_ok=True)
d = pd.read_csv(C.RAW_CSV, parse_dates=["timestamp"]).rename(columns={"timestamp": "ts"})
d.insert(0, "seq", np.arange(1, len(d) + 1))                      # urutan baris asli = kunci pengurutan
step = d.ts.diff()
back = step < pd.Timedelta(0)
dup = d.ts.duplicated(keep="first")
d["gap_flag"] = np.where(back, "ts_mundur", np.where(dup, "ts_ganda", np.where(step > pd.Timedelta(minutes=5), "celah", "ok")))
d.loc[0, "gap_flag"] = "ok"
d.to_csv(C.CLEAN_DIR / "sensor_readings.csv", index=False)

win = json.loads(C.RAW_LABELS.read_text())[C.NAB_LABEL_KEY]
wdf = pd.DataFrame([dict(window_id=i + 1, start_ts=a, end_ts=b, source=f"NAB {C.NAB_TAG} combined_windows.json") for i, (a, b) in enumerate(win)])
wdf["start_ts"] = pd.to_datetime(wdf.start_ts)
wdf["end_ts"] = pd.to_datetime(wdf.end_ts)
wdf.to_csv(C.CLEAN_DIR / "anomaly_windows.csv", index=False)
inwin = np.zeros(len(d), bool)
for a, b in zip(wdf.start_ts, wdf.end_ts):
    inwin |= ((d.ts >= a) & (d.ts <= b)).values
d["in_window"] = inwin
norm = d[~d.in_window]                                             # statistik "normal" memakai titik di luar jendela berlabel

# kualitas data (Q2)
expected_steps = (step.dropna() == pd.Timedelta(minutes=5)).sum()
jump = d.loc[back].index[0]
q = [("titik data (baris)", len(d)), ("timestamp pertama", str(d.ts.min())), ("timestamp terakhir", str(d.ts.max())),
     ("rentang (hari)", round((d.ts.max() - d.ts.min()).total_seconds() / 86400, 2)),
     ("interval 5 menit normal", int(expected_steps)), ("celah waktu (> 5 menit)", int((step > pd.Timedelta(minutes=5)).sum())),
     ("timestamp mundur", int(back.sum())), ("mundur sebesar (menit)", int(-step[back].iloc[0].total_seconds() / 60)),
     ("timestamp ganda (kemunculan kedua)", int(dup.sum())), ("tanggal timestamp mundur", str(d.loc[jump, "ts"])[:16]),
     ("nilai kosong", int(d.value.isna().sum())), ("suhu minimum", round(d.value.min(), 2)), ("suhu maksimum", round(d.value.max(), 2)),
     ("titik dengan suhu di bawah 30", int((d.value < 30).sum())), ("jendela anomali berlabel", len(wdf)),
     ("titik di dalam jendela berlabel", int(d.in_window.sum()))]
pd.DataFrame(q, columns=["ukuran", "nilai"]).to_csv(C.RES_PREP / "data_quality.csv", index=False)

# pola harian dan mingguan (Q1), dari titik di luar jendela berlabel
h = norm.groupby(norm.ts.dt.hour).value.agg(mean="mean", std="std", p05=lambda s: s.quantile(.05), p95=lambda s: s.quantile(.95), n="size").reset_index().rename(columns={"ts": "hour"})
h.to_csv(C.RES_PREP / "profile_hour.csv", index=False)
w = norm.groupby(norm.ts.dt.dayofweek).value.agg(mean="mean", std="std", n="size").reset_index().rename(columns={"ts": "dow"})
w["hari"] = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
w.to_csv(C.RES_PREP / "profile_dow.csv", index=False)
daily = d.groupby(d.ts.dt.date).value.agg(mean="mean", min="min", max="max", n="size").reset_index().rename(columns={"ts": "date"})
daily.to_csv(C.RES_PREP / "daily_stats.csv", index=False)


def eta2(g):                                                         # porsi varians yang dijelaskan faktor g
    tot = ((norm.value - norm.value.mean()) ** 2).sum()
    return float(sum(len(s) * (s.mean() - norm.value.mean()) ** 2 for _, s in norm.value.groupby(g)) / tot)


s = [("suhu rata-rata (di luar jendela)", norm.value.mean()), ("simpangan baku", norm.value.std()), ("median", norm.value.median()),
     ("persentil 5", norm.value.quantile(.05)), ("persentil 95", norm.value.quantile(.95)),
     ("rata-rata - 2 simpangan baku", norm.value.mean() - 2 * norm.value.std()), ("rata-rata + 2 simpangan baku", norm.value.mean() + 2 * norm.value.std()),
     ("selisih rata-rata jam tertinggi dan terendah", h["mean"].max() - h["mean"].min()),
     ("varians dijelaskan jam dalam sehari (eta^2)", eta2(norm.ts.dt.hour)), ("varians dijelaskan hari dalam minggu (eta^2)", eta2(norm.ts.dt.dayofweek)),
     ("rata-rata dalam jendela berlabel", d[d.in_window].value.mean()), ("rata-rata harian: min", daily["mean"].min()), ("rata-rata harian: maks", daily["mean"].max())]
pd.DataFrame(s, columns=["ukuran", "nilai"]).to_csv(C.RES_PREP / "profile_summary.csv", index=False)
print(pd.DataFrame(q).to_string()); print(pd.DataFrame(s).round(3).to_string())
