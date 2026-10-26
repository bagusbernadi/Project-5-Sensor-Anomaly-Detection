"""Pengaturan bersama untuk semua skrip. Semua jalur relatif terhadap folder project/."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # folder project/
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"                                 # file NAB asli (tidak di-commit)
CLEAN_DIR = DATA / "clean"                             # data bersih + fitur (tidak di-commit)
RAW_CSV = RAW_DIR / "machine_temperature_system_failure.csv"
RAW_LABELS = RAW_DIR / "combined_windows.json"
DB_PATH = ROOT / "sensor.duckdb"
CODE = ROOT / "code"
SQL_PREP = CODE / "1-data-preparation" / "sql"
SQL_ANALYSIS = CODE / "2-analysis" / "sql"
RES_PREP = ROOT / "results" / "1-data-preparation"
RES_ANALYSIS = ROOT / "results" / "2-analysis"
RES_PRESENT = ROOT / "results" / "3-presentation"
DOCS_DIR = ROOT / "docs"
for _d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):     # folder hasil dibuat otomatis saat menjalankan dari repo bersih
    _d.mkdir(parents=True, exist_ok=True)

# Sumber data (NAB v1.1, lisensi MIT)
NAB_TAG = "v1.1"
NAB_BASE = f"https://raw.githubusercontent.com/numenta/NAB/{NAB_TAG}/"
NAB_DATA_PATH = "data/realKnownCause/machine_temperature_system_failure.csv"
NAB_LABEL_PATH = "labels/combined_windows.json"
NAB_LABEL_KEY = "realKnownCause/machine_temperature_system_failure.csv"
ACCESS_DATE = "25 Oktober 2026"                        # tanggal akses dari user (halaman rancangan)

# Definisi evaluasi (lihat docs/definitions.md)
WINDOW_POINTS = 288                                    # 24 jam x 12 titik per jam
SLOPE_POINTS = 72                                      # 6 jam
COOLDOWN = 12                                          # 1 jam tenang menutup satu episode alarm
FA_LIMIT = 2.0                                         # batas alarm palsu per minggu (asumsi, dapat diubah)
FA_LIMITS_SENS = [1.0, 2.0, 5.0]
TRAIN_END = "2014-01-01"                               # ambang dipilih dari data sebelum tanggal ini
K_LIST = [1, 3, 6]                                     # syarat titik berturut-turut
K_DEFAULT = 3
MARGINS_H = [0, 6, 12]                                 # sensitivitas: alarm sebelum jendela dihitung dini
SEED = 20261025

# Asumsi dampak (estimated)
DOWNTIME_H = [4, 8, 12]                                # jam downtime darurat per kegagalan (asumsi)
MIN_LEAD_H = 2.0                                       # peringatan minimal agar perbaikan sempat dijadwalkan (asumsi)


def result(name):
    """Cari CSV hasil di folder hasil per tahap."""
    for d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def chdir_root():
    os.chdir(ROOT)
