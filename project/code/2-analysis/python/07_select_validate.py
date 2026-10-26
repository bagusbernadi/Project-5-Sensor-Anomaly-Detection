"""Memilih ambang HANYA dari data latih (sebelum TRAIN_END), menguji pada data sesudahnya, dan memvalidasi evaluasi:
pemisahan waktu (Q11), cek silang hasil Python vs SQL pada tabel alarms (Q12), sensitivitas batas alarm palsu dan margin jendela."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from alarm_lib import build_scores, connect, evaluate, load, periods, run_grid, select_on_train  # noqa: E402

C.chdir_root()
con = connect()
f, w = load(con)
P = periods(f)
ev = pd.read_csv(C.RES_ANALYSIS / "method_evaluation.csv")
KEY = ["method", "feature_set", "threshold", "persistence"]


def cfg_rows(r):
    m = ev
    for k in KEY:
        m = m[(m[k] - r[k]).abs() < 1e-9] if k in ("threshold", "persistence") else m[m[k] == r[k]]
    return m.set_index("period")


def wide(sel):
    out = []
    for _, r in sel.iterrows():
        g = cfg_rows(r)
        d = dict(method=r.method, feature_set=r.feature_set, threshold=r.threshold, persistence=r.persistence)
        for p in ("train", "test", "all"):
            for c in ("events_total", "events_detected", "events_early", "episodes", "false_alarms", "fa_per_week", "precision", "lead_mean_h", "lead_min_h"):
                d[f"{c}_{p}"] = g.loc[p, c]
        out.append(d)
    return pd.DataFrame(out)


# 1. seleksi utama (batas FA_LIMIT) -------------------------------------------------
sel = select_on_train(ev, C.FA_LIMIT)
sw = wide(sel)
sw.to_csv(C.RES_ANALYSIS / "selection.csv", index=False)
# metode terbaik per kelompok (Isolation Forest dipilih dari kumpulan fitur menurut data latih saja)
order = ["events_detected_train", "fa_per_week_train", "lead_mean_h_train"]
sw["_lead"] = sw.lead_mean_h_train.fillna(-1e9)
best = (sw.sort_values(["method", "events_detected_train", "fa_per_week_train", "_lead"], ascending=[True, False, True, False]).groupby("method", as_index=False).head(1)).drop(columns="_lead")
best.to_csv(C.RES_ANALYSIS / "selection_best_per_method.csv", index=False)
final = best.assign(_lead=best.lead_mean_h_train.fillna(-1e9)).sort_values(["events_detected_train", "fa_per_week_train", "_lead"], ascending=[False, True, False]).iloc[0]
final = final.drop(labels="_lead")
pd.DataFrame([final]).to_csv(C.RES_ANALYSIS / "final_rule.csv", index=False)

# 2. sensitivitas batas alarm palsu -------------------------------------------------
rows = []
for lim in C.FA_LIMITS_SENS:
    s = wide(select_on_train(ev, lim))
    s["_lead"] = s.lead_mean_h_train.fillna(-1e9)
    b = s.sort_values(["method", "events_detected_train", "fa_per_week_train", "_lead"], ascending=[True, False, True, False]).groupby("method", as_index=False).head(1)
    for _, r in b.iterrows():
        rows.append(dict(batas_fa_per_minggu=lim, **{k: r[k] for k in ["method", "feature_set", "threshold", "persistence", "events_detected_train", "fa_per_week_train",
                                                                       "events_detected_test", "fa_per_week_test", "events_detected_all", "fa_per_week_all", "lead_mean_h_all"]}))
pd.DataFrame(rows).to_csv(C.RES_ANALYSIS / "selection_limits.csv", index=False)

# 3. persistence (Q8): ambang terpilih tiap metode, k = 1, 3, 6 --------------------
rows = []
for _, r in best.iterrows():
    for k in C.K_LIST:
        g = cfg_rows(r.to_dict() | {"persistence": k})
        for p in ("train", "test", "all"):
            x = g.loc[p]
            rows.append(dict(method=r.method, feature_set=r.feature_set, threshold=r.threshold, persistence=k, period=p, events_detected=x.events_detected, events_total=x.events_total,
                             false_alarms=x.false_alarms, fa_per_week=x.fa_per_week, lead_mean_h=x.lead_mean_h))
pd.DataFrame(rows).to_csv(C.RES_ANALYSIS / "persistence.csv", index=False)

# 4. z-score per kejadian (Q3) dan detail kejadian untuk aturan terbaik tiap metode ----
al = con.execute("SELECT * FROM alarms ORDER BY alarm_id").df()


def episodes_of(method, fs, thr, k):
    m = al[(al.method == method) & (al.feature_set == fs) & ((al.threshold - thr).abs() < 1e-9) & (al.persistence == k)]
    return m.ts.sort_values().reset_index(drop=True)


def event_table(method, fs, thr, k, margin=0.0):
    ep = episodes_of(method, fs, thr, k)
    out = []
    for r in w.itertuples():
        a, b = r.start_ts - pd.Timedelta(hours=margin), r.end_ts
        hit = ep[(ep >= a) & (ep <= b)]
        first = hit.min() if len(hit) else pd.NaT
        out.append(dict(window_id=r.window_id, window_start=r.start_ts, window_mid=r.mid_ts, window_end=r.end_ts, detected=bool(len(hit)),
                        first_alarm=first, lead_h=(r.mid_ts - first).total_seconds() / 3600 if len(hit) else np.nan))
    return pd.DataFrame(out)


zr = []
for thr in (2.0, 3.0, 4.0, 5.0):
    t = event_table("zscore", "-", thr, 3)
    for r in t.itertuples():
        zr.append(dict(threshold=thr, window_id=r.window_id, detected=r.detected, lead_h=r.lead_h))
pd.DataFrame(zr).to_csv(C.RES_ANALYSIS / "zscore_events.csv", index=False)
det = []
for _, r in best.iterrows():
    t = event_table(r.method, r.feature_set, r.threshold, int(r.persistence))
    t.insert(0, "method", r.method); t.insert(1, "feature_set", r.feature_set)
    det.append(t)
pd.concat(det).to_csv(C.RES_ANALYSIS / "event_detail.csv", index=False)

# 5. sensitivitas margin jendela -----------------------------------------------------
rows = []
for _, r in best.iterrows():
    ep = episodes_of(r.method, r.feature_set, r.threshold, int(r.persistence))
    for mh in C.MARGINS_H:
        e = evaluate(ep.values, w, P["all"][0], P["all"][1], margin_h=mh)
        rows.append(dict(method=r.method, feature_set=r.feature_set, margin_h=mh, events_detected=e["events_detected"], false_alarms=e["false_alarms"],
                         fa_per_week=e["fa_per_week"], lead_mean_h=e["lead_mean_h"], events_early=e["events_early"]))
pd.DataFrame(rows).to_csv(C.RES_ANALYSIS / "margin_sensitivity.csv", index=False)

# 6. cek silang: hasil Python vs SQL pada tabel alarms (Q12) ----------------------------
sqlv = con.execute("SELECT * FROM v_alarm_eval").df()
allp = ev[ev.period == "all"]
rows = []
for r in allp.itertuples():
    m = sqlv[(sqlv.method == r.method) & (sqlv.feature_set == r.feature_set) & ((sqlv.threshold - r.threshold).abs() < 1e-9) & (sqlv.persistence == r.persistence)]
    s = m.iloc[0] if len(m) else dict(episodes=0, episodes_in_window=0, false_alarms=0, events_detected=0)
    for name, a, b in (("episode", r.episodes, s["episodes"]), ("episode dalam jendela", r.episodes_in_window, s["episodes_in_window"]),
                       ("alarm palsu", r.false_alarms, s["false_alarms"]), ("kejadian terdeteksi", r.events_detected, s["events_detected"])):
        rows.append(dict(metode=r.method, fitur=r.feature_set, ambang=r.threshold, persistence=r.persistence, ukuran=name, python=int(a), sql=int(b), status="PASS" if int(a) == int(b) else "FAIL"))
cx = pd.DataFrame(rows)
cx.to_csv(C.RES_ANALYSIS / "crosscheck_alarms.csv", index=False)
assert (cx.status == "PASS").all(), cx[cx.status == "FAIL"].head()

# 7. uji kebocoran waktu (Q11): ulangi seluruh seleksi hanya dengan data sebelum TRAIN_END ----
te = pd.Timestamp(C.TRAIN_END)
f_tr = f[f.ts < te].reset_index(drop=True)
sc_tr, center_tr = build_scores(f_tr, C.TRAIN_END)
ev_tr, _ = run_grid(f_tr, w, sc_tr, {"train": (f_tr.ts.min(), te)})
sel_tr = select_on_train(ev_tr, C.FA_LIMIT)
rows = []
for _, r in sel.iterrows():
    m = sel_tr[(sel_tr.method == r.method) & (sel_tr.feature_set == r.feature_set)].iloc[0]
    same = abs(m.threshold - r.threshold) < 1e-9 and m.persistence == r.persistence
    rows.append(dict(method=r.method, feature_set=r.feature_set, ambang_data_lengkap=r.threshold, persistence_data_lengkap=r.persistence,
                     ambang_hanya_data_latih=m.threshold, persistence_hanya_data_latih=m.persistence, status="PASS" if same else "FAIL"))
lk = pd.DataFrame(rows)
lk.loc[len(lk)] = dict(method="(semua)", feature_set="data terakhir yang dipakai memilih", ambang_data_lengkap=np.nan, persistence_data_lengkap=np.nan, ambang_hanya_data_latih=np.nan,
                       persistence_hanya_data_latih=np.nan, status="PASS" if f_tr.ts.max() < te else "FAIL")
lk["ts_terakhir_data_latih"] = str(f_tr.ts.max())
lk.to_csv(C.RES_ANALYSIS / "leakage_check.csv", index=False)
assert (lk.status == "PASS").all(), lk
print(final.to_string())
print(best[["method", "feature_set", "threshold", "persistence", "events_detected_train", "fa_per_week_train", "events_detected_test", "fa_per_week_test", "lead_mean_h_all"]].round(2).to_string())
print("crosscheck alarms:", len(cx), "PASS; kebocoran:", (lk.status == "PASS").sum(), "PASS")
