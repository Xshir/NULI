import streamlit as st
import pandas as pd
import random
import json
import datetime
import requests
import time
import re
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components
import plotly.graph_objects as go
import os # Add this import

# --- CONFIGURATION ---
# Use environment variable for Docker, default to localhost for local testing
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_URL = f"http://{OLLAMA_HOST}:11434/api/generate"
MODEL_NAME = "llama3"

# --- PAGE SETUP & UI STYLING ---
st.set_page_config(page_title="Team Noctilucent: Intelligence Suite", layout="wide")

st.markdown("""
    <style>
    /* Golden Sliders, Progress Bar, and Buttons */
    .stSlider > div [data-baseweb="slider"] [role="slider"] { background-color: #FFD700 !important; }
    .stSlider > div [data-baseweb="slider"] > div > div { background: #FFD700 !important; }
    .stProgress > div > div > div > div { background-color: #FFD700 !important; }
    
    /* Text Color Enhancements */
    h1, h2, h3, .stMetric, [data-testid="stMetricValue"] { color: #FFD700 !important; }
    </style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if 'files' not in st.session_state: st.session_state['files'] = None
if 'results' not in st.session_state: st.session_state['results'] = []
if 'ai_cache' not in st.session_state: st.session_state['ai_cache'] = {}
if 'macro_plan' not in st.session_state: st.session_state['macro_plan'] = ""
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []

# --- 1. THE 10-FILE UNIVERSAL GENERATOR (Phase-Shift Physics) ---
def generate_files(profile, severity, length=10):
    timestamp = datetime.datetime.now()
    files = {"JSON_A": [], "JSON_B": [], "XML_A_RAW": [], "XML_B_RAW": [], "TEXT_A": [], "TEXT_B": [], "SYS_A": [], "SYS_B": [], "KV_A": [], "KV_B": []}
    root_a = ET.Element("ToolLog", {"Vendor": "Vendor_A"})
    root_b = ET.Element("SensorExport", {"Vendor": "Vendor_B"})

    pressure_a, pressure_b = 0.9, 0.9
    
    for i in range(length):
        timestamp += datetime.timedelta(seconds=10)
        ts_iso, ts_text = timestamp.isoformat(), timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")

        if profile == "Slow Leak": 
            pressure_a += (i * 0.05 * (severity / 5))
            if i > length // 3: pressure_b += ((i - length//3) * 0.05 * (severity / 5))
        elif profile == "Sudden Burst": 
            if i > length // 4: pressure_a += random.uniform(3.0, 5.0)
            else: pressure_a += random.uniform(-0.02, 0.02)
            if i > (length // 4) * 3: pressure_b += random.uniform(3.0, 5.0)
            else: pressure_b += random.uniform(-0.02, 0.02)
        elif profile == "Ghost Fault": 
            pressure_a = 0.9 + (random.choice([0, 2.0, 0.5, 3.1]) * (severity / 5))
            pressure_b = 0.9 + (random.choice([0, 0, 1.0, 3.5]) * (severity / 5))
        else: 
            pressure_a += random.uniform(-0.02, 0.02)
            pressure_b += random.uniform(-0.02, 0.02)

        p_val_a, p_val_b = round(pressure_a, 3), round(pressure_b, 3)
        status_a = "ALARM: VACUUM_FAULT" if p_val_a > 3.5 else "STATUS_OK"
        status_b = "ALARM: VACUUM_FAULT" if p_val_b > 3.5 else "STATUS_OK"

        files["JSON_A"].append({"id": "MCH_A01", "time": ts_iso, "val": p_val_a, "fw": "v2.1"})
        files["TEXT_A"].append(f"[{ts_text}] ID:MCH_A01 VENDOR:Vendor_A VAL:{p_val_a}Pa FW:v2.1 {status_a}")
        files["SYS_A"].append(f"<14> {ts_iso} MCH_A01 VENDOR_A - - VAL:{p_val_a}Pa FW:v2.1 {status_a}")
        files["KV_A"].append(f"timestamp={ts_iso} ID=MCH_A01 vendor=Vendor_A Pressure={p_val_a} FW=v2.1 status={status_a}")
        files["XML_A_RAW"].append(f"<Entry><T>{ts_iso}</T><P>{p_val_a}</P></Entry>")
        ea = ET.SubElement(root_a, "Entry"); ET.SubElement(ea, "T").text = ts_iso; ET.SubElement(ea, "P").text = str(p_val_a)

        files["JSON_B"].append({"machine_code": "MCH_B02", "timestamp": ts_iso, "pressure_reading": p_val_b, "ch": "C1"})
        files["TEXT_B"].append(f"{ts_text} | MCH_B02 | Vendor_B | Pressure={p_val_b} | CH=C1 | {status_b}")
        files["SYS_B"].append(f"<14> {ts_iso} MCH_B02 VENDOR_B - - Pressure={p_val_b}Pa CH=C1 {status_b}")
        files["KV_B"].append(f"timestamp={ts_iso} ID=MCH_B02 vendor=Vendor_B Pressure={p_val_b} CH=C1 status={status_b}")
        files["XML_B_RAW"].append(f"<Reading><DateTime>{ts_iso}</DateTime><Vacuum_Pa>{p_val_b}</Vacuum_Pa></Reading>")
        eb = ET.SubElement(root_b, "Reading"); ET.SubElement(eb, "DateTime").text = ts_iso; ET.SubElement(eb, "Vacuum_Pa").text = str(p_val_b)

    files["XML_A_DISPLAY"] = minidom.parseString(ET.tostring(root_a)).toprettyxml(indent=" ")
    files["XML_B_DISPLAY"] = minidom.parseString(ET.tostring(root_b)).toprettyxml(indent=" ")
    return files

# --- 2. ROBUST TRIAGE & CACHE EXTRACTION ---
def robust_parse(content, vendor, format_type):
    data = {"timestamp": None, "tool_id": "N/A", "vendor": vendor, "category": "SENSOR", "severity": "INFO", "value": 0.0, "metadata_payload": {}, "ai_summary": "", "rca_diagnosis": "N/A"}

    try:
        if format_type == "JSON":
            raw = content if isinstance(content, dict) else json.loads(content)
            data["timestamp"] = raw.get("time") or raw.get("timestamp")
            data["tool_id"] = raw.get("id") or raw.get("machine_code")
            data["value"] = float(raw.get("val") or raw.get("pressure_reading"))
            data["metadata_payload"] = {k: v for k, v in raw.items() if k not in ["time", "timestamp", "val", "pressure_reading", "id", "machine_code"]}
        elif format_type == "XML":
            tree = ET.fromstring(content)
            data["timestamp"] = tree.find("T").text if tree.find("T") is not None else tree.find("DateTime").text
            data["value"] = float(tree.find("P").text if tree.find("P") is not None else tree.find("Vacuum_Pa").text)
            data["tool_id"] = "MCH_A01" if vendor == "Vendor A" else "MCH_B02"
        elif format_type in ["TEXT", "SYS", "KV"]:
            ts_match = re.search(r"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?)", content)
            val_match = re.search(r"(?:VAL:|Pressure=)([\d.]+)", content)
            id_match = re.search(r"(MCH_[\w\d]+)", content)
            if ts_match: data["timestamp"] = ts_match.group(1).replace(" ", "T")
            if val_match: data["value"] = float(val_match.group(1))
            if id_match: data["tool_id"] = id_match.group(1)
            meta = {}
            if fw := re.search(r"FW[=:]([\w.]+)", content): meta["fw"] = fw.group(1)
            if ch := re.search(r"CH[=:]([\w\d]+)", content): meta["ch"] = ch.group(1)
            data["metadata_payload"] = meta
    except Exception: pass

    cache_key = f"{vendor}_{data['timestamp']}"
    if cache_key in st.session_state['ai_cache']:
        data.update(st.session_state['ai_cache'][cache_key])
        return data

    if data["value"] <= 3.5:
        data.update({"category": "SENSOR", "severity": "INFO", "ai_summary": "Nominal operation.", "rca_diagnosis": "N/A"})
    else:
        data.update({"category": "ALARM", "severity": "CRITICAL"})
        try:
            prompt = f"Analyze anomaly: {content}. Return STRICT JSON with 'ai_summary' (one technical sentence) and 'rca_diagnosis' (e.g. 'Seal degradation in C1')."
            resp = requests.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"}, timeout=8)
            ai_res = json.loads(re.sub(r'```json|```', '', resp.json().get("response", "")).strip())
            data["ai_summary"] = ai_res.get("ai_summary", "Critical vacuum fault.")
            data["rca_diagnosis"] = ai_res.get("rca_diagnosis", "Hardware failure.")
        except Exception:
            data.update({"ai_summary": "Fault detected. AI skipped.", "rca_diagnosis": "Pending LLM."})

    st.session_state['ai_cache'][cache_key] = {"category": data["category"], "severity": data["severity"], "ai_summary": data["ai_summary"], "rca_diagnosis": data["rca_diagnosis"]}
    return data

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Navigation")
    page = st.radio("Go to:", ["⚙️ Simulation Engine", "📊 Factory Dashboard"])
    st.divider()
    if st.button("🗑️ Clear Memory & Reset"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# PAGE 1: SIMULATION ENGINE (The Backend)
# ==========================================
if page == "⚙️ Simulation Engine":
    st.header("⚙️ Synthetic Log Generator")
    st.write("Generate highly realistic, format-diverse equipment logs for Vendor A and B.")
    
    c1, c2, c3 = st.columns(3)
    profile = c1.selectbox("Failure Profile", ["Normal Ops", "Slow Leak", "Sudden Burst", "Ghost Fault"])
    severity_val = c2.slider("Failure Severity", 1, 10, 5)
    log_len = c3.number_input("Log Length", 5, 200, 15)
    
    if st.button("Generate 10 Files"):
        st.session_state['files'] = generate_files(profile, severity_val, log_len)
        st.session_state['results'] = [] 
        st.session_state['ai_cache'] = {}
        st.session_state['macro_plan'] = ""
        st.session_state['chat_history'] = []
        st.success("Files Generated successfully! Proceed to the Factory Dashboard.")

    if st.session_state['files']:
        st.subheader("Raw Buffer Comparison")
        t1, t2, t3, t4, t5 = st.tabs(["JSON", "XML", "Text", "Syslog", "Key-Value"])
        with t1:
            col1, col2 = st.columns(2); col1.json(st.session_state['files']['JSON_A']); col2.json(st.session_state['files']['JSON_B'])
        with t2:
            col1, col2 = st.columns(2); col1.code(st.session_state['files']['XML_A_DISPLAY'], "xml"); col2.code(st.session_state['files']['XML_B_DISPLAY'], "xml")
        with t3:
            col1, col2 = st.columns(2); col1.text_area("Vendor A Text", "\n".join(st.session_state['files']['TEXT_A'])); col2.text_area("Vendor B Text", "\n".join(st.session_state['files']['TEXT_B']))
        with t4:
            col1, col2 = st.columns(2); col1.text_area("Vendor A Syslog", "\n".join(st.session_state['files']['SYS_A'])); col2.text_area("Vendor B Syslog", "\n".join(st.session_state['files']['SYS_B']))
        with t5:
            col1, col2 = st.columns(2); col1.text_area("Vendor A KV", "\n".join(st.session_state['files']['KV_A'])); col2.text_area("Vendor B KV", "\n".join(st.session_state['files']['KV_B']))

# ==========================================
# PAGE 2: FACTORY DASHBOARD (The Frontend)
# ==========================================
elif page == "📊 Factory Dashboard":
    st.header("📊 Intelligence & Analytics Dashboard")
    
    if not st.session_state['files']:
        st.warning("No data found. Please generate logs in the Simulation Engine first.")
    else:
        col1, col2 = st.columns([1, 3])
        batch = col1.slider("Process Batch Size", 1, len(st.session_state['files']['JSON_A']), min(10, len(st.session_state['files']['JSON_A'])))
        
        if col1.button("🚀 Begin Smart Normalization"):
            timer_container = st.empty()
            with timer_container:
                components.html(f"""
                    <div style="font-family: monospace; color: #FFD700; font-size: 20px; font-weight: bold; padding: 10px; border: 1px solid #FFD700; border-radius: 5px; background: #222;">
                        LIVE ELAPSED TIME: <span id="timer">0.0</span>s
                    </div>
                    <script>
                        var start = Date.now();
                        setInterval(function() {{ document.getElementById('timer').innerHTML = ((Date.now() - start) / 1000).toFixed(1); }}, 100);
                    </script>
                """, height=70)

            status_box = st.empty()
            prog = st.progress(0)
            results = []
            
            start_time = time.time()
            for i in range(batch):
                idx = -(i + 1)
                status_box.text(f"Processing Time Step {i+1} of {batch} across 10 distinct formats...")
                results.append(robust_parse(st.session_state['files']['JSON_A'][idx], "Vendor A", "JSON"))
                results.append(robust_parse(st.session_state['files']['JSON_B'][idx], "Vendor B", "JSON"))
                results.append(robust_parse(st.session_state['files']['XML_A_RAW'][idx], "Vendor A", "XML"))
                results.append(robust_parse(st.session_state['files']['XML_B_RAW'][idx], "Vendor B", "XML"))
                results.append(robust_parse(st.session_state['files']['TEXT_A'][idx], "Vendor A", "TEXT"))
                results.append(robust_parse(st.session_state['files']['TEXT_B'][idx], "Vendor B", "TEXT"))
                results.append(robust_parse(st.session_state['files']['SYS_A'][idx], "Vendor A", "SYS"))
                results.append(robust_parse(st.session_state['files']['SYS_B'][idx], "Vendor B", "SYS"))
                results.append(robust_parse(st.session_state['files']['KV_A'][idx], "Vendor A", "KV"))
                results.append(robust_parse(st.session_state['files']['KV_B'][idx], "Vendor B", "KV"))
                prog.progress((i + 1) / batch)

            timer_container.success(f"✅ Normalization complete in **{time.time() - start_time:.2f}s**")
            status_box.empty()
            st.session_state['results'] = results
            st.session_state['macro_plan'] = "" 
            st.session_state['chat_history'] = []

        if st.session_state['results']:
            df = pd.DataFrame(st.session_state['results'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce', utc=True)
            df = df.sort_values('timestamp', ascending=True)
            df['value'] = pd.to_numeric(df['value'], errors='coerce')

            df['baseline'] = df.groupby('vendor')['value'].transform(lambda x: x.rolling(window=3, min_periods=1).mean().shift(1).fillna(0.9))
            drift_condition = (abs(df['value'] - df['baseline']) / df['baseline'] > 0.15) & (df['value'] <= 3.5)
            df['drift_warning'] = drift_condition.map({True: "⚠️ Drift", False: "Normal"})
            df['yield_scrap_est'] = df.apply(lambda row: round((row['value'] - 3.5) * 12.5, 1) if row['category'] == 'ALARM' else 0, axis=1)

            # --- PLOTLY DYNAMIC CHART ---
            st.subheader("📈 Dynamic Drift & Anomaly Matrix")
            fig = go.Figure()
            for vendor in ['Vendor A', 'Vendor B']:
                v_df = df[df['vendor'] == vendor]
                fig.add_trace(go.Scatter(x=v_df['timestamp'], y=v_df['value'], mode='lines', name=vendor))
                anomalies = v_df[v_df['value'] > 3.5]
                if not anomalies.empty:
                    fig.add_trace(go.Scatter(x=anomalies['timestamp'], y=anomalies['value'], mode='markers', 
                                             marker=dict(color='#FFA500', size=12, line=dict(color='red', width=2)), 
                                             name=f"{vendor} Anomaly Event"))

            fig.add_hline(y=3.5, line_dash="dash", line_color="red", annotation_text="Critical Action Threshold (3.5 Pa)")
            fig.update_layout(template="plotly_dark", xaxis_title="Timestamp", yaxis_title="Vacuum Pressure (Pa)", height=500)
            st.plotly_chart(fig, use_container_width=True)

            # --- MACRO ACTION PLAN ---
            alarms_df = df[df['category'] == 'ALARM'].drop_duplicates(subset=['rca_diagnosis'])
            if not alarms_df.empty:
                st.divider()
                st.subheader("🚨 Executive Macro Mitigation Plan")
                if st.button("Generate Mitigation Strategy from RCAs"):
                    with st.spinner("Aggregating faults and consulting AI Chief Engineer..."):
                        faults = " | ".join(alarms_df['rca_diagnosis'].astype(str).tolist())
                        prompt = f"You are a fab manager. Based on these concurrent vacuum tool faults: [{faults}], generate a concise, 3-step physical mitigation plan for the floor technicians. Do not use markdown."
                        try:
                            resp = requests.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=15)
                            st.session_state['macro_plan'] = resp.json().get("response", "Error generating plan.")
                        except Exception:
                            st.session_state['macro_plan'] = "Macro Plan generation timed out. Local LLM may be busy."
                if st.session_state['macro_plan']: st.info(st.session_state['macro_plan'])

            # --- PERFORMANCE DASHBOARD ---
            st.divider()
            m1, m2, m3 = st.columns(3)
            alarms = len(df[df['category'] == 'ALARM'])
            availability = ((len(df) - alarms) / len(df)) * 100 if len(df) > 0 else 100
            m1.metric("Tool Availability", f"{availability:.1f}%")
            m2.metric("Predictive Drift Warnings", len(df[df['drift_warning'] == "⚠️ Drift"]))
            m3.metric("Estimated Yield Loss", f"{df['yield_scrap_est'].sum():.1f} Units", delta="-High Impact" if df['yield_scrap_est'].sum() > 50 else None, delta_color="inverse")

            # --- UNIFIED TABLE & EXPORT ---
            st.subheader("Unified Intelligence Table")
            cols = ['timestamp', 'tool_id', 'vendor', 'category', 'severity', 'value', 'drift_warning', 'rca_diagnosis', 'yield_scrap_est']
            df_display = df.reindex(columns=cols).fillna("N/A")
            c_table, c_btn = st.columns([8, 1])
            c_table.dataframe(df_display, use_container_width=True)
            csv = df_display.to_csv(index=False).encode('utf-8')
            c_btn.download_button("📥 Export CSV", data=csv, file_name="normalized_fab_logs.csv", mime="text/csv")

            # --- FACTORY AI COPILOT (STRICT RAG UPGRADE) ---
            st.divider()
            st.subheader("🤖 Factory AI Copilot")
            st.caption("Ask questions about the normalized factory data, tool performance, and root causes.")

            for msg in st.session_state['chat_history']:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if user_q := st.chat_input("E.g., At what time did Vendor A's machine start to fail?"):
                st.session_state['chat_history'].append({"role": "user", "content": user_q})
                with st.chat_message("user"): st.markdown(user_q)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing pre-processed factory context..."):
                        
                        context_blocks = []
                        alarm_rows = df_display[df_display['category'] == 'ALARM']
                        if alarm_rows.empty:
                            context_blocks.append("No critical alarms detected in this batch.")
                        else:
                            unique_alarms = alarm_rows.drop_duplicates(subset=['timestamp', 'vendor'])
                            for _, row in unique_alarms.iterrows():
                                context_blocks.append(f"At exact time {row['timestamp']}, {row['vendor']} (Tool: {row['tool_id']}) triggered an ALARM with pressure spiking to {row['value']} Pa. Root cause: {row['rca_diagnosis']}.")
                        
                        info_rows = df_display[df_display['category'] == 'INFO']
                        if not info_rows.empty:
                            context_blocks.append(f"There were {len(info_rows)} normal operational events recorded between {info_rows['timestamp'].min()} and {info_rows['timestamp'].max()}.")

                        # XML Demarcation for the LLM
                        clean_context = "<FACTORY_DATA>\n" + "\n".join(context_blocks) + "\n</FACTORY_DATA>"
                        
                        # The Penalty Prompt
                        copilot_prompt = f"""You are Team Noctilucent's strict Factory Diagnostic AI. 
You MUST answer the user's question using ONLY the verified data enclosed in the <FACTORY_DATA> tags below.
If the answer is not explicitly stated in the tags, reply "I cannot find this information in the current log batch."
Under NO circumstances should you invent dates, times, vendors, or diagnoses.

{clean_context}

User Question: {user_q}
Be direct, factual, and concise."""
                        
                        try:
                            # THE FIX: Zero Temperature Payload
                            resp = requests.post(OLLAMA_URL, json={
                                "model": MODEL_NAME, 
                                "prompt": copilot_prompt, 
                                "stream": False,
                                "options": {"temperature": 0.0}
                            }, timeout=15)
                            
                            answer = resp.json().get("response", "Error connecting to local LLM.")
                            st.markdown(answer)
                            st.session_state['chat_history'].append({"role": "assistant", "content": answer})
                        except Exception:
                            err_msg = "Copilot request timed out. Make sure the local LLM is running."
                            st.error(err_msg)
                            st.session_state['chat_history'].append({"role": "assistant", "content": err_msg})