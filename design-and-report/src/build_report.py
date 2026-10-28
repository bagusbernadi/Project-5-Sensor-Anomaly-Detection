"""Membuat design-and-report/index.html (Report Project versi 2) dari page_v1.html dan CSV hasil.

- Pane Design diambil apa adanya dari page_v1.html (dicek identik).
- Semua angka di Report berasal dari project/results/*.csv lewat helper I/D/P/cs (report_lib.py) dan diaudit di akhir.
Jalankan dari folder mana saja:  python design-and-report/src/build_report.py
"""
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "project" / "code"))
sys.path.insert(0, str(HERE))
from common import (DB_PATH, FA_LIMIT, MIN_LEAD_H, RES_ANALYSIS, RES_PREP, RES_PRESENT, TRAIN_END, result)  # noqa: E402
from report_lib import (BLUE, D, GREY, HI, I, NO, OK, P, PART, SOFT, audit, bars, cs, esc, gbars, legend, lines,  # noqa: E402
                        pill, qa, table)

R = lambda n: pd.read_csv(result(n))
PRIO = {1: "Utama", 2: "Pendukung", 3: "Utama", 4: "Utama", 5: "Utama", 6: "Pendukung", 7: "Utama", 8: "Pendukung",
        9: "Utama", 10: "Tambahan", 11: "Utama", 12: "Utama"}
QT = {1: "Bagaimana pola suhu harian dan mingguan, dan berapa rentang suhu normal?",
      2: "Berapa banyak data hilang atau lompatan waktu di antara titik data?",
      3: "Seberapa awal aturan rolling z-score mendeteksi keempat jendela anomali berlabel?",
      4: "Berapa alarm palsu per minggu untuk setiap ambang?",
      5: "Apakah Isolation Forest lebih baik daripada rolling z-score dan ambang tetap?",
      6: "Fitur mana (rata-rata bergulir, simpangan, kemiringan) yang paling membantu?",
      7: "Ambang mana yang menangkap kejadian sebelum kegagalan dengan alarm palsu di bawah batas yang diterima tim?",
      8: "Berapa titik berturut-turut skor harus tinggi sebelum alarm dikirim?",
      9: "Berapa jam peringatan dini rata-rata sebelum kegagalan?",
      10: "Berapa jam downtime yang bisa dicegah per tahun?",
      11: "Apakah evaluasi tidak bocor ke masa depan, misalnya ambang dipilih dari data yang belum terjadi?",
      12: "Apakah statistik bergulir dari SQL sama dengan hasil pandas?"}
WARN = set()


def Q(n, ans, warn=False):
    if warn:
        WARN.add(n)
    return qa(f"Q{n}", QT[n], PRIO[n], ans, "Terjawab dengan catatan" if warn else "Terjawab", warn)


mk = lambda *a: "".join(a)
MONTH = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
TGL = lambda s: cs(f"{int(str(s)[8:10])} {MONTH[int(str(s)[5:7]) - 1]} {str(s)[:4]}")
TS = lambda s: cs(str(s)[:16])
METH = {"fixed": "Ambang tetap", "zscore": "Rolling z-score", "iforest": "Isolation Forest"}

# ---------------------------------------------------------------- data
dqt = R("data_quality.csv").set_index("ukuran").nilai
ps = R("profile_summary.csv").set_index("ukuran").nilai.astype(float)
hr, dw, rows_t = R("profile_hour.csv"), R("profile_dow.csv"), R("table_rows.csv")
ctest, cons, dlog = R("constraint_tests.csv"), R("consistency_checks.csv"), R("download_log.csv")
fsum = R("features_summary.csv").set_index("fitur")
xf, xa, leak = R("crosscheck_features.csv"), R("crosscheck_alarms.csv"), R("leakage_check.csv")
ev, sel, best = R("method_evaluation.csv"), R("selection.csv"), R("selection_best_per_method.csv").set_index("method")
lim, per, ze = R("selection_limits.csv"), R("persistence.csv"), R("zscore_events.csv")
ed, lt, mg, imp, fr = R("event_detail.csv"), R("lead_time.csv").set_index("method"), R("margin_sensitivity.csv"), R("impact.csv"), R("final_rule.csv").iloc[0]
ifs = R("iforest_features.csv")
con = duckdb.connect(str(DB_PATH), read_only=True)
dbc = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("sensor_readings", "anomaly_windows", "alarms", "features")}
win = con.execute("SELECT window_id, start_ts, end_ts FROM anomaly_windows ORDER BY window_id").df()
mundur = con.execute("SELECT min(seq) FROM sensor_readings WHERE gap_flag='ts_mundur'").fetchone()[0]
sample = con.execute(f"SELECT seq, ts, value, gap_flag FROM sensor_readings WHERE seq BETWEEN {mundur - 2} AND {mundur + 2} ORDER BY seq").fetchall()
gapc = dict(con.execute("SELECT gap_flag, count(*) FROM sensor_readings GROUP BY 1").fetchall())
con.close()

fx, zs, itf = best.loc["fixed"], best.loc["zscore"], best.loc["iforest"]
ifv = sel[sel.method == "iforest"].set_index("feature_set")
ae = ev[(ev.period == "all") & (ev.persistence == 3)]
afx, azs = ae[ae.method == "fixed"].sort_values("threshold"), ae[ae.method == "zscore"].sort_values("threshold")
lead = ed.pivot(index="window_id", columns="method", values="lead_h")
ok_fa = lambda d: d[d.fa_per_week <= FA_LIMIT].iloc[0]          # ambang terlonggar yang memenuhi batas alarm palsu (semua data)
zlim, flim = ok_fa(azs), ok_fa(afx)
ip = imp.set_index(["downtime_per_kegagalan_h", "skenario"])
i4, i8, i12 = (ip.loc[(h, "titik")] for h in (4, 8, 12))
ilo, ihi = ip.loc[(4, "batas bawah (Wilson 95%)")], ip.loc[(4, "batas atas (Wilson 95%)")]
ilo12, ihi12 = ip.loc[(12, "batas bawah (Wilson 95%)")], ip.loc[(12, "batas atas (Wilson 95%)")]
mf, mi, mz = (mg[mg.method == m].set_index("margin_h") for m in ("fixed", "iforest", "zscore"))
n_win, n_in = int(dqt["jendela anomali berlabel"]), int(dqt["titik di dalam jendela berlabel"])
npr = {k: sum(1 for v in PRIO.values() if v == k) for k in ("Utama", "Pendukung", "Tambahan")}
nfeat = int(fsum.loc["z_score", "n"])

assert (n_win, int(dqt["titik data (baris)"]), int(dqt["celah waktu (> 5 menit)"])) == (4, 22695, 0)
assert (xf.status == "PASS").all() and (xa.status == "PASS").all() and (leak.status == "PASS").all()
assert (ctest.outcome == "ditolak").all() and (cons.violations == 0).all()
assert fx.events_detected_all == 4 and fx.events_early_all == 3 and fx.fa_per_week_all < FA_LIMIT
assert fx.fa_per_week_all < itf.fa_per_week_all < zs.fa_per_week_all and fx.fa_per_week_test < FA_LIMIT
assert ifv.loc["value"].events_detected_all == 4 and ifv.loc["value"].events_early_all == 4
assert (fx.threshold, fx.persistence) == (fr.threshold, fr.persistence)
assert zs.events_detected_all == 3 and zs.fa_per_week_all > FA_LIMIT and ps["varians dijelaskan jam dalam sehari (eta^2)"] < 0.05

# ---------------------------------------------------------------- 1. data
kp = lambda c, v, l, d: f'<div class="card kpi" style="--h:var(--{c}H)"><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></div>'
rp1 = mk(
    '<div class="kpis">',
    kp("navy", I(dbc["sensor_readings"]), "titik data suhu", f"Satu sensor, satu titik per 5 menit, {TS(dqt['timestamp pertama'])[:10]} sampai {TS(dqt['timestamp terakhir'])[:10]} ({I(float(dqt['rentang (hari)']))} hari)."),
    kp("amber", I(n_win), "jendela anomali berlabel", f"Label NAB v1.1; {I(n_in)} titik ({P(n_in / dbc['sensor_readings'], 1)}) berada di dalam jendela. Dua kejadian di periode latih, dua di periode uji."),
    kp("teal", I(nfeat), "titik dengan fitur lengkap", f"Setelah masa pemanasan 288 titik (24 jam); dihitung dengan window function SQL di view <code>features</code>."),
    kp("plum", I(float(dqt["timestamp mundur"]) + float(dqt["timestamp ganda (kemunculan kedua)"])), "titik bertanda waktu janggal", f"{I(dqt['timestamp mundur'])} timestamp mundur ({I(dqt['mundur sebesar (menit)'])} menit) dan {I(dqt['timestamp ganda (kemunculan kedua)'])} timestamp ganda; celah waktu: {I(dqt['celah waktu (> 5 menit)'])}."),
    kp("rose", I(dbc["alarms"]), "episode alarm dievaluasi", "Semua kombinasi metode, ambang, dan persistence; satu baris = satu episode alarm."),
    kp("sky", I(len(ev)), "konfigurasi dievaluasi", f"{I(len(ev) // 3)} konfigurasi, masing-masing dinilai pada data latih, uji, dan seluruh data."),
    '</div><h3>1.1 Data NAB (mentah dan bersih)</h3>')
rp1 += '<div class="card"><h4>Cuplikan sensor_readings di sekitar timestamp yang mundur</h4>' + table(
    ["seq", "ts", "value", "gap_flag"], [[I(r[0]), TS(r[1]), D(r[2], 2), f"<code>{r[3]}</code>"] for r in sample]) + \
    '<p>Urutan baris (<code>seq</code>) dipakai sebagai kunci, bukan timestamp, karena timestamp mundur satu kali. Baris yang ditandai tetap dipakai.</p></div>'
rp1 += '<div class="card"><h4>Tabel 1.1. Kualitas data</h4>' + table(
    ["Pemeriksaan", "Hasil", "Keputusan"],
    [["Titik data", I(dqt["titik data (baris)"]), "Dipakai semua"],
     ["Interval 5 menit normal", I(dqt["interval 5 menit normal"]), "Dipakai"],
     ["Celah waktu (lebih dari 5 menit)", I(dqt["celah waktu (> 5 menit)"]), "Tidak ada; hipotesis 5 tidak terbukti"],
     ["Timestamp mundur", f"{I(dqt['timestamp mundur'])} kali, {I(dqt['mundur sebesar (menit)'])} menit ({TS(dqt['tanggal timestamp mundur'])})", "Ditandai <code>ts_mundur</code>; jendela bergulir mengikuti <code>seq</code>"],
     ["Timestamp ganda", I(dqt["timestamp ganda (kemunculan kedua)"]), "Ditandai <code>ts_ganda</code>"],
     ["Nilai kosong", I(dqt["nilai kosong"]), "Tidak perlu penanganan"],
     ["Suhu minimum dan maksimum", f"{D(dqt['suhu minimum'], 2)} dan {D(dqt['suhu maksimum'], 2)}", "Dipakai"],
     ["Titik dengan suhu di bawah 30", I(dqt["titik dengan suhu di bawah 30"]), "Dipakai (bagian dari kegagalan, bukan kesalahan data)"]]) + \
    f'<p>Sumber: {I(len(dlog))} file dari NAB {dlog.version[0]}, tanggal akses {cs(dlog.access_date[0])} (<code>download_log.csv</code>). Data mentah dan bersih tidak di-commit; diunduh ulang oleh skrip.</p></div>'
rp1 += '<h3>1.2 Tabel di database (<code>sensor.duckdb</code>)</h3><div class="card"><h4>Tabel 1.2a. Isi database</h4>' + table(
    ["Tabel", "Baris", "Isi"],
    [["sensor_readings", I(dbc["sensor_readings"]), "Satu bacaan suhu. Kunci utama <code>seq</code>; <code>gap_flag</code> menandai waktu janggal."],
     ["anomaly_windows", I(dbc["anomaly_windows"]), "Satu jendela anomali berlabel (tabel referensi)."],
     ["alarms", I(dbc["alarms"]), "Satu episode alarm dari satu metode, ambang, dan persistence. Kunci asing ke jendela."],
     ["features (view)", I(dbc["features"]), "Fitur bergulir dari window function: rata-rata, simpangan, z-score, selisih, kemiringan."]]) + \
    '<h4>Tabel 1.2b. Uji aturan pengecekan (constraint)</h4>' + table(
    ["Baris salah yang dicoba dimasukkan", "Hasil"], [[r.test, OK("Ditolak") if r.outcome == "ditolak" else NO("Diterima")] for r in ctest.itertuples()]) + \
    f'<p>Kesepuluh jenis data salah ditolak oleh database. {I(len(cons))} pemeriksaan konsistensi menghasilkan 0 pelanggaran.</p></div>'
FILES = {"consistency_checks": ("Pemeriksaan konsistensi database", "Q2"), "constraint_tests": ("Uji constraint database", "Q2"), "daily_stats": ("Statistik suhu per hari", "Q1"),
         "data_quality": ("Ringkasan kualitas data", "Q2"), "download_log": ("Log unduhan sumber (URL, ukuran, versi)", "dokumentasi"), "profile_dow": ("Suhu per hari dalam minggu", "Q1"),
         "profile_hour": ("Suhu per jam dalam sehari", "Q1"), "profile_summary": ("Ringkasan profil suhu", "Q1"), "table_rows": ("Baris per tabel", "Q2"),
         "crosscheck_alarms": ("Episode alarm: SQL vs pandas", "Q12"), "crosscheck_features": ("Fitur bergulir: SQL vs pandas", "Q12"), "event_detail": ("Alarm pertama dan lead time per kejadian", "Q3, Q9"),
         "features_summary": ("Ringkasan distribusi fitur", "Q6"), "final_rule": ("Aturan alarm terpilih", "Q7"), "hour_profile_sql": ("Profil jam dari query SQL", "Q1, Q12"),
         "iforest_features": ("Kombinasi fitur Isolation Forest", "Q6"), "impact": ("Estimasi downtime yang bisa dicegah", "Q10"), "lead_time": ("Ringkasan lead time per metode", "Q9"),
         "leakage_check": ("Uji kebocoran data masa depan", "Q11"), "margin_sensitivity": ("Sensitivitas margin sebelum jendela", "Q3, Q9"), "method_evaluation": ("Evaluasi semua metode, ambang, persistence", "Q3, Q4, Q5"),
         "persistence": ("Syarat titik berturut-turut", "Q8"), "selection": ("Konfigurasi terpilih per metode dan fitur", "Q5, Q6"), "selection_best_per_method": ("Konfigurasi terbaik per metode", "Q5"),
         "selection_limits": ("Pemilihan pada batas alarm palsu 1, 2, 5 per minggu", "Q7"), "zscore_events": ("Lead time z-score per ambang dan kejadian", "Q3")}
resfiles = sorted(p for d in (RES_PREP, RES_ANALYSIS) for p in d.glob("*.csv"))
miss = [p.stem for p in resfiles if p.stem not in FILES]
assert not miss, f"CSV hasil belum didokumentasikan di FILES: {miss}"
rp1 += '<div class="card"><h4>Tabel 1.2c. Data hasil analisis (<code>project/results/</code>)</h4>' + table(
    ["File", "Isi", "Baris", "Menjawab"], [[f"<code>{p.stem}.csv</code>", FILES[p.stem][0], I(len(pd.read_csv(p))), FILES[p.stem][1]] for p in resfiles]) + \
    f'<p>{I(len(resfiles))} file CSV, ditambah {I(len(list(RES_PRESENT.glob("dash_*.csv"))))} CSV data dashboard.</p></div>'
rp1 += '<h3>1.3 Angka kunci (KPI)</h3><div class="card"><h4>Tabel 1.3. Lima KPI (definisi di <code>project/docs/definitions.md</code>)</h4>' + table(
    ["KPI", "Rumus ringkas", "Hasil (aturan terpilih)", "Jumlah data"],
    [["Kejadian terdeteksi", "kejadian dengan episode alarm di dalam jendela ÷ kejadian", f"{I(fr.events_detected_all)} dari {I(fr.events_total_all)}", f"latih {I(fr.events_detected_train)} dari {I(fr.events_total_train)}, uji {I(fr.events_detected_test)} dari {I(fr.events_total_test)}"],
     ["Alarm palsu per minggu", "episode di luar jendela ÷ lama periode (minggu)", f"{D(fr.fa_per_week_all, 2)} (uji {D(fr.fa_per_week_test, 2)})", f"{I(fr.false_alarms_all)} dari {I(fr.episodes_all)} episode"],
     ["Precision (tingkat episode)", "episode di dalam jendela ÷ semua episode", f"{P(fr.precision_all, 0)} (uji {P(fr.precision_test, 0)})", f"{I(fr.episodes_all)} episode"],
     ["Lead time rata-rata", "titik tengah jendela − alarm pertama (jam)", f"{D(fr.lead_mean_h_all, 1)} jam", f"{I(fr.events_early_all)} dari {I(fr.events_total_all)} kejadian lebih awal"],
     ["Downtime dicegah (estimated)", "kegagalan per tahun × share berperingatan ≥ 2 jam × jam downtime", f"{D(i4.jam_downtime_dicegah_per_tahun, 0)} sampai {D(i12.jam_downtime_dicegah_per_tahun, 0)} jam per tahun", "asumsi downtime 4 sampai 12 jam"]]) + \
    f'<p>Aturan terpilih: ambang tetap ±{D(fr.threshold, 0)} derajat dari median data latih, {I(fr.persistence)} titik berturut-turut. Dipilih dari data sebelum {cs(TRAIN_END)} saja.</p></div>'

