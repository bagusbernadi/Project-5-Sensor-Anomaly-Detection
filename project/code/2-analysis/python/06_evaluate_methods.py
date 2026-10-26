"""Evaluasi tiga metode (ambang tetap, rolling z-score, Isolation Forest) untuk banyak ambang dan syarat titik berturut-turut.
Isolation Forest dilatih hanya pada data sebelum TRAIN_END. Semua episode alarm disimpan di tabel alarms (DuckDB);
ringkasan per konfigurasi dan periode ditulis ke results/2-analysis/method_evaluation.csv."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from alarm_lib import FEATURE_SETS, build_scores, connect, load, periods, run_grid  # noqa: E402

C.chdir_root()
con = connect(read_only=False)
f, w = load(con)
P = periods(f)
scores, center = build_scores(f, C.TRAIN_END)
ev, al = run_grid(f, w, scores, P)
ev.to_csv(C.RES_ANALYSIS / "method_evaluation.csv", index=False)

# simpan episode ke tabel alarms (view SQL v_alarm_eval dipakai 07 untuk memeriksa hasil Python)
con.execute("DELETE FROM alarms")
al.insert(0, "alarm_id", np.arange(1, len(al) + 1))
con.register("al", al)
con.execute("INSERT INTO alarms SELECT alarm_id, method, feature_set, threshold, persistence, seq, ts, score, window_id, in_window FROM al")
con.close()
pd.DataFrame(list(FEATURE_SETS.items()), columns=["feature_set", "kolom"]).assign(kolom=lambda d: d.kolom.map(", ".join)).to_csv(C.RES_ANALYSIS / "iforest_features.csv", index=False)
print(len(ev), "baris evaluasi;", len(al), "episode alarm; pusat ambang tetap", round(center, 2))
print(ev[(ev.period == "all") & (ev.method == "zscore") & (ev.persistence == 3)][["threshold", "events_detected", "episodes", "false_alarms", "fa_per_week", "lead_mean_h"]].round(2).to_string())
