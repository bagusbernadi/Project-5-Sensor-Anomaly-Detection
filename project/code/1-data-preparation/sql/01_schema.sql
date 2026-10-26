-- Skema database sensor.duckdb (dijalankan dari folder project/)
CREATE OR REPLACE TABLE sensor_readings (
    seq       INTEGER PRIMARY KEY,                       -- urutan baris asli (kunci pengurutan, bukan timestamp)
    ts        TIMESTAMP NOT NULL,                        -- tidak unik: ada waktu mundur satu kali (lihat docs/definitions.md)
    value     DOUBLE NOT NULL CHECK (value BETWEEN -50 AND 200),
    gap_flag  VARCHAR NOT NULL CHECK (gap_flag IN ('ok', 'ts_mundur', 'ts_ganda', 'celah'))
);
CREATE OR REPLACE TABLE anomaly_windows (
    window_id INTEGER PRIMARY KEY,
    start_ts  TIMESTAMP NOT NULL,
    end_ts    TIMESTAMP NOT NULL,
    source    VARCHAR NOT NULL,
    CHECK (end_ts > start_ts)
);
CREATE OR REPLACE TABLE alarms (
    alarm_id    INTEGER PRIMARY KEY,
    method      VARCHAR NOT NULL CHECK (method IN ('fixed', 'zscore', 'iforest')),
    feature_set VARCHAR NOT NULL,                        -- untuk iforest: kombinasi fitur; selain itu '-'
    threshold   DOUBLE NOT NULL,
    persistence INTEGER NOT NULL CHECK (persistence >= 1),
    seq         INTEGER NOT NULL REFERENCES sensor_readings (seq),
    ts          TIMESTAMP NOT NULL,
    score       DOUBLE NOT NULL,
    window_id   INTEGER REFERENCES anomaly_windows (window_id),   -- NULL = alarm di luar jendela (alarm palsu)
    in_window   BOOLEAN NOT NULL,
    CHECK ((window_id IS NULL) = (NOT in_window))
);