# ---------------------------------------------------------------- 2. business questions
sec21 = mk(
    '<h3 id="sec21">2.1 Pola suhu dan kualitas waktu <span class="qlist">Q1, Q2</span></h3><div class="card">',
    Q(1, f"Pola harian lemah. Rata-rata per jam hanya berselisih {D(ps['selisih rata-rata jam tertinggi dan terendah'], 1)} derajat antara jam tertinggi dan terendah, dan jam dalam sehari hanya menjelaskan {P(ps['varians dijelaskan jam dalam sehari (eta^2)'], 1)} variasi suhu (hari dalam minggu: {P(ps['varians dijelaskan hari dalam minggu (eta^2)'], 1)}). "
         f"Rentang suhu normal (di luar jendela anomali): rata-rata {D(ps['suhu rata-rata (di luar jendela)'], 1)}, persentil 5 sampai 95 antara {D(ps['persentil 5'], 1)} dan {D(ps['persentil 95'], 1)}; rata-rata di dalam jendela berlabel hanya {D(ps['rata-rata dalam jendela berlabel'], 1)}. "
         "Jadi hipotesis 4 (suhu punya pola harian yang kuat) tidak didukung data."),
    Q(2, f"Tidak ada celah waktu: {I(dqt['interval 5 menit normal'])} dari {I(dbc['sensor_readings'] - 1)} selisih antar titik tepat 5 menit. Yang ada: {I(dqt['timestamp mundur'])} timestamp mundur {I(dqt['mundur sebesar (menit)'])} menit ({TS(dqt['tanggal timestamp mundur'])}) yang membuat {I(dqt['timestamp ganda (kemunculan kedua)'])} timestamp muncul dua kali. "
         "Hipotesis 5 (ada celah waktu) tidak terbukti; bentuk masalahnya berbeda dan sudah ditandai di <code>gap_flag</code>."),
    '<h4>Grafik 2.1a. Rata-rata suhu per jam dalam sehari</h4>',
    lines([f"{int(h):02d}" for h in hr.hour], [("Rata-rata per jam", BLUE, 2.5, list(hr["mean"]))], lambda v: D(v, 0), "Rata-rata suhu per jam", zero=False),
    '<h4>Grafik 2.1b. Rata-rata suhu per hari dalam minggu</h4>',
    bars([(r.hari[:3], r.mean, BLUE, f"{r.hari}: rata-rata {D(r.mean, 1)}, simpangan baku {D(r.std, 1)}, {I(r.n)} titik") for r in dw.itertuples()], lambda v: D(v, 0), "Rata-rata suhu per hari", rot=0, small=True),
    '<h4>Tabel 2.1c. Ringkasan profil suhu (di luar jendela anomali)</h4>',
    table(["Ukuran", "Nilai"], [[k, D(v, 3 if "eta" in k else 1)] for k, v in ps.items()]), '</div>')
zp = ze.pivot(index="threshold", columns="window_id", values="lead_h")
sec22 = mk(
    '<h3 id="sec22">2.2 Rolling z-score dan keempat jendela <span class="qlist">Q3</span></h3><div class="card">',
    Q(3, f"Pada ambang terpilih (|z| > {D(zs.threshold, 2)}, {I(zs.persistence)} titik berturut-turut) rolling z-score mendeteksi {I(zs.events_detected_all)} dari 4 kejadian dan hanya {I(zs.events_early_all)} yang lebih awal; kejadian 3 terlewat. "
         f"Pada ambang longgar (|z| > {D(2.0, 0)}) keempatnya terdeteksi, tetapi kejadian 4 baru berbunyi setelah titik tengah jendela (lead time {D(zp.loc[2.0, 4], 1)} jam) dan alarm palsu {D(azs.iloc[0].fa_per_week, 2)} per minggu. "
         "Lead time memakai titik tengah jendela sebagai perkiraan waktu kegagalan; nilai negatif berarti alarm datang setelahnya.", warn=True),
    '<h4>Tabel 2.2a. Lead time z-score (jam) per ambang dan kejadian, persistence 3</h4>',
    table(["Ambang |z|", "Kejadian 1", "Kejadian 2", "Kejadian 3", "Kejadian 4"],
          [[D(t, 1)] + [D(zp.loc[t, w], 1) if pd.notna(zp.loc[t, w]) else NO("tidak terdeteksi") for w in (1, 2, 3, 4)] for t in zp.index]),
    '<p>Hanya ambang 2, 3, 4, dan 5 yang ditampilkan di sini. Hasil semua ambang ada di <code>method_evaluation.csv</code>. Kejadian dianggap terdeteksi jika episode alarm pertama mulai di dalam jendela berlabel.</p></div>')
sec23 = mk(
    '<h3 id="sec23">2.3 Alarm palsu per ambang <span class="qlist">Q4</span></h3><div class="card">',
    Q(4, f"Alarm palsu turun mengikuti ambang. Rolling z-score: dari {D(azs.iloc[0].fa_per_week, 2)} per minggu (|z| > {D(azs.iloc[0].threshold, 1)}) menjadi 0 pada |z| > {D(azs[azs.fa_per_week == 0].iloc[0].threshold, 2)}. "
         f"Ambang tetap: dari {D(afx.iloc[0].fa_per_week, 2)} per minggu (±{D(afx.iloc[0].threshold, 0)} derajat) menjadi 0 pada ±{D(afx[afx.fa_per_week == 0].iloc[0].threshold, 0)} derajat. "
         f"Dengan batas {D(FA_LIMIT, 0)} per minggu, ambang paling longgar yang memenuhi adalah |z| > {D(zlim.threshold, 2)} (hanya {I(zlim.events_detected)} dari 4 kejadian) dan ±{D(flim.threshold, 0)} derajat ({I(flim.events_detected)} dari 4)."),
    '<h4>Grafik 2.3a. Alarm palsu per minggu menurut ambang rolling z-score (semua data, persistence 3)</h4>',
    lines([D(t, 2) for t in azs.threshold], [("Alarm palsu per minggu", BLUE, 2.5, list(azs.fa_per_week))], lambda v: D(v, 1), "Alarm palsu z-score", zero=True),
    '<h4>Grafik 2.3b. Alarm palsu per minggu menurut ambang tetap (derajat dari median, persistence 3)</h4>',
    lines([D(t, 0) for t in afx.threshold], [("Alarm palsu per minggu", HI, 2.5, list(afx.fa_per_week))], lambda v: D(v, 1), "Alarm palsu ambang tetap", zero=True),
    '<h4>Tabel 2.3c. Ambang tetap: kejadian terdeteksi dan alarm palsu (semua data, persistence 3)</h4>',
    table(["Ambang (± derajat)", "Kejadian terdeteksi", "Alarm palsu", "Per minggu", "Lead time rata-rata (jam)"],
          [[D(r.threshold, 0), f"{I(r.events_detected)} dari 4", I(r.false_alarms), D(r.fa_per_week, 2), D(r.lead_mean_h, 1)] for r in afx.itertuples()]),
    '<p>Alarm di luar jendela belum tentu salah: NAB hanya melabeli empat kejadian, sehingga sebagian "alarm palsu" bisa gangguan nyata yang tidak dilabeli.</p></div>')
cats = [METH["fixed"], METH["zscore"], METH["iforest"] + " (value+z+std)"]
bb = [fx, zs, itf]
sec24 = mk(
    '<h3 id="sec24">2.4 Perbandingan metode dan fitur <span class="qlist">Q5, Q6</span></h3><div class="card">',
    Q(5, f"Tidak pada data ini. Dengan aturan pemilihan dari data latih, ambang tetap terbaik: {I(fx.events_detected_all)} dari 4 kejadian, {D(fx.fa_per_week_all, 2)} alarm palsu per minggu, lead time rata-rata {D(fx.lead_mean_h_all, 1)} jam. "
         f"Isolation Forest (value+z+std) {I(itf.events_detected_all)} dari 4 dengan {D(itf.fa_per_week_all, 2)} per minggu dan lead {D(itf.lead_mean_h_all, 1)} jam; rolling z-score {I(zs.events_detected_all)} dari 4 dengan {D(zs.fa_per_week_all, 2)} per minggu. "
         f"Namun Isolation Forest dengan fitur suhu saja memberi {I(ifv.loc['value'].events_early_all)} dari 4 kejadian lebih awal pada {D(ifv.loc['value'].fa_per_week_all, 2)} per minggu, hampir menyamai ambang tetap; dengan hanya 4 kejadian selisih ini belum cukup sebagai bukti.", warn=True),
    Q(6, f"Tidak ada fitur tambahan yang konsisten membantu. Suhu saja (value) mendeteksi {I(ifv.loc['value'].events_detected_all)} dari 4 dengan {D(ifv.loc['value'].fa_per_week_all, 2)} per minggu; menambah z_score, simpangan, atau kemiringan menurunkan kejadian terdeteksi atau menambah alarm palsu. "
         f"Kombinasi value+z+std yang dipilih aturan data latih mendeteksi {I(ifv.loc['value+z+std'].events_detected_all)} dari 4 tetapi hanya {I(ifv.loc['value+z+std'].events_early_all)} lebih awal dengan {D(ifv.loc['value+z+std'].fa_per_week_all, 2)} per minggu."),
    '<h4>Grafik 2.4a. Alarm palsu per minggu: data latih vs data uji (konfigurasi terpilih dari data latih)</h4>',
    gbars(cats, [("Latih", GREY, [b.fa_per_week_train for b in bb]), ("Uji", BLUE, [b.fa_per_week_test for b in bb])], lambda v: D(v, 1), "Alarm palsu per minggu per metode", rot=0),
    legend([(GREY, "Data latih"), (BLUE, "Data uji")]),
    '<h4>Tabel 2.4b. Konfigurasi terpilih per metode</h4>',
    table(["Metode", "Ambang", "Persistence", "Terdeteksi (latih / uji / semua)", "Dini (semua)", "Alarm palsu per minggu (latih / uji)", "Precision uji", "Lead rata-rata (jam)"],
          [[METH[m], D(b.threshold, 2), I(b.persistence), f"{I(b.events_detected_train)} / {I(b.events_detected_test)} / {I(b.events_detected_all)}", I(b.events_early_all),
            f"{D(b.fa_per_week_train, 2)} / {D(b.fa_per_week_test, 2)}", D(b.precision_test, 2), D(b.lead_mean_h_all, 1)] for m, b in zip(("fixed", "zscore", "iforest"), bb)]),
    '<h4>Tabel 2.4c. Isolation Forest menurut kombinasi fitur</h4>',
    table(["Fitur", "Kolom", "Ambang", "Persistence", "Terdeteksi (uji / semua)", "Dini (semua)", "Alarm palsu per minggu (uji)", "Lead rata-rata (jam)"],
          [[f"<code>{r.Index}</code>", ifs.set_index("feature_set").loc[r.Index].kolom, D(r.threshold, 2), I(r.persistence), f"{I(r.events_detected_test)} / {I(r.events_detected_all)}",
            I(r.events_early_all), D(r.fa_per_week_test, 2), D(r.lead_mean_h_all, 1)] for r in ifv.itertuples()]),
    '<p>Model dilatih hanya pada data sebelum 1 Januari 2014 (200 pohon, seed tetap); ambang adalah persentil skor data latih. Hanya 2 kejadian di data uji, jadi satu kejadian mengubah recall 50 poin.</p></div>')
