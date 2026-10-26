"""Dashboard Streamlit: suhu mesin, jendela kegagalan, alarm tiap metode, simulasi ambang.
Hanya membaca CSV di results/ (jalankan dari mana saja: streamlit run app.py)."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RES = Path(__file__).resolve().parents[3] / "results"
P, A_ = RES / "3-presentation", RES / "2-analysis"
st.set_page_config(page_title="Sensor Anomaly Detection", layout="wide")


@st.cache_data
def load():
    s = pd.read_csv(P / "dash_series.csv", parse_dates=["ts"])
    w = pd.read_csv(P / "dash_windows.csv", parse_dates=["start_ts", "end_ts", "mid_ts"])
    a = pd.read_csv(P / "dash_alarms.csv", parse_dates=["ts"])
    sim = pd.read_csv(P / "dash_threshold_sim.csv")
    fr = pd.read_csv(A_ / "final_rule.csv").iloc[0]
    lt = pd.read_csv(A_ / "lead_time.csv")
    return s, w, a, sim, fr, lt


s, w, a, sim, fr, lt = load()
page = st.sidebar.radio("Halaman", ["Ringkasan", "Grafik suhu", "Simulasi ambang"])
st.title("Project 5: Sensor Time-Series Anomaly Detection")
st.caption("Data NAB v1.1 (machine_temperature_system_failure), 4 kejadian berlabel. Semua kesimpulan bersifat indikatif.")

if page == "Ringkasan":
    c = st.columns(4)
    c[0].metric("Kejadian terdeteksi", f"{int(fr.events_detected_all)} dari {int(fr.events_total_all)}")
    c[1].metric("Dengan peringatan dini", f"{int(fr.events_early_all)} dari {int(fr.events_total_all)}")
    c[2].metric("Alarm palsu per minggu", f"{fr.fa_per_week_all:.2f}")
    c[3].metric("Lead time rata-rata (jam)", f"{fr.lead_mean_h_all:.1f}")
    st.markdown(f"**Aturan terpilih (dari data latih saja):** ambang tetap ±{fr.threshold:g} derajat dari median, "
                f"alarm jika {int(fr.persistence)} titik berturut-turut. Data uji: {int(fr.events_detected_test)} dari "
                f"{int(fr.events_total_test)} kejadian, {fr.fa_per_week_test:.2f} alarm palsu per minggu, precision {fr.precision_test:.2f}.")
    st.subheader("Perbandingan metode (lead time, jam)")
    st.dataframe(lt.rename(columns={"events_detected": "terdeteksi", "events_with_lead_ge_min": "lead ≥ 2 jam",
                                    "lead_mean_h": "rata-rata", "lead_median_h": "median", "lead_min_h": "min", "lead_max_h": "maks"}),
                 hide_index=True)
    st.info("Alarm di luar jendela belum tentu salah: NAB hanya melabeli 4 kejadian.")

elif page == "Grafik suhu":
    labels = sorted(a.label.unique())
    pick = st.multiselect("Metode", labels, default=labels[:1])
    fig = go.Figure(go.Scattergl(x=s.ts, y=s.value, mode="lines", name="Suhu", line=dict(color="#5f6368", width=1)))
    for r in w.itertuples():
        fig.add_vrect(x0=r.start_ts, x1=r.end_ts, fillcolor="#d93025", opacity=0.12, line_width=0)
        fig.add_vline(x=r.mid_ts, line_dash="dot", line_color="#d93025")
    colors = ["#1a73e8", "#188038", "#e37400"]
    for i, lb in enumerate(pick):
        m = a[a.label == lb]
        for ok, nm, sym in ((True, "di jendela", "triangle-up"), (False, "alarm palsu", "x")):
            d = m[m.in_window == ok]
            fig.add_trace(go.Scatter(x=d.ts, y=[s.set_index("seq").value.get(q) for q in d.seq], mode="markers",
                                     name=f"{lb}: {nm}", marker=dict(symbol=sym, size=10, color=colors[i % 3])))
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Suhu", legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    st.caption("Area merah = jendela berlabel; garis titik = titik tengah (perkiraan waktu kegagalan).")

else:
    k = st.select_slider("Persistence (titik berturut-turut)", sorted(sim.persistence.unique()), value=6)
    d = sim[sim.persistence == k]
    limit = st.slider("Batas alarm palsu per minggu", 0.5, 10.0, 2.0, 0.5)
    d = d.assign(memenuhi=d.fa_per_week <= limit)
    st.dataframe(d.rename(columns={"threshold": "ambang ± derajat", "events_detected": "terdeteksi", "events_early": "dini",
                                   "false_alarms": "alarm palsu", "fa_per_week": "alarm palsu/minggu", "lead_mean_h": "lead rata-rata (jam)"})
                 [["ambang ± derajat", "terdeteksi", "dini", "alarm palsu", "alarm palsu/minggu", "lead rata-rata (jam)", "memenuhi"]],
                 hide_index=True)
    ok = d[d.memenuhi]
    if len(ok):
        b = ok.sort_values(["events_detected", "fa_per_week"], ascending=[False, True]).iloc[0]
        st.success(f"Ambang terbaik pada batas ini: ±{b.threshold:g} derajat ({int(b.events_detected)} dari {int(b.events_total)} kejadian).")
    else:
        st.warning("Tidak ada ambang yang memenuhi batas ini.")
    st.caption("Simulasi memakai seluruh data (latih + uji), hanya untuk eksplorasi. Pemilihan resmi memakai data latih saja.")
