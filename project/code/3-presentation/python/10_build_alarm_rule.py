"""Aturan alarm usulan (alarm_rule.md) dan gambarnya; semua angka dari CSV hasil."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

fr = pd.read_csv(C.result("final_rule.csv")).iloc[0]
s = pd.read_csv(C.result("dash_series.csv"), parse_dates=["ts"])
w = pd.read_csv(C.result("dash_windows.csv"), parse_dates=["start_ts", "end_ts", "mid_ts"])
a = pd.read_csv(C.result("dash_alarms.csv"), parse_dates=["ts"])
a = a[a.label == "Ambang tetap"]
ed = pd.read_csv(C.result("event_detail.csv"))
ed = ed[ed.method == "fixed"]

fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(s.ts, s.value, color="#5f6368", lw=0.6)
for r in w.itertuples():
    ax.axvspan(r.start_ts, r.end_ts, color="#d93025", alpha=0.15)
    ax.axvline(r.mid_ts, color="#d93025", ls=":", lw=1)
sv = s.set_index("seq").value
for ok, mk, nm in ((True, "^", "alarm di jendela"), (False, "x", "alarm di luar jendela")):
    d = a[a.in_window == ok]
    ax.scatter(d.ts, sv.loc[d.seq].values, marker=mk, s=45, color="#1a73e8", label=nm, zorder=3)
ax.set_ylabel("Suhu"); ax.legend(loc="lower left"); ax.set_title("Aturan usulan: ambang tetap, 6 titik berturut-turut")
fig.tight_layout(); fig.savefig(C.RES_PRESENT / "alarm_rule.png", dpi=130); plt.close(fig)

f = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")
rows = "\n".join(f"| {int(r.window_id)} | {r.window_mid} | {r.first_alarm} | {f(r.lead_h, 1)} |" for r in ed.itertuples())
md = f"""# Aturan alarm usulan

**Aturan:** kirim alarm jika suhu menyimpang lebih dari **{fr.threshold:g} derajat** dari median data latih selama **{int(fr.persistence)} titik berturut-turut** (30 menit). Satu episode ditutup setelah 1 jam tanpa alarm.

Ambang dan persistence dipilih dari data sebelum {C.TRAIN_END} saja, dengan batas alarm palsu {f(C.FA_LIMIT)} per minggu (asumsi, belum disepakati dengan tim maintenance).

## Hasil
| Periode | Kejadian terdeteksi | Peringatan dini | Alarm palsu per minggu | Precision (episode) |
|---|---|---|---|---|
| Latih | {int(fr.events_detected_train)} dari {int(fr.events_total_train)} | {int(fr.events_early_train)} | {f(fr.fa_per_week_train, 2)} | {f(fr.precision_train, 2)} |
| Uji | {int(fr.events_detected_test)} dari {int(fr.events_total_test)} | {int(fr.events_early_test)} | {f(fr.fa_per_week_test, 2)} | {f(fr.precision_test, 2)} |
| Semua | {int(fr.events_detected_all)} dari {int(fr.events_total_all)} | {int(fr.events_early_all)} | {f(fr.fa_per_week_all, 2)} | {f(fr.precision_all, 2)} |

## Lead time per kejadian (jam; negatif = setelah perkiraan waktu kegagalan)
| Jendela | Titik tengah (perkiraan kegagalan) | Alarm pertama | Lead time |
|---|---|---|---|
{rows}

![Aturan alarm](alarm_rule.png)

## Alasan dan batasan
- Aturan paling sederhana mengalahkan rolling z-score dan Isolation Forest pada data ini; lihat `results/2-analysis/selection_best_per_method.csv`.
- Hanya 4 kejadian (2 latih, 2 uji): kesimpulan bersifat indikatif, bukan bukti umum.
- "Alarm palsu" adalah alarm di luar jendela berlabel; sebagian bisa gangguan nyata yang tidak dilabeli NAB.
- Titik tengah jendela hanyalah pendekatan waktu kegagalan.
"""
(C.RES_PRESENT / "alarm_rule.md").write_text(md, encoding="utf-8")
print("alarm_rule.md dan alarm_rule.png ditulis")