sec25 = mk(
    '<h3 id="sec25">2.5 Memilih ambang dan persistence <span class="qlist">Q7, Q8</span></h3><div class="card">',
    Q(7, f"Ambang tetap ±{D(fr.threshold, 0)} derajat dari median data latih dengan {I(fr.persistence)} titik berturut-turut. Pada data latih: {I(fr.events_detected_train)} dari {I(fr.events_total_train)} kejadian, {D(fr.fa_per_week_train, 2)} alarm palsu per minggu; "
         f"pada data uji: {I(fr.events_detected_test)} dari {I(fr.events_total_test)} kejadian, {D(fr.fa_per_week_test, 2)} per minggu, precision {D(fr.precision_test, 2)}. Hasil sama pada batas 1, 2, dan 5 alarm palsu per minggu. "
         f"Batas {D(FA_LIMIT, 0)} per minggu adalah asumsi dan belum disepakati dengan tim maintenance.", warn=True),
    Q(8, f"Untuk ambang tetap, persistence hampir tidak mengubah hasil: 1, 3, atau 6 titik tetap mendeteksi 4 dari 4; alarm palsu semua data {D(per[(per.method == 'fixed') & (per.persistence == 1) & (per.period == 'all')].fa_per_week.iloc[0], 2)}, "
         f"{D(per[(per.method == 'fixed') & (per.persistence == 3) & (per.period == 'all')].fa_per_week.iloc[0], 2)}, dan {D(per[(per.method == 'fixed') & (per.persistence == 6) & (per.period == 'all')].fa_per_week.iloc[0], 2)} per minggu. "
         "Persistence 6 dipilih karena alarm palsu data latih 0. Untuk rolling z-score persistence 6 justru menghilangkan kejadian, dan Isolation Forest paling baik pada persistence 3."),
    '<h4>Tabel 2.5a. Konfigurasi terpilih pada tiga batas alarm palsu per minggu</h4>',
    table(["Batas (per minggu)", "Metode", "Ambang", "Persistence", "Terdeteksi latih / uji / semua", "Alarm palsu per minggu (uji)", "Lead rata-rata (jam)"],
          [[D(r.batas_fa_per_minggu, 0), METH[r.method], D(r.threshold, 2), I(r.persistence), f"{I(r.events_detected_train)} / {I(r.events_detected_test)} / {I(r.events_detected_all)}",
            D(r.fa_per_week_test, 2), D(r.lead_mean_h_all, 1)] for r in lim.itertuples()]),
    '<h4>Tabel 2.5b. Pengaruh persistence pada konfigurasi terpilih (semua data)</h4>',
    table(["Metode", "Persistence", "Terdeteksi", "Alarm palsu", "Per minggu", "Lead rata-rata (jam)"],
          [[METH[r.method], I(r.persistence), f"{I(r.events_detected)} dari {I(r.events_total)}", I(r.false_alarms), D(r.fa_per_week, 2), D(r.lead_mean_h, 1)] for r in per[per.period == "all"].itertuples()]), '</div>')
fxl = lead["fixed"]
leadbar = [(f"Kejadian {w}", max(float(v), 0), BLUE, f"Kejadian {w}: lead time {D(v, 1)} jam") for w, v in fxl.items()]
sec26 = mk(
    '<h3 id="sec26">2.6 Lead time dan dampak <span class="qlist">Q9, Q10</span></h3><div class="card">',
    Q(9, f"Aturan terpilih memberi peringatan rata-rata {D(lt.loc['fixed'].lead_mean_h, 1)} jam sebelum perkiraan waktu kegagalan (median {D(lt.loc['fixed'].lead_median_h, 1)}, maksimum {D(lt.loc['fixed'].lead_max_h, 1)}); minimum {D(lt.loc['fixed'].lead_min_h, 2)} jam, yaitu kejadian 3 yang baru berbunyi tepat saat titik tengah jendela. "
         f"{I(lt.loc['fixed'].events_with_lead_ge_min)} dari 4 kejadian mendapat peringatan minimal {D(MIN_LEAD_H, 0)} jam. Waktu kegagalan dihampiri titik tengah jendela, jadi angka ini perkiraan. "
         f"Jika alarm yang berbunyi sampai {I(12)} jam sebelum awal jendela dihitung, ambang tetap tidak berubah, sedangkan rolling z-score naik menjadi {I(mz.loc[12].events_detected)} dari 4 kejadian dengan lead rata-rata {D(mz.loc[12].lead_mean_h, 1)} jam (Tabel 2.6c).", warn=True),
    Q(10, f"Sekitar {D(i4.kegagalan_per_tahun, 1)} kegagalan per tahun jika 4 kejadian dalam {I(float(dqt['rentang (hari)']))} hari diekstrapolasi, dengan {P(i4.share_dengan_peringatan, 0)} kejadian berperingatan cukup. Downtime yang bisa dicegah sekitar {D(i4.jam_downtime_dicegah_per_tahun, 0)} jam per tahun (asumsi 4 jam per kegagalan), "
          f"{D(i8.jam_downtime_dicegah_per_tahun, 0)} jam (8 jam), atau {D(i12.jam_downtime_dicegah_per_tahun, 0)} jam (12 jam). Rentang dengan interval Wilson 95%: {D(ilo.jam_downtime_dicegah_per_tahun, 0)} sampai {D(ihi12.jam_downtime_dicegah_per_tahun, 0)} jam. Semua angka estimated.", warn=True),
    '<h4>Grafik 2.6a. Lead time ambang tetap per kejadian (jam; nilai negatif digambar nol, nilai asli di tooltip dan Tabel 2.6b)</h4>',
    bars(leadbar, lambda v: D(v, 1), "Lead time per kejadian", rot=0, small=True),
    '<h4>Tabel 2.6b. Lead time per kejadian dan metode (jam; negatif = setelah titik tengah jendela)</h4>',
    table(["Kejadian", "Awal jendela", "Titik tengah (perkiraan kegagalan)"] + [METH[m] for m in ("fixed", "zscore", "iforest")],
          [[I(w), TS(win.start_ts[w - 1]), TS(ed[(ed.method == "fixed") & (ed.window_id == w)].window_mid.iloc[0])] +
           [D(lead.loc[w, m], 1) if pd.notna(lead.loc[w, m]) else NO("tidak terdeteksi") for m in ("fixed", "zscore", "iforest")] for w in lead.index]),
    '<h4>Tabel 2.6c. Sensitivitas: alarm sampai N jam sebelum awal jendela ikut dihitung dini</h4>',
    table(["Metode", "Margin (jam)", "Terdeteksi", "Dini", "Alarm palsu", "Per minggu", "Lead rata-rata (jam)"],
          [[METH[r.method], I(r.margin_h), f"{I(r.events_detected)} dari 4", I(r.events_early), I(r.false_alarms), D(r.fa_per_week, 2), D(r.lead_mean_h, 1)] for r in mg.itertuples()]),
    '<h4>Tabel 2.6d. Downtime yang bisa dicegah per tahun (estimated)</h4>',
    table(["Downtime per kegagalan (jam, asumsi)", "Skenario", "Share berperingatan", "Kegagalan per tahun", "Jam dicegah per tahun"],
          [[I(r.downtime_per_kegagalan_h), r.skenario, P(r.share_dengan_peringatan, 0), D(r.kegagalan_per_tahun, 1), D(r.jam_downtime_dicegah_per_tahun, 1)] for r in imp.itertuples()]),
    f'<p>Peringatan dianggap berguna jika minimal {D(MIN_LEAD_H, 0)} jam (asumsi). Kegagalan per tahun diekstrapolasi dari hanya 4 kejadian, jadi rentang sangat lebar.</p></div>')
