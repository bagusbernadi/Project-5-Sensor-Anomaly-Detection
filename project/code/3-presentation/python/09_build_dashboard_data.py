"""Data kecil untuk dashboard dan notebook: deret suhu, jendela, alarm tiap metode terpilih, grid simulasi ambang."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "2-analysis" / "python"))
import common as C  # noqa: E402
import alarm_lib as A  # noqa: E402

C.RES_PRESENT.mkdir(parents=True, exist_ok=True)
con = A.connect()
series = con.execute("SELECT seq, ts, value FROM sensor_readings ORDER BY seq").df()
series.to_csv(C.RES_PRESENT / "dash_series.csv", index=False)
w = con.execute("SELECT window_id, start_ts, end_ts FROM anomaly_windows ORDER BY window_id").df()
w["mid_ts"] = w.start_ts + (w.end_ts - w.start_ts) / 2
w.to_csv(C.RES_PRESENT / "dash_windows.csv", index=False)

best = pd.read_csv(C.result("selection_best_per_method.csv"))
best = best[(best.method != "iforest") | (best.feature_set == "value+z+std")]
al = con.execute("SELECT method, feature_set, threshold, persistence, seq, ts, score, window_id, in_window FROM alarms").df()
parts = []
for r in best.itertuples():
    m = al[(al.method == r.method) & (al.feature_set == r.feature_set) & (al.persistence == r.persistence)
           & ((al.threshold - r.threshold).abs() < 1e-9)]
    parts.append(m.assign(label={"fixed": "Ambang tetap", "zscore": "Rolling z-score", "iforest": "Isolation Forest"}[r.method]))
pd.concat(parts).to_csv(C.RES_PRESENT / "dash_alarms.csv", index=False)

ev = pd.read_csv(C.result("method_evaluation.csv"))
sim = ev[(ev.method == "fixed") & (ev.period == "all")][
    ["threshold", "persistence", "events_total", "events_detected", "events_early", "episodes", "false_alarms", "fa_per_week", "lead_mean_h"]]
sim.to_csv(C.RES_PRESENT / "dash_threshold_sim.csv", index=False)
print("dash:", len(series), "titik,", sum(len(p) for p in parts), "alarm,", len(sim), "baris simulasi")
