"""Cek silang (Q12): fitur bergulir dari SQL (window function) vs hitungan pandas, dan profil jam SQL vs pandas."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from alarm_lib import connect  # noqa: E402

C.chdir_root()
con = connect()
sql = con.execute("SELECT * FROM features ORDER BY seq").df()
d = pd.read_csv(C.CLEAN_DIR / "sensor_readings.csv", parse_dates=["ts"]).sort_values("seq").reset_index(drop=True)
v = d.value
m = v.shift(1).rolling(C.WINDOW_POINTS).mean()
s = v.shift(1).rolling(C.WINDOW_POINTS).std()
x = np.arange(C.SLOPE_POINTS) - (C.SLOPE_POINTS - 1) / 2
slope = v.rolling(C.SLOPE_POINTS).apply(lambda a: (x * (a - a.mean())).sum() / (x * x).sum(), raw=True) * 12
pdf = pd.DataFrame({"roll_mean_24h": m, "roll_std_24h": s, "z_score": (v - m) / s, "dev_mean": v - m, "slope_6h": slope})
rows = []
for c in pdf.columns:
    a, b = sql[c].values, pdf[c].values
    both = ~np.isnan(a) & ~np.isnan(b)
    same_null = (np.isnan(a) == np.isnan(b)).all()
    diff = np.abs(a[both] - b[both])
    rows.append(dict(fitur=c, titik_dibandingkan=int(both.sum()), pola_kosong_sama="ya" if same_null else "tidak", selisih_maks=float(diff.max()),
                     status="PASS" if same_null and diff.max() < 1e-7 else "FAIL"))
# profil jam
ph = pd.read_csv(C.RES_PREP / "profile_hour.csv").set_index("hour")
sh = pd.read_csv(C.RES_ANALYSIS / "hour_profile_sql.csv").set_index("hour")
dm = float((ph["mean"] - sh["mean"]).abs().max())
rows.append(dict(fitur="profil jam: rata-rata", titik_dibandingkan=len(ph), pola_kosong_sama="ya", selisih_maks=dm, status="PASS" if dm < 1e-9 else "FAIL"))
ds = float((ph["std"] - sh["std"]).abs().max())
rows.append(dict(fitur="profil jam: simpangan baku", titik_dibandingkan=len(ph), pola_kosong_sama="ya", selisih_maks=ds, status="PASS" if ds < 1e-9 else "FAIL"))
out = pd.DataFrame(rows)
out.to_csv(C.RES_ANALYSIS / "crosscheck_features.csv", index=False)
print(out.to_string())
assert (out.status == "PASS").all()
