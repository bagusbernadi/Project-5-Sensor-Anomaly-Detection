# Kamus data (Project 5)

## `sensor_readings` (22.695 baris)
| Kolom | Arti |
|---|---|
| `seq` | Urutan baris asli, 1..N (kunci utama, dipakai untuk mengurutkan) |
| `ts` | Timestamp bacaan, interval 5 menit. Tidak unik (lihat `gap_flag`) |
| `value` | Suhu mesin (satuan mengikuti sumber NAB, dibaca sebagai derajat) |
| `gap_flag` | `ok`, `ts_mundur`, `ts_ganda`, `celah` |

## `anomaly_windows` (4 baris, tabel referensi)
| Kolom | Arti |
|---|---|
| `window_id` | 1..4 menurut urutan waktu |
| `start_ts`, `end_ts` | Awal dan akhir jendela berlabel NAB |
| `source` | Sumber label (NAB v1.1, `combined_windows.json`) |

## `features` (view, bukan tabel)
`seq`, `ts`, `value`, `roll_mean_24h`, `roll_std_24h`, `z_score`, `dev_mean`, `slope_6h`. Definisi di `definitions.md`.

## `alarms` (satu baris = satu episode alarm dari satu metode, ambang, dan persistence)
| Kolom | Arti |
|---|---|
| `alarm_id` | Nomor urut |
| `method` | `fixed`, `zscore`, atau `iforest` |
| `feature_set` | Kombinasi fitur Isolation Forest; `-` untuk metode lain |
| `threshold` | Ambang (derajat, nilai z, atau skor Isolation Forest) |
| `persistence` | Jumlah titik berturut-turut yang disyaratkan |
| `seq`, `ts` | Titik pertama alarm menyala |
| `score` | Skor di titik itu |
| `window_id` | Jendela berlabel yang memuat alarm; kosong jika di luar jendela |
| `in_window` | Benar jika di dalam jendela (kosong `window_id` berarti alarm palsu) |