sec27 = mk(
    '<h3 id="sec27">2.7 Validasi evaluasi <span class="qlist">Q11, Q12</span></h3><div class="card">',
    Q(11, f"Ya. Data latih berhenti pada {TS(leak.ts_terakhir_data_latih.iloc[0])} dan ketujuh konfigurasi (satu per metode dan kombinasi fitur) diulang hanya dengan data sebelum {cs(TRAIN_END)}: ambang dan persistence terpilih sama persis. "
          f"Model Isolation Forest dan pusat ambang tetap juga hanya memakai data latih, dan jendela bergulir hanya melihat {I(288)} titik sebelumnya (titik sekarang tidak ikut). Semua {I(len(leak))} pemeriksaan PASS."),
    Q(12, f"Ya. {I(len(xf))} pemeriksaan fitur bergulir (rata-rata, simpangan, z-score, selisih, kemiringan, dan profil jam) antara SQL dan pandas semuanya PASS dengan selisih terbesar di bawah 1E-10, dan {I(len(xa))} pemeriksaan jumlah episode alarm SQL vs Python semuanya PASS."),
    '<h4>Tabel 2.7a. Uji kebocoran data masa depan</h4>',
    table(["Metode", "Fitur", "Ambang (data lengkap)", "Ambang (hanya data latih)", "Persistence (lengkap / latih)", "Status"],
          [[METH.get(r.method, r.method), f"<code>{r.feature_set}</code>", D(r.ambang_data_lengkap, 2) if pd.notna(r.ambang_data_lengkap) else "-", D(r.ambang_hanya_data_latih, 2) if pd.notna(r.ambang_hanya_data_latih) else "-",
            f"{I(r.persistence_data_lengkap)} / {I(r.persistence_hanya_data_latih)}" if pd.notna(r.persistence_data_lengkap) else "-", OK(r.status)] for r in leak.itertuples()]),
    '<h4>Tabel 2.7b. Cek silang SQL vs pandas</h4>',
    table(["Fitur atau profil", "Titik dibandingkan", "Pola kosong sama", "Selisih terbesar", "Status"],
          [[f"<code>{r.fitur}</code>", I(r.titik_dibandingkan), r.pola_kosong_sama, f"{r.selisih_maks:.1e}".replace("e-", "E-"), OK(r.status)] for r in xf.itertuples()]),
    f'<p>Cek silang episode alarm: {I(len(xa))} kombinasi metode, ambang, dan persistence, jumlah episode dan episode dalam jendela sama di SQL dan Python.</p></div>')
SEC = {1: "21", 2: "21", 3: "22", 4: "23", 5: "24", 6: "24", 7: "25", 8: "25", 9: "26", 10: "26", 11: "27", 12: "27"}
rp2_body = mk(sec21, sec22, sec23, sec24, sec25, sec26, sec27)
qn_uniq = sorted(set(int(x) for x in re.findall(r'<span class="qn">Q(\d+)</span>', rp2_body)))
assert qn_uniq == list(range(1, 13)), qn_uniq
nw = len(WARN)
wtxt = ", ".join(f"Q{n}" for n in sorted(WARN))
chips = '<div class="qchips">' + "".join(f'<a class="qc{" w" if n in WARN else ""}" href="#sec{SEC[n]}" title="{esc(QT[n])}">Q{n}</a>' for n in range(1, 13)) + "</div>"
rp2 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> semua {len(QT)} pertanyaan terjawab ({npr["Utama"]} Utama, {npr["Pendukung"]} Pendukung, {npr["Tambahan"]} Tambahan). '
         f'{nw} jawaban dengan catatan (kuning): {wtxt}. Klik nomor pertanyaan untuk melompat ke pembahasannya. Hanya 4 kejadian berlabel, jadi semua kesimpulan bersifat indikatif.</p>',
         chips, '<p class="report-note">Q hijau = terjawab, Q kuning = terjawab dengan catatan. Pembahasan dikelompokkan per grafik atau tabel bukti (2.1 sampai 2.7).</p></div>', rp2_body)

# ---------------------------------------------------------------- 3-5. dataset, tools, alur
CODE_REL = "project/code/"
allcode = list((REPO / CODE_REL).rglob("*.py"))
npy, loc = len(allcode), sum(len(p.read_text(encoding="utf-8").splitlines()) for p in allcode)
nsql = len(list((REPO / CODE_REL).rglob("*.sql")))
rp3 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> dataset sesuai rancangan (NAB v1.1, {I(dbc["sensor_readings"])} titik, {I(n_win)} jendela, repositori berlisensi AGPL v3). Dua dari lima hipotesis tidak didukung data (pola harian dan celah waktu), dua sebagian benar, satu terbukti sebagian. '
         'Tabel features dibuat sebagai view, bukan tabel.</p></div>',
         table(["Aspek", "Rancangan", "Realisasi", "Verdict"], [
             ["Sumber", "NAB v1.1, <code>machine_temperature_system_failure</code>, akses 25 Oktober 2026", f"Diunduh skrip dari tag {dlog.version[0]}; {I(len(dlog))} file dicatat di <code>download_log.csv</code>", OK("Sesuai")],
             ["Ukuran", "22.695 titik, 2 kolom, interval 5 menit, 4 jendela berlabel", f"{I(dbc['sensor_readings'])} titik, {I(dqt['interval 5 menit normal'])} selisih tepat 5 menit, {I(n_win)} jendela", OK("Sesuai")],
             ["Lisensi dan sitasi", "AGPL v3 (repositori NAB); Lavin dan Ahmad (2015)", "Dicatat di <code>project/data/README.md</code>; file data tidak di-commit", OK("Sesuai")],
             ["Tabel", "sensor_readings, features, anomaly_windows, alarms", "Keempatnya; <code>features</code> berupa view SQL (selalu konsisten dengan data), ditambah constraint dan 10 uji penolakan", PART("Sesuai + penyesuaian")],
             ["Hipotesis 1: penyimpangan bertahap sebelum kegagalan, bisa dideteksi lebih awal", "Belum terbukti",
              f"Ambang tetap memberi peringatan {D(fxl.min(), 1)} sampai {D(fxl.max(), 1)} jam dari titik tengah; {I(fx.events_early_all)} dari 4 kejadian lebih awal, kejadian 3 tidak", PART("Sebagian")],
             ["Hipotesis 2: rolling z-score menangkap sebagian besar kejadian", "Belum terbukti",
              f"{I(zs.events_detected_all)} dari 4 kejadian pada ambang terpilih ({I(azs.iloc[0].events_detected)} dari 4 pada |z| > 2), tetapi alarm palsu {D(zs.fa_per_week_all, 2)} per minggu, di atas batas {D(FA_LIMIT, 0)}", PART("Sebagian")],
             ["Hipotesis 3: Isolation Forest mengurangi alarm palsu, belum tentu lebih awal", "Belum terbukti",
              f"Alarm palsu {D(itf.fa_per_week_all, 2)} per minggu, lebih sedikit daripada z-score ({D(zs.fa_per_week_all, 2)}) tetapi lebih banyak daripada ambang tetap ({D(fx.fa_per_week_all, 2)}); lead time rata-rata {D(itf.lead_mean_h_all, 1)} jam", PART("Sebagian")],
             ["Hipotesis 4: ambang tetap memberi lebih banyak alarm palsu karena pola harian", "Belum terbukti",
              f"Pola harian lemah ({P(ps['varians dijelaskan jam dalam sehari (eta^2)'], 1)} variasi) dan ambang tetap justru paling sedikit alarm palsu", NO("Tidak terbukti")],
             ["Hipotesis 5: ada celah waktu kecil di data", "Belum terbukti",
              f"Celah waktu {I(dqt['celah waktu (> 5 menit)'])}; yang ada {I(dqt['timestamp mundur'])} timestamp mundur dan {I(dqt['timestamp ganda (kemunculan kedua)'])} timestamp ganda", NO("Tidak terbukti")],
             ["Contoh aturan: 288 titik, 3 titik berturut-turut", "Usulan awal, bisa disesuaikan", "Dipakai untuk z-score (persistence 3); persistence 1, 3, 6 dibandingkan untuk semua metode", OK("Sesuai")]]))
