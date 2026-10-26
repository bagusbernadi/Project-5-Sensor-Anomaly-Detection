-- Fitur bergulir dengan window function (langkah 5). Jendela = 288 titik SEBELUM titik ini (24 jam, tidak termasuk titik sekarang),
-- diurutkan menurut seq. Fitur baru terisi setelah 288 titik tersedia (warm-up 24 jam).
CREATE OR REPLACE VIEW features AS
WITH w AS (
    SELECT seq, ts, value,
           avg(value)         OVER p AS m,
           stddev_samp(value) OVER p AS s,
           count(value)       OVER p AS n,
           regr_slope(value, seq) OVER (ORDER BY seq ROWS BETWEEN 71 PRECEDING AND CURRENT ROW) AS slope_pt,
           count(value) OVER (ORDER BY seq ROWS BETWEEN 71 PRECEDING AND CURRENT ROW) AS n_slope
    FROM sensor_readings
    WINDOW p AS (ORDER BY seq ROWS BETWEEN 288 PRECEDING AND 1 PRECEDING)
)
SELECT seq, ts, value,
       CASE WHEN n = 288 THEN m END                            AS roll_mean_24h,
       CASE WHEN n = 288 THEN s END                            AS roll_std_24h,
       CASE WHEN n = 288 AND s > 0 THEN (value - m) / s END    AS z_score,
       CASE WHEN n = 288 THEN value - m END                    AS dev_mean,
       CASE WHEN n_slope = 72 THEN slope_pt * 12 END           AS slope_6h        -- derajat per jam
FROM w;

-- Hari dan jam untuk profil harian (dipakai di Q1)
CREATE OR REPLACE VIEW v_hour_profile AS
SELECT hour(ts) AS hour, avg(value) AS mean, stddev_samp(value) AS std, count(*) AS n
FROM sensor_readings s
WHERE NOT EXISTS (SELECT 1 FROM anomaly_windows a WHERE s.ts BETWEEN a.start_ts AND a.end_ts)
GROUP BY 1 ORDER BY 1;

-- Alarm per metode dan ambang, dievaluasi dari tabel alarms (dipakai untuk memeriksa hasil Python)
CREATE OR REPLACE VIEW v_alarm_eval AS
SELECT method, feature_set, threshold, persistence,
       count(*)                                          AS episodes,
       count(*) FILTER (WHERE in_window)                 AS episodes_in_window,
       count(*) FILTER (WHERE NOT in_window)             AS false_alarms,
       count(DISTINCT window_id)                         AS events_detected
FROM alarms GROUP BY ALL;
