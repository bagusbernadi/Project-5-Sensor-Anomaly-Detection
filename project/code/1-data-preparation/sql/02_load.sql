-- Memuat data (dibuat oleh 02_profile_data.py) ke tabel; dijalankan dari folder project/
INSERT INTO sensor_readings
SELECT seq, ts, value, gap_flag FROM read_csv('data/clean/sensor_readings.csv', header = true);
INSERT INTO anomaly_windows
SELECT window_id, start_ts, end_ts, source FROM read_csv('data/clean/anomaly_windows.csv', header = true);