rp4 = mk('<div class="card"><p><b>Jawaban singkat:</b> semua tools rancangan dipakai. Streamlit dibuat dan diuji lokal tetapi belum di-deploy; statsmodels dan matplotlib ditambahkan.</p></div>',
         table(["Tool", "Rancangan", "Realisasi", "Verdict"], [
             ["DuckDB + SQL", "Memuat CSV, menandai celah waktu, window function", f"<code>sensor.duckdb</code> dengan constraint; {I(nsql)} file SQL; view <code>features</code> memakai window function {I(288)} baris sebelumnya", OK("Sesuai")],
             ["Python (pandas, NumPy)", "Profil data, z-score, evaluasi alarm, cek silang", f"{I(npy)} skrip dan modul, {I(loc)} baris; evaluasi {I(len(ev))} baris konfigurasi", OK("Sesuai")],
             ["scikit-learn", "Isolation Forest sebagai pembanding", f"<code>IsolationForest</code> 200 pohon, seed tetap, dilatih pada data latih saja; {I(len(ifs))} kombinasi fitur", OK("Sesuai")],
             ["Jupyter", "Notebook langkah analisis", "<code>analysis.ipynb</code> dibuat otomatis dari CSV hasil dan dieksekusi tanpa error", OK("Sesuai")],
             ["Streamlit + Plotly", "Dashboard, dipublikasikan lewat link", "<code>streamlit/app.py</code> 3 halaman; diuji dengan <code>AppTest</code>; belum di-deploy", PART("Sebagian")],
             ["GitHub + Markdown", "Kode, query, README; data tidak disimpan", "Struktur dan README siap; berada di branch <code>project-5-build</code>, belum digabung ke <code>main</code>; data tidak di-commit", PART("Sebagian")],
             ["statsmodels dan matplotlib", "Tidak ada di rancangan", "Interval Wilson 95% untuk estimasi dampak; gambar aturan alarm", PART("Tambahan")]]))
steps = [("1", "Menyepakati definisi", "<code>project/docs/definitions.md</code>", PART("Sesuai + penyesuaian"), "Titik tengah jendela sebagai perkiraan waktu kegagalan dan batas alarm palsu 2 per minggu adalah asumsi saya; belum disepakati dengan tim maintenance."),
         ("2", "Mengunduh data dan mendokumentasikan sumber", "<code>01_download_data.py</code>, <code>project/data/README.md</code>", OK("Sesuai"), "Ditambah log unduhan (URL, ukuran, sidik jari)."),
         ("3", "Memprofil data", "<code>02_profile_data.py</code>", PART("Sesuai + temuan"), "Pola harian lemah dan tidak ada celah waktu: hipotesis 4 dan 5 tidak terbukti."),
         ("4", "Memuat data ke database", "<code>03_build_db.py</code>, <code>01_schema.sql</code>, <code>02_load.sql</code>", PART("Sesuai + tambahan"), "Kunci pakai <code>seq</code>; ditambah 10 uji penolakan dan 7 pemeriksaan konsistensi."),
         ("5", "Menghitung fitur bergulir", "<code>03_features.sql</code>, <code>04_run_queries.py</code>", OK("Sesuai"), ""),
         ("6", "Mengevaluasi ambang tetap dan z-score", "<code>06_evaluate_methods.py</code>", OK("Sesuai"), ""),
         ("7", "Menguji Isolation Forest", "<code>06_evaluate_methods.py</code>", OK("Sesuai"), "Lima kombinasi fitur dibandingkan."),
         ("8", "Memilih ambang dan aturan persistence", "<code>07_select_validate.py</code>", PART("Sesuai + tambahan"), "Ditambah sensitivitas batas alarm palsu (1, 2, 5) dan margin sebelum jendela."),
         ("9", "Menghitung lead time dan dampak", "<code>08_lead_time_impact.py</code>", OK("Sesuai"), "Estimasi berlabel estimated."),
         ("10", "Memvalidasi evaluasi", "<code>05_crosscheck_features.py</code>, <code>07_select_validate.py</code>", OK("Sesuai"), "Cek silang SQL vs pandas dan uji kebocoran."),
         ("11", "Membuat dashboard", "<code>09_build_dashboard_data.py</code>, <code>streamlit/app.py</code>", PART("Sebagian"), "Belum di-deploy ke Streamlit Community Cloud."),
         ("12", "Menulis README dan finalisasi", "<code>README.md</code>, <code>12_build_readme.py</code>, halaman ini", PART("Sebagian"), "Siap; digabung ke main setelah ditinjau.")]
renames = [("docs/definitions.md", "project/docs/definitions.md"), ("docs/data_dictionary.md", "project/docs/data_dictionary.md"), ("data/README.md", "project/data/README.md"),
           ("data/raw/*.csv, *.json", "project/data/raw/ (tidak di-commit)"), ("sql/01_load.sql", CODE_REL + "1-data-preparation/sql/01_schema.sql, " + CODE_REL + "1-data-preparation/sql/02_load.sql"),
           ("sql/02_features.sql", CODE_REL + "2-analysis/sql/03_features.sql"), ("sensor.duckdb", "project/sensor.duckdb (tidak di-commit)"),
           ("notebooks/analysis.ipynb", "project/results/3-presentation/analysis.ipynb"), ("outputs/method_evaluation.csv", "project/results/2-analysis/method_evaluation.csv"),
           ("outputs/alarm_rule.md", "project/results/3-presentation/alarm_rule.md, project/results/3-presentation/alarm_rule.png"), ("dashboard/app.py", CODE_REL + "3-presentation/streamlit/app.py"),
           ("requirements.txt", "project/requirements.txt"),
           ("(tidak ada)", ", ".join(CODE_REL + p for p in ("1-data-preparation/python/01_download_data.py", "1-data-preparation/python/02_profile_data.py", "1-data-preparation/python/03_build_db.py",
                                                            "2-analysis/python/04_run_queries.py", "2-analysis/python/05_crosscheck_features.py", "2-analysis/python/06_evaluate_methods.py",
                                                            "2-analysis/python/07_select_validate.py", "2-analysis/python/08_lead_time_impact.py", "2-analysis/python/alarm_lib.py", "common.py")))]
for a, b in renames:
    for part in b.split(", "):
        part = part.split(" (")[0]
        if "*" in part or "/" not in part or "tidak di-commit" in b:
            continue
        assert (REPO / part).exists(), part
rp5 = mk('<div class="card"><p><b>Jawaban singkat:</b> 12 langkah dijalankan sesuai urutan. Nama dan lokasi file berubah mengikuti struktur repo standar, beberapa langkah ditambah (sensitivitas, cek silang, uji kebocoran), dan dua langkah (11 dan 12) belum sepenuhnya selesai.</p></div>',
         table(["Langkah", "Rancangan", "Realisasi", "Verdict", "Catatan"], [[a, b, c, d, e] for a, b, c, d, e in steps]),
         '<div class="card"><h4>Penyesuaian dan improvisasi yang tidak ada di rancangan</h4><ul class="tight">',
         '<li>Titik tengah jendela dipakai sebagai perkiraan waktu kegagalan karena rancangan tidak mendefinisikan lead time; batas alarm palsu 2 per minggu juga asumsi (sensitivitas 1 dan 5 ada di Tabel 2.5a).</li>',
         '<li>Kunci urutan adalah <code>seq</code>, bukan timestamp, karena timestamp mundur satu kali; titik bertanda tetap dipakai.</li>',
         '<li>Sensitivitas margin sebelum jendela (0, 6, 12 jam) ditambahkan karena aturan ketat di dalam jendela menghukum kejadian yang mulai menyimpang sebelum jendela (Tabel 2.6c).</li>',
         f'<li>Uji kebocoran data masa depan ({I(len(leak))} pemeriksaan) dan cek silang SQL vs pandas ({I(len(xf) + len(xa))} pemeriksaan) ditambahkan di luar rancangan.</li>',
         '<li>Tabel <code>features</code> dibuat sebagai view SQL, bukan tabel, supaya selalu konsisten dengan data.</li>',
         '<li>Notebook, aturan alarm, dan angka halaman ini dibuat otomatis dari hasil, dan angka halaman ini diaudit terhadap file hasil.</li></ul></div>',
         '<div class="card"><h4>Perubahan nama dan lokasi file terhadap rancangan</h4>',
         table(["Rancangan", "Realisasi"], [[f"<code>{a}</code>" if a != "(tidak ada)" else "(tidak ada di rancangan)", ", ".join(f"<code>{x}</code>" if "(" not in x else x for x in b.split(", "))] for a, b in renames]) + '</div>')

# ---------------------------------------------------------------- 6. output
chk = lambda rel: (REPO / rel).exists()
outs = [("Dashboard interaktif", "Utama", PART("Sebagian"), "<code>streamlit/app.py</code> (3 halaman: Ringkasan, Grafik suhu, Simulasi ambang) diuji lokal dengan AppTest. Link publik belum ada"),
        ("Aturan alarm usulan", "Utama", OK("Tercapai"), "<code>alarm_rule.md</code> dan <code>alarm_rule.png</code>, dengan lead time dan alarm palsu per minggu"),
        ("Database & query SQL", "Utama", OK("Tercapai"), f"<code>sensor.duckdb</code> (dibuat ulang, tidak di-commit) dan {I(nsql)} file SQL"),
        ("Tabel evaluasi metode", "Utama", OK("Tercapai"), f"<code>method_evaluation.csv</code>, {I(len(ev))} baris"),
        ("Notebook analisis", "Utama", OK("Tercapai"), "<code>analysis.ipynb</code> dieksekusi tanpa error, mencakup Q1 sampai Q12"),
        ("Laporan temuan & rekomendasi", "Utama", OK("Tercapai"), "<code>README.md</code> dan halaman ini"),
        ("Repositori GitHub", "Utama", PART("Sebagian"), "Struktur dan cara menjalankan ulang siap; berada di branch <code>project-5-build</code>, belum digabung ke <code>main</code>"),
        ("Slide presentasi", "Opsional", NO("Tidak dibuat"), "Opsional, tidak dibuat")]
