"""Fungsi bersama untuk evaluasi alarm (dipakai 06, 07, 08, dashboard dan notebook)."""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

FEATURE_SETS = {
    "value": ["value"],
    "value+z": ["value", "z_score"],
    "value+z+std": ["value", "z_score", "roll_std_24h"],
    "value+z+slope": ["value", "z_score", "slope_6h"],
    "semua fitur": ["value", "z_score", "roll_std_24h", "slope_6h", "dev_mean"],
}


def connect(read_only=True):
    return duckdb.connect(str(C.DB_PATH), read_only=read_only)


def load(con):
    """Fitur dari view SQL (hanya titik setelah warm-up) dan jendela berlabel."""
    f = con.execute("SELECT * FROM features WHERE z_score IS NOT NULL ORDER BY seq").df()
    w = con.execute("SELECT * FROM anomaly_windows ORDER BY window_id").df()
    w["mid_ts"] = w.start_ts + (w.end_ts - w.start_ts) / 2          # perkiraan waktu kegagalan = tengah jendela
    f["window_id"] = np.nan
    for r in w.itertuples():
        f.loc[(f.ts >= r.start_ts) & (f.ts <= r.end_ts), "window_id"] = r.window_id
    return f, w


def episode_starts(exceed, k, cooldown=C.COOLDOWN):
    """exceed: array bool per titik. Alarm menyala jika terlampaui k titik berturut-turut; satu episode ditutup
    setelah `cooldown` titik tanpa alarm. Mengembalikan indeks posisi awal tiap episode."""
    e = np.asarray(exceed, bool)
    run = np.zeros(len(e), int)
    c = 0
    for i, x in enumerate(e):
        c = c + 1 if x else 0
        run[i] = c
    on = np.flatnonzero(run >= k)
    if len(on) == 0:
        return np.array([], int)
    new = np.r_[True, np.diff(on) > cooldown]
    return on[new]


def assign_window(ts, w, margin_h=0.0):
    """window_id untuk setiap timestamp: di dalam jendela, atau sampai margin_h jam sebelum awal jendela."""
    out = []
    m = pd.Timedelta(hours=margin_h)
    for t in ts:
        hit = np.nan
        for r in w.itertuples():
            if r.start_ts - m <= t <= r.end_ts:
                hit = r.window_id
                break
        out.append(hit)
    return np.array(out, float)


def evaluate(ep_ts, w, period_start, period_end, margin_h=0.0):
    """Ringkasan untuk satu periode. ep_ts = timestamp awal episode alarm (sudah dibatasi pada periode)."""
    ep_ts = pd.to_datetime(pd.Series(ep_ts))
    ev = w[(w.start_ts >= period_start) & (w.start_ts < period_end)]
    wid = assign_window(ep_ts, ev, margin_h) if len(ep_ts) else np.array([])
    ins = ~np.isnan(wid)
    leads = []
    for r in ev.itertuples():
        hits = ep_ts[(wid == r.window_id)] if len(ep_ts) else ep_ts
        leads.append((r.mid_ts - hits.min()).total_seconds() / 3600 if len(hits) else np.nan)
    leads = np.array(leads, float)
    det = ~np.isnan(leads)
    weeks = max((period_end - period_start).total_seconds() / 604800, 1e-9)
    n_fa = int((~ins).sum()) if len(ep_ts) else 0
    return dict(events_total=len(ev), events_detected=int(det.sum()), events_early=int((leads > 0).sum()),
                episodes=int(len(ep_ts)), episodes_in_window=int(ins.sum()), false_alarms=n_fa, weeks=round(weeks, 3),
                fa_per_week=n_fa / weeks, lead_mean_h=float(np.nanmean(leads)) if det.any() else np.nan,
                lead_min_h=float(np.nanmin(leads)) if det.any() else np.nan, leads=leads, event_ids=ev.window_id.values)


