"""Membuat sensor.duckdb: skema + muat data, uji constraint, dan pemeriksaan konsistensi."""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

C.chdir_root()
if C.DB_PATH.exists():
    C.DB_PATH.unlink()
con = duckdb.connect(str(C.DB_PATH))
con.execute((C.SQL_PREP / "01_schema.sql").read_text())
con.execute((C.SQL_PREP / "02_load.sql").read_text())
con.execute((C.SQL_ANALYSIS / "03_features.sql").read_text())

# 1. jumlah baris
rows = [(t, con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]) for t in ("sensor_readings", "anomaly_windows", "alarms")]
rows.append(("features (view)", con.execute("SELECT count(*) FROM features").fetchone()[0]))
pd.DataFrame(rows, columns=["tabel", "baris"]).to_csv(C.RES_PREP / "table_rows.csv", index=False)

# 2. uji constraint: data salah harus ditolak
tests = [
    ("seq ganda", "INSERT INTO sensor_readings VALUES (1, '2014-01-01', 80, 'ok')"),
    ("suhu di luar -50..200", "INSERT INTO sensor_readings VALUES (999999, '2014-01-01', 500, 'ok')"),
    ("gap_flag tidak dikenal", "INSERT INTO sensor_readings VALUES (999998, '2014-01-01', 80, 'xx')"),
    ("suhu kosong", "INSERT INTO sensor_readings VALUES (999997, '2014-01-01', NULL, 'ok')"),
    ("jendela berakhir sebelum mulai", "INSERT INTO anomaly_windows VALUES (99, '2014-01-02', '2014-01-01', 'x')"),
    ("metode alarm tidak dikenal", "INSERT INTO alarms VALUES (1, 'lstm', '-', 3, 3, 1000, '2013-12-05', 1, NULL, FALSE)"),
    ("alarm menunjuk seq yang tidak ada", "INSERT INTO alarms VALUES (1, 'zscore', '-', 3, 3, 888888, '2013-12-05', 1, NULL, FALSE)"),
    ("alarm menunjuk jendela yang tidak ada", "INSERT INTO alarms VALUES (1, 'zscore', '-', 3, 3, 1000, '2013-12-05', 1, 77, TRUE)"),
    ("in_window tidak cocok dengan window_id", "INSERT INTO alarms VALUES (1, 'zscore', '-', 3, 3, 1000, '2013-12-05', 1, 1, FALSE)"),
    ("persistence nol", "INSERT INTO alarms VALUES (1, 'zscore', '-', 3, 0, 1000, '2013-12-05', 1, NULL, FALSE)"),
]
res = []
for name, sql in tests:
    try:
        con.execute(sql)
        con.execute("ROLLBACK") if False else None
        out = "diterima"
    except Exception:
        out = "ditolak"
    res.append((name, out))
pd.DataFrame(res, columns=["test", "outcome"]).to_csv(C.RES_PREP / "constraint_tests.csv", index=False)
assert all(o == "ditolak" for _, o in res), res

# 3. konsistensi
chk = [
    ("seq berurutan 1..N tanpa lubang", "SELECT count(*) FROM (SELECT seq, row_number() OVER (ORDER BY seq) rn FROM sensor_readings) WHERE seq <> rn"),
    ("jumlah timestamp mundur = 1", "SELECT abs(count(*) - 1) FROM (SELECT ts, lag(ts) OVER (ORDER BY seq) p FROM sensor_readings) WHERE ts < p"),
    ("gap_flag ts_mundur tepat 1 baris", "SELECT abs(count(*) - 1) FROM sensor_readings WHERE gap_flag = 'ts_mundur'"),
    ("tidak ada celah > 5 menit", "SELECT count(*) FROM sensor_readings WHERE gap_flag = 'celah'"),
    ("jendela berlabel tidak tumpang tindih", "SELECT count(*) FROM anomaly_windows a JOIN anomaly_windows b ON a.window_id < b.window_id AND a.start_ts <= b.end_ts AND b.start_ts <= a.end_ts"),
    ("semua jendela berada di dalam rentang data", "SELECT count(*) FROM anomaly_windows a WHERE a.start_ts < (SELECT min(ts) FROM sensor_readings) OR a.end_ts > (SELECT max(ts) FROM sensor_readings)"),
    ("fitur: tepat 288 baris pertama kosong", "SELECT abs(count(*) - 288) FROM features WHERE z_score IS NULL"),
]
out = []
for name, sql in chk:
    v = con.execute(sql).fetchone()[0]
    out.append((name, int(v)))
pd.DataFrame(out, columns=["pemeriksaan", "violations"]).to_csv(C.RES_PREP / "consistency_checks.csv", index=False)
print(pd.DataFrame(rows).to_string()); print(pd.DataFrame(res).to_string()); print(pd.DataFrame(out).to_string())
assert all(v == 0 for _, v in out), out
con.close()