nU = [o for o in outs if o[1] == "Utama"]
cnt = lambda s: sum(1 for o in nU if s in o[2])
docs = [("docs/definitions.md", "Definisi kejadian, alarm, alarm palsu, lead time", "project/docs/definitions.md"), ("data/README.md", "Sumber, versi, akses, lisensi, sitasi", "project/data/README.md"),
        ("data/raw/*.csv, *.json", "File suhu dan label (tidak di-commit)", "project/data/raw"), ("sql/01_load.sql", "Pemuatan data dan penandaan celah", "project/code/1-data-preparation/sql/02_load.sql"),
        ("sql/02_features.sql", "Fitur bergulir", "project/code/2-analysis/sql/03_features.sql"), ("sensor.duckdb", "File database (tidak di-commit)", "project/sensor.duckdb"),
        ("notebooks/analysis.ipynb", "Notebook", "project/results/3-presentation/analysis.ipynb"), ("outputs/method_evaluation.csv", "Evaluasi per metode dan ambang", "project/results/2-analysis/method_evaluation.csv"),
        ("outputs/alarm_rule.md", "Aturan alarm usulan", "project/results/3-presentation/alarm_rule.md"), ("dashboard/app.py", "Dashboard Streamlit", "project/code/3-presentation/streamlit/app.py"),
        ("requirements.txt", "Paket Python", "project/requirements.txt"), ("README.md", "Laporan temuan", "README.md"), ("index.html", "Pengalihan ke design-and-report/", "index.html"),
        ("slides/presentation.pdf", "Slide", "slides/presentation.pdf")]
stat_doc = lambda rel: PART("Tidak di-commit") if ("duckdb" in rel or "raw" in rel) else (OK("Ada") if chk(rel) else NO("Belum ada"))
rp6 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> {I(cnt("Tercapai"))} dari {I(len(nU))} output Utama tercapai penuh dan {I(cnt("Sebagian"))} sebagian (dashboard belum punya link publik, repositori belum digabung ke main). Slide Opsional tidak dibuat.</p></div>',
         table(["Output", "Label", "Status", "Bukti"], [[f"<b>{a}</b>", b, c, d] for a, b, c, d in outs]),
         '<div class="card"><h4>Daftar dokumen pada rancangan vs repositori</h4>',
         table(["Dokumen (rancangan)", "Isi", "Lokasi sekarang", "Status"], [[f"<code>{a}</code>", b, f"<code>{c}</code>", stat_doc(c)] for a, b, c in docs]),
         '<p>Data mentah, data bersih, dan <code>sensor.duckdb</code> tidak di-commit karena bisa dibuat ulang oleh skrip.</p></div>')

# ---------------------------------------------------------------- 7. kesimpulan
fa_ok = fr.fa_per_week_all <= FA_LIMIT and fr.fa_per_week_test <= FA_LIMIT
crit = [("1. Kedelapan pertanyaan Utama terjawab dengan angka", OK("Tercapai"), "Q1, Q3, Q4, Q5, Q7, Q9, Q11, Q12 terjawab (bagian 2); empat di antaranya dengan catatan"),
        ("2. Aturan alarm mendeteksi minimal 3 dari 4 kejadian sebelum akhir jendela, alarm palsu di bawah batas", OK("Tercapai") if (fr.events_detected_all >= 3 and fa_ok) else NO("Belum"),
         f"{I(fr.events_detected_all)} dari 4 terdeteksi, alarm palsu {D(fr.fa_per_week_all, 2)} per minggu (uji {D(fr.fa_per_week_test, 2)}); batas {D(FA_LIMIT, 0)} per minggu adalah asumsi"),
        ("3. Ambang dipilih hanya dari periode awal, diuji pada periode sesudahnya", OK("Tercapai"), f"{I(len(leak))} pemeriksaan kebocoran PASS (Tabel 2.7a)"),
        ("4. Statistik bergulir dari SQL sama dengan pandas", OK("Tercapai"), f"{I(len(xf))} pemeriksaan fitur dan {I(len(xa))} pemeriksaan alarm PASS"),
        ("5. Orang awam membuka dashboard dan menjelaskan kapan alarm berbunyi dalam &lt; 1 menit", PART("Belum diuji"), "Dashboard dibuat tetapi belum di-deploy dan belum diuji ke pembaca sebenarnya"),
        ("6. Checklist standar (pertanyaan bisnis, cleaning, SQL, dashboard ter-deploy, README)", PART("Sebagian"), "Semua ada kecuali dashboard ter-deploy")]
ncr = sum(1 for c in crit if ">Tercapai<" in c[1])
rp7 = mk(
    '<div class="card"><h4>7.1 Hasil analisis: jawaban atas pertanyaan utama</h4>',
    '<p><i>Kapan alarm suhu harus berbunyi agar kegagalan mesin bisa ditangkap lebih awal, dengan alarm palsu yang masih bisa diterima?</i></p><ul class="tight">',
    f'<li><b>Aturan paling sederhana yang terbaik:</b> alarm jika suhu menyimpang lebih dari {D(fr.threshold, 0)} derajat dari median data latih selama {I(fr.persistence)} titik berturut-turut. {I(fr.events_detected_all)} dari 4 kejadian terdeteksi, {D(fr.fa_per_week_all, 2)} alarm palsu per minggu, lead time rata-rata {D(fr.lead_mean_h_all, 1)} jam.</li>',
    f'<li><b>Metode lebih rumit belum lebih baik:</b> rolling z-score {D(zs.fa_per_week_all, 2)} alarm palsu per minggu, Isolation Forest {D(itf.fa_per_week_all, 2)} per minggu pada konfigurasi yang dipilih dari data latih.</li>',
    f'<li><b>Pola harian lemah:</b> jam dalam sehari hanya menjelaskan {P(ps["varians dijelaskan jam dalam sehari (eta^2)"], 1)} variasi suhu, sehingga ambang tetap cukup.</li>',
    f'<li><b>Dampak (estimated):</b> sekitar {D(i4.jam_downtime_dicegah_per_tahun, 0)} sampai {D(i12.jam_downtime_dicegah_per_tahun, 0)} jam downtime per tahun bisa dicegah, tergantung lama downtime per kegagalan.</li></ul></div>',
    '<div class="card"><h4>7.2 Impact</h4><ul class="tight">',
    f'<li><b>Nilai praktis (estimated):</b> {I(lt.loc["fixed"].events_with_lead_ge_min)} dari 4 kejadian mendapat peringatan minimal {D(MIN_LEAD_H, 0)} jam, cukup untuk menjadwalkan perbaikan sebelum mesin berhenti.</li>',
    '<li><b>Nilai analitis:</b> evaluasi per kejadian (recall, alarm palsu per minggu, lead time) menggantikan akurasi per titik yang menyesatkan karena hampir semua titik normal.</li>',
    '<li><b>Nilai portofolio:</b> pipeline lengkap: data publik berversi, window function SQL, tiga metode, pemisahan data menurut waktu, uji kebocoran, cek silang SQL vs pandas, notebook, dan dashboard.</li>',
    '<li><b>Belum terukur:</b> kegagalan mesin lain, dampak rupiah, dan penerimaan tim maintenance atas batas alarm palsu.</li></ul></div>')
rp7 += ('<div class="card"><h4>7.3 Success criteria</h4>' + table(["Kriteria (Design Project, bagian 8)", "Status", "Bukti"], [[a, b, c] for a, b, c in crit])
        + f'<p><b>Hasil:</b> {I(ncr)} dari {I(len(crit))} kriteria tercapai, {I(len(crit) - ncr)} sebagian atau belum diuji.</p></div>')
rp7 += mk('<div class="card"><h4>7.4 Rekomendasi</h4><ul class="tight">',
          f'<li>Mulai dari aturan ambang tetap ±{D(fr.threshold, 0)} derajat dengan {I(fr.persistence)} titik berturut-turut sebagai alarm awal, dan pantau alarm di luar jendela untuk memeriksa apakah itu gangguan nyata.</li>',
          '<li>Sepakati batas alarm palsu per minggu dengan tim maintenance; hasil tidak berubah pada batas 1, 2, dan 5 per minggu.</li>',
          '<li>Pakai Isolation Forest hanya jika data lebih banyak tersedia; pada 4 kejadian ia belum membuktikan keunggulan atas aturan sederhana.</li>',
          '<li>Laporkan kinerja alarm per kejadian (terdeteksi, lead time, alarm palsu per minggu), bukan akurasi per titik.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.5 Saran perbaikan</h4><ul class="tight">',
          '<li>Uji aturan pada mesin dan kejadian lain di NAB atau data pabrik sendiri; 4 kejadian dari satu mesin tidak cukup untuk menyimpulkan.</li>',
          '<li>Minta waktu kegagalan sebenarnya dari log maintenance supaya lead time tidak bergantung pada titik tengah jendela.</li>',
          '<li>Periksa alarm di luar jendela terhadap catatan operasional; sebagian mungkin gangguan nyata yang tidak dilabeli.</li>',
          '<li>Deploy dashboard ke Streamlit Community Cloud dan uji ke satu pembaca awam untuk mengisi kriteria 5 dan 6.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.6 Batasan</h4><ul class="tight">',
          '<li>Hanya 4 kejadian (2 latih, 2 uji): satu kejadian yang terlewat mengubah recall 25 poin, jadi hasil bersifat indikatif.</li>',
          '<li>Jendela NAB adalah rentang di sekitar kejadian; titik tengah hanya perkiraan waktu kegagalan, dan alarm di luar jendela belum tentu alarm palsu.</li>',
          f'<li>Batas alarm palsu {D(FA_LIMIT, 0)} per minggu, minimal peringatan {D(MIN_LEAD_H, 0)} jam, dan downtime per kegagalan adalah asumsi; estimasi kegagalan per tahun diekstrapolasi dari kurang dari 3 bulan data.</li>',
          '<li>Satu mesin tidak mewakili semua mesin; ambang terbaik bisa berbeda.</li>',
          '<li>Dashboard belum di-deploy dan kriteria 5 dan 6 belum terpenuhi. Slide presentasi (Opsional) tidak dibuat. Lisensi repositori NAB: AGPL v3 (cakupannya untuk berkas data belum dipastikan).</li></ul></div>')

