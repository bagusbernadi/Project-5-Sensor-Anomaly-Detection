# Data (Project 5)

File data tidak disimpan di repositori. `code/1-data-preparation/python/01_download_data.py` mengunduhnya ke `data/raw/`.

| Item | Keterangan |
|---|---|
| Dataset | Numenta Anomaly Benchmark (NAB), `machine_temperature_system_failure` |
| Sumber | [here](https://github.com/numenta/NAB/blob/v1.1/data/realKnownCause/machine_temperature_system_failure.csv) (Versi: NAB v1.1, Tanggal akses: 25 Oktober 2026) |
| Label | `labels/combined_windows.json` (NAB v1.1), kunci `realKnownCause/machine_temperature_system_failure.csv` |
| Lisensi | MIT (repositori NAB) |
| Sitasi | Lavin, A. & Ahmad, S. (2015). Evaluating Real-time Anomaly Detection Algorithms: the Numenta Anomaly Benchmark. |
| Ukuran | 22.695 titik, 2 kolom (`timestamp`, `value`), interval 5 menit, 2013-12-02 21:15 sampai 2014-02-19 15:25, 4 jendela berlabel |

`results/1-data-preparation/download_log.csv` mencatat URL, ukuran file, dan sidik jari (sha256 sebagian) tiap file yang diunduh. Unduh dengan:

```
cd project/code/1-data-preparation/python && python 01_download_data.py
```
