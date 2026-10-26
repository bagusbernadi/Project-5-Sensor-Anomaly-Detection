"""Lead time dan estimasi dampak (Q9, Q10). Estimasi memakai asumsi eksplisit di common.py dan diberi label estimated."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

C.chdir_root()
final = pd.read_csv(C.RES_ANALYSIS / "final_rule.csv").iloc[0]
det = pd.read_csv(C.RES_ANALYSIS / "event_detail.csv", parse_dates=["window_start", "window_mid", "window_end", "first_alarm"])
dq = pd.read_csv(C.RES_PREP / "data_quality.csv").set_index("ukuran").nilai
span_days = float(dq["rentang (hari)"])
n_events = det.window_id.nunique()

rows = []
for (m, fs), g in det.groupby(["method", "feature_set"]):
    ld = g.lead_h.dropna()
    rows.append(dict(method=m, feature_set=fs, events_total=len(g), events_detected=int(g.detected.sum()), events_with_lead_ge_min=int((g.lead_h >= C.MIN_LEAD_H).sum()),
                     lead_mean_h=ld.mean() if len(ld) else np.nan, lead_median_h=ld.median() if len(ld) else np.nan, lead_min_h=ld.min() if len(ld) else np.nan, lead_max_h=ld.max() if len(ld) else np.nan))
pd.DataFrame(rows).to_csv(C.RES_ANALYSIS / "lead_time.csv", index=False)

g = det[(det.method == final.method) & (det.feature_set == final.feature_set)]
k = int((g.lead_h >= C.MIN_LEAD_H).sum())
lo, hi = proportion_confint(k, n_events, method="wilson")
fail_per_year = n_events * 365.0 / span_days
rows = []
for dh in C.DOWNTIME_H:
    for lab, share in (("titik", k / n_events), ("batas bawah (Wilson 95%)", lo), ("batas atas (Wilson 95%)", hi)):
        rows.append(dict(downtime_per_kegagalan_h=dh, skenario=lab, share_dengan_peringatan=share, kegagalan_per_tahun=fail_per_year, jam_downtime_dicegah_per_tahun=fail_per_year * share * dh))
imp = pd.DataFrame(rows)
imp.to_csv(C.RES_ANALYSIS / "impact.csv", index=False)
print(pd.read_csv(C.RES_ANALYSIS / "lead_time.csv").round(2).to_string())
print(f"kegagalan/tahun (ekstrapolasi {span_days} hari) = {fail_per_year:.1f}; aturan {final.method}: {k}/{n_events} kejadian dengan lead >= {C.MIN_LEAD_H} jam")
print(imp.round(2).to_string())