def periods(f):
    t0, t1 = f.ts.min(), f.ts.max() + pd.Timedelta(minutes=5)
    te = pd.Timestamp(C.TRAIN_END)
    return {"all": (t0, t1), "train": (t0, te), "test": (te, t1)}


QS = [0.90, 0.93, 0.95, 0.96, 0.97, 0.98, 0.985, 0.99, 0.995, 0.999]


def build_scores(f, train_end):
    """Skor per metode. Pusat ambang tetap dan model Isolation Forest hanya memakai data sebelum train_end."""
    from sklearn.ensemble import IsolationForest
    tr = f[f.ts < pd.Timestamp(train_end)]
    center = float(tr.value.median())
    scores = {("fixed", "-"): (np.abs(f.value.values - center), [float(h) for h in range(5, 65, 5)]),
              ("zscore", "-"): (np.abs(f.z_score.values), [round(x, 2) for x in np.arange(2.0, 7.01, 0.25)])}
    assert tr.ts.max() < pd.Timestamp(train_end)
    for name, cols in FEATURE_SETS.items():
        m = IsolationForest(n_estimators=200, random_state=C.SEED, contamination="auto").fit(tr[cols])
        s_all, s_tr = -m.score_samples(f[cols]), -m.score_samples(tr[cols])
        scores[("iforest", name)] = (s_all, [float(np.quantile(s_tr, q)) for q in QS])
    return scores, center


def run_grid(f, w, scores, per):
    """Evaluasi semua konfigurasi. Mengembalikan (DataFrame evaluasi per periode, DataFrame episode alarm)."""
    rows, alarm_rows = [], []
    for (method, fs), (sc, grid) in scores.items():
        for thr in grid:
            for k in C.K_LIST:
                starts = episode_starts(sc > thr, k)
                ep = pd.DataFrame({"seq": f.seq.values[starts], "ts": pd.to_datetime(f.ts.values[starts]), "score": sc[starts]})
                ep["window_id"] = np.nan
                for r in w.itertuples():
                    ep.loc[(ep.ts >= r.start_ts) & (ep.ts <= r.end_ts), "window_id"] = r.window_id
                for _, r in ep.iterrows():
                    alarm_rows.append((method, fs, thr, k, int(r.seq), r.ts, float(r.score), None if np.isnan(r.window_id) else int(r.window_id), not np.isnan(r.window_id)))
                for name, (a, b) in per.items():
                    sub = ep[(ep.ts >= a) & (ep.ts < b)]
                    e = evaluate(sub.ts.values, w, a, b)
                    e.pop("leads"); e.pop("event_ids")
                    rows.append(dict(method=method, feature_set=fs, threshold=thr, persistence=k, period=name, **e))
    ev = pd.DataFrame(rows)
    ev["recall_event"] = ev.events_detected / ev.events_total.replace(0, np.nan)
    ev["precision"] = ev.episodes_in_window / ev.episodes.replace(0, np.nan)
    al = pd.DataFrame(alarm_rows, columns=["method", "feature_set", "threshold", "persistence", "seq", "ts", "score", "window_id", "in_window"])
    return ev, al


def select_on_train(ev, fa_limit):
    """Per (method, feature_set): konfigurasi latih terbaik dengan alarm palsu <= fa_limit per minggu.
    Urutan: kejadian terdeteksi terbanyak, alarm palsu paling sedikit, lead time rata-rata terbesar."""
    t = ev[ev.period == "train"].copy()
    t = t[t.fa_per_week <= fa_limit]
    t["lead_key"] = t.lead_mean_h.fillna(-1e9)
    t = t.sort_values(["method", "feature_set", "events_detected", "fa_per_week", "lead_key", "persistence", "threshold"],
                      ascending=[True, True, False, True, False, True, False])
    return t.groupby(["method", "feature_set"], as_index=False).head(1).drop(columns="lead_key").reset_index(drop=True)
