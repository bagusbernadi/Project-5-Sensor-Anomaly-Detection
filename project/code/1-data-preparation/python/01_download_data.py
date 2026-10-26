"""Mengunduh file NAB v1.1 (data suhu dan label jendela) dari repositori resmi Numenta (lisensi MIT)."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

C.RAW_DIR.mkdir(parents=True, exist_ok=True)
C.RES_PREP.mkdir(parents=True, exist_ok=True)
rows = []
for rel, dest in ((C.NAB_DATA_PATH, C.RAW_CSV), (C.NAB_LABEL_PATH, C.RAW_LABELS)):
    url = C.NAB_BASE + rel
    with urllib.request.urlopen(url, timeout=60) as r:
        blob = r.read()
    dest.write_bytes(blob)
    rows.append(dict(file=dest.name, url=url, bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest()[:16]))
    print(dest.name, len(blob), "byte")
labels = json.loads(C.RAW_LABELS.read_text())[C.NAB_LABEL_KEY]
assert len(labels) == 4, "jumlah jendela berlabel tidak sesuai rancangan"
pd.DataFrame(rows).assign(version=f"NAB {C.NAB_TAG}", access_date=C.ACCESS_DATE).to_csv(C.RES_PREP / "download_log.csv", index=False)