evq = [("1", "rp1", "Data yang didapat", OK("Didapat"), f"{I(dbc['sensor_readings'])} titik suhu, {I(n_win)} jendela berlabel, {I(dbc['alarms'])} episode alarm dievaluasi"),
       ("2", "rp2", "Business question terjawab?", OK(f"{len(QT)} dari {len(QT)}"), f"Semua terjawab ({npr['Utama']} Utama, {npr['Pendukung']} Pendukung, {npr['Tambahan']} Tambahan); {nw} dengan catatan ({wtxt})"),
       ("3", "rp3", "Dataset sesuai?", PART("Sesuai + temuan"), "Dataset sesuai; dua hipotesis tidak terbukti, tiga sebagian"),
       ("4", "rp4", "Tools sesuai?", PART("Sesuai + tambahan"), "Semua tools dipakai; Streamlit belum di-deploy"),
       ("5", "rp5", "Alur sesuai?", PART("Sesuai + penyesuaian"), "12 langkah dijalankan; sensitivitas dan uji kebocoran ditambahkan"),
       ("6", "rp6", "Output tercapai?", PART(f"{cnt('Tercapai')} penuh, {cnt('Sebagian')} sebagian"), f"{cnt('Tercapai')} dari {len(nU)} output Utama penuh"),
       ("7", "rp7", "Kesimpulan", OK("Tersedia"), f"Hasil analisis, Impact, {len(crit)} kriteria sukses, rekomendasi, saran perbaikan, batasan")]
evq_html = '<div class="scroll"><table class="evq"><tr><th>No</th><th>Pertanyaan evaluasi</th><th>Verdict</th><th>Ringkasan</th></tr>' + "".join(
    f'<tr><td><span class="en">{n}</span></td><td><a href="#{h}">{t}</a></td><td>{v}</td><td>{s}</td></tr>' for n, h, t, v, s in evq) + "</table></div>"
H = lambda i, t, sm, body: f'\n<h2 id="rp{i}">{i}. {t}<small>{sm}</small></h2>\n{body}\n'
report = mk(
    '<div class="pane" id="report" data-tab="report" hidden>\n',
    '<div class="callout g"><h4>Report Project versi 2: evaluasi hasil terhadap Design Project</h4><p>Halaman ini disusun sebagai 7 jawaban atas pertanyaan evaluasi. Tabel dan grafik dibuat otomatis dari hasil query SQL (DuckDB) dan evaluasi alarm pada data NAB. '
    f'Hasil SQL dicek silang dengan pandas ({I(len(xf) + len(xa))} pemeriksaan). Angka pada teks diaudit terhadap file di <code>project/results/</code>: @@AUDIT@@ angka diperiksa tanpa selisih. '
    'Hanya 4 kejadian berlabel, jadi semua kesimpulan bersifat indikatif. Rancangan lengkap ada di tab <a href="#design">Design Project</a>.</p></div>\n',
    evq_html,
    H(1, "Data yang berhasil didapatkan", "Isi data mentah, tabel di database, dan data hasil analisis", rp1),
    H(2, "Apakah business question terjawab?", f"{len(QT)} pertanyaan pada Design Project, dijawab dengan data", rp2),
    H(3, "Apakah dataset sesuai dengan Design Project?", "Perbandingan rancangan dengan realisasi", rp3),
    H(4, "Apakah tools yang digunakan sesuai?", "Perbandingan rancangan dengan eksekusi", rp4),
    H(5, "Apakah alur pengerjaan sesuai dengan Design Project?", f"{len(steps)} langkah rancangan vs yang dijalankan", rp5),
    H(6, "Apakah project output tercapai?", "Output pada Design Project, bagian 7", rp6),
    H(7, "Kesimpulan", "Hasil analisis, Impact, success criteria, rekomendasi, saran perbaikan, dan batasan", rp7),
    '</div>\n')

# ---------------------------------------------------------------- audit angka
STATIC = {str(i) for i in range(0, 21)} | {f"{i:02d}" for i in range(0, 13)} | {"30", "100", "50", "25", "24", "72", "288", "200", "2013", "2014", "2015", "2026", "22.695", "1E-10", "95", "40", "60", "12", "22",
                                                                                   "0,05", "1E-9", "31", "15", "19"}
STATIC |= {f"{a}.{b}" for a in range(1, 10) for b in range(1, 10)}
n_tok, bad = audit(report, STATIC)
manual = [("seluruh CSV hasil terdokumentasi", not miss), ("crosscheck fitur dan alarm semua PASS", (xf.status == "PASS").all() and (xa.status == "PASS").all()),
          ("uji kebocoran semua PASS", (leak.status == "PASS").all()), ("semua uji constraint ditolak", (ctest.outcome == "ditolak").all()),
          ("semua pemeriksaan konsistensi 0 pelanggaran", (cons.violations == 0).all()), ("jumlah pertanyaan = 12 (8 Utama, 3 Pendukung, 1 Tambahan)", len(QT) == 12 and npr == {"Utama": 8, "Pendukung": 3, "Tambahan": 1}),
          ("catatan hanya Q3, Q5, Q7, Q9, Q10", WARN == {3, 5, 7, 9, 10}), ("langkah rancangan = 12", len(steps) == 12), ("jumlah pertanyaan unik pada bagian 2 = 12", qn_uniq == list(range(1, 13))),
          ("aturan terpilih = baris final_rule", (fx.threshold, fx.persistence) == (fr.threshold, fr.persistence)), ("periode latih dan uji menutup seluruh jendela", fr.events_total_train + fr.events_total_test == n_win),
          ("episode semua data = latih + uji", int(fr.episodes_all) == int(fr.episodes_test) + int(fr.episodes_train)),
          ("jumlah baris evaluasi = 3 periode x konfigurasi", len(ev) % 3 == 0), ("jam dicegah naik menurut downtime", i4.jam_downtime_dicegah_per_tahun < i8.jam_downtime_dicegah_per_tahun < i12.jam_downtime_dicegah_per_tahun)]
assert all(v for _, v in manual), [k for k, v in manual if not v]
if bad:
    print("TOKEN TIDAK TERDAFTAR:", bad)
    sys.exit(1)
report = report.replace("@@AUDIT@@", I(n_tok) + f" (ditambah {I(len(manual))} klaim manual)")

# ---------------------------------------------------------------- rakit halaman
v1 = (HERE / "page_v1.html").read_text(encoding="utf-8")
a = v1.index('<div class="pane" id="report"')
b = v1.index("</main>")
design_pane = v1[v1.index('<div class="pane" id="design"'):a]
nav_old = re.search(r'<nav aria-label="Project navigation">.*?</nav>', v1, re.S).group(0)
btn = lambda t: re.search(rf'<button type="button" class="tab[^"]*" data-t="{t}".*?</button>', nav_old, re.S).group(0)
design_links = re.search(r'<div class="links" data-tab="design">.*?</div>', nav_old, re.S).group(0)
report_links = ('<div class="links" data-tab="report" hidden>' + "".join(f'<a href="#rp{i}">{t}</a>' for i, t in
               enumerate(["Data", "Business Questions", "Dataset", "Tools", "Alur Kerja", "Project Output", "Kesimpulan"], 1)) + "</div>")
nav_new = f'<nav aria-label="Project navigation">{btn("design")}{btn("report")}{design_links}{report_links}</nav>'
css = (HERE / "report.css").read_text(encoding="utf-8")
html = v1[:a] + report + v1[b:]
html = html.replace(nav_old, nav_new)
i = html.rindex("</style>")
html = html[:i] + css + html[i:]
out = REPO / "design-and-report" / "index.html"
out.write_text(html, encoding="utf-8")
assert design_pane == html[html.index('<div class="pane" id="design"'):html.index('<div class="pane" id="report"')], "pane Design berubah"
print(f"index.html {len(html) / 1024:.0f} KB; {n_tok} angka diaudit; {len(manual)} klaim manual; pane Design identik")
