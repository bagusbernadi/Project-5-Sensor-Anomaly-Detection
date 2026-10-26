"""Menjalankan query SQL analisis: ringkasan fitur dan profil jam dari database."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from alarm_lib import connect  # noqa: E402

C.chdir_root()
con = connect()
con.execute("SELECT * FROM v_hour_profile").df().to_csv(C.RES_ANALYSIS / "hour_profile_sql.csv", index=False)
summ = con.execute("""
SELECT 'z_score' AS fitur, count(z_score) AS n, avg(z_score) AS mean, stddev_samp(z_score) AS std,
       quantile_cont(z_score, 0.001) AS p001, quantile_cont(z_score, 0.01) AS p01, quantile_cont(z_score, 0.99) AS p99,
       quantile_cont(z_score, 0.999) AS p999, min(z_score) AS min, max(z_score) AS max FROM features
UNION ALL SELECT 'roll_std_24h', count(roll_std_24h), avg(roll_std_24h), stddev_samp(roll_std_24h), quantile_cont(roll_std_24h, 0.001), quantile_cont(roll_std_24h, 0.01),
       quantile_cont(roll_std_24h, 0.99), quantile_cont(roll_std_24h, 0.999), min(roll_std_24h), max(roll_std_24h) FROM features
UNION ALL SELECT 'slope_6h', count(slope_6h), avg(slope_6h), stddev_samp(slope_6h), quantile_cont(slope_6h, 0.001), quantile_cont(slope_6h, 0.01),
       quantile_cont(slope_6h, 0.99), quantile_cont(slope_6h, 0.999), min(slope_6h), max(slope_6h) FROM features
""").df()
summ.round(8).to_csv(C.RES_ANALYSIS / "features_summary.csv", index=False)
print(summ.round(3).to_string())
