"""Membuat dan menjalankan results/3-presentation/analysis.ipynb (Q1-Q12). Notebook hanya membaca CSV hasil."""
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

nb = nbf.v4.new_notebook()
M = lambda t: nb.cells.append(nbf.v4.new_markdown_cell(t))
K = lambda t: nb.cells.append(nbf.v4.new_code_cell(t.strip()))

M("# Project 5: Sensor Time-Series Anomaly Detection\nNotebook membaca CSV hasil (`results/`), tidak menghitung ulang model. Urutan mengikuti 12 pertanyaan pada Design Project.\n\n"
  "Catatan: hanya 4 kejadian berlabel (2 latih, 2 uji), jadi semua kesimpulan indikatif.")
K("""
import pandas as pd, matplotlib.pyplot as plt
pd.set_option("display.width", 160); pd.set_option("display.max_columns", 30)
R1, R2, R3 = "../1-data-preparation/", "../2-analysis/", "./"
def rd(p, **k): return pd.read_csv(p, **k)
""")
M("## Q1. Pola suhu harian dan mingguan, rentang suhu normal")
K("""
print(rd(R1+"profile_summary.csv").to_string(index=False))
h, d = rd(R1+"profile_hour.csv"), rd(R1+"profile_dow.csv")
fig, ax = plt.subplots(1, 2, figsize=(12, 3.5))
ax[0].plot(h.hour, h["mean"]); ax[0].fill_between(h.hour, h.p05, h.p95, alpha=.2); ax[0].set_title("Rata-rata per jam (area = p05-p95)")
ax[1].bar(d.hari, d["mean"]); ax[1].set_title("Rata-rata per hari"); plt.tight_layout(); plt.show()
""")
M("## Q2. Data hilang atau lompatan waktu")
K("""
print(rd(R1+"data_quality.csv").to_string(index=False))
print(rd(R1+"consistency_checks.csv").to_string(index=False))
""")
M("## Q3. Seberapa awal rolling z-score mendeteksi keempat jendela (lead time, jam)")
K("""
z = rd(R2+"zscore_events.csv")
print(z.pivot(index="threshold", columns="window_id", values="lead_h").round(1).to_string())
""")
M("## Q4. Alarm palsu per minggu untuk setiap ambang")
K("""
ev = rd(R2+"method_evaluation.csv"); a = ev[(ev.period == "all") & (ev.persistence == 3)]
fig, ax = plt.subplots(figsize=(7, 4))
for (m, fs), g in a.groupby(["method", "feature_set"]):
    if m != "iforest" or fs == "value+z+std":
        g = g.sort_values("threshold"); ax.plot(range(len(g)), g.fa_per_week, marker="o", label=f"{m} {fs}")
ax.set_yscale("symlog"); ax.set_xlabel("urutan ambang (longgar ke ketat)"); ax.set_ylabel("alarm palsu per minggu"); ax.legend(); plt.show()
""")
M("## Q5. Apakah Isolation Forest lebih baik daripada rolling z-score dan ambang tetap?")
K("""
b = rd(R2+"selection_best_per_method.csv")
print(b[["method","feature_set","threshold","persistence","events_detected_train","events_detected_test","fa_per_week_test","precision_test","events_detected_all","fa_per_week_all","lead_mean_h_all"]].round(2).to_string(index=False))
""")
M("## Q6. Fitur mana yang paling membantu (Isolation Forest)")
K("""
print(rd(R2+"iforest_features.csv").to_string(index=False))
print(b[b.method == "iforest"][["feature_set","events_detected_test","fa_per_week_test","lead_mean_h_all"]].round(2).to_string(index=False))
""")
M("## Q7. Ambang yang menangkap kejadian dengan alarm palsu di bawah batas")
K("""
print(rd(R2+"selection_limits.csv").round(2).to_string(index=False))
print(rd(R2+"final_rule.csv").T.to_string(header=False))
""")
M("## Q8. Berapa titik berturut-turut sebelum alarm dikirim (persistence)")
K("""
p = rd(R2+"persistence.csv"); print(p[p.period == "all"].round(2).to_string(index=False))
""")
M("## Q9. Peringatan dini rata-rata dan minimum (jam)")
K("""
print(rd(R2+"lead_time.csv").round(2).to_string(index=False))
e = rd(R2+"event_detail.csv"); print(e[e.method == "fixed"].round(2).to_string(index=False))
print(rd(R2+"margin_sensitivity.csv").round(2).to_string(index=False))
""")
M("## Q10. Jam downtime yang bisa dicegah per tahun (estimated)")
K("""
print(rd(R2+"impact.csv").round(2).to_string(index=False))
""")
M("## Q11. Apakah evaluasi bocor ke masa depan")
K("""
print(rd(R2+"leakage_check.csv").to_string(index=False))
""")
M("## Q12. Statistik bergulir SQL sama dengan pandas")
K("""
print(rd(R2+"crosscheck_features.csv").to_string(index=False))
c = rd(R2+"crosscheck_alarms.csv"); print(c.status.value_counts().to_string())
""")
M("## Aturan alarm usulan")
K("""
from IPython.display import Markdown, Image, display
display(Markdown(open(R3+"alarm_rule.md", encoding="utf-8").read().replace("![Aturan alarm](alarm_rule.png)", "")))
display(Image(R3+"alarm_rule.png"))
""")

out = C.RES_PRESENT / "analysis.ipynb"
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(C.RES_PRESENT)}}).execute()
errs = [o for c in nb.cells if c.cell_type == "code" for o in c.outputs if o.output_type == "error"]
assert not errs, errs
nbf.write(nb, out)
print("notebook:", len(nb.cells), "sel, 0 error")
