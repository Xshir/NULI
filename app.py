import streamlit as st
import pandas as pd
import random
import json
import datetime
import requests
import time
import re
import os
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components
import plotly.graph_objects as go
import Configuration as cfg

# ==========================================
# PAGE SETUP & UI STYLING
# ==========================================
st.set_page_config(page_title=cfg.PAGE_TITLE, layout=cfg.PAGE_LAYOUT)

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap');

    .stApp {{
        background: linear-gradient(135deg, {cfg.COLOR_BG_PRIMARY} 0%, {cfg.COLOR_BG_SECONDARY} 100%);
        font-family: {cfg.FONT_MAIN} !important;
        color: {cfg.COLOR_TEXT_MAIN} !important;
    }}
    
    h1, h2, h3, h4, h5, h6, [data-testid="stHeader"] {{
        color: {cfg.COLOR_ACCENT_PLATINUM} !important;
        font-weight: 600 !important;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }}

    [data-testid="stWidgetLabel"] p, .st-emotion-cache-16idsys p, label {{
        color: {cfg.COLOR_ACCENT_PLATINUM} !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.5px;
    }}

    code, .stMetric, [data-testid="stMetricValue"], #timer {{
        font-family: {cfg.FONT_MONO} !important;
        color: {cfg.COLOR_ACCENT_CYAN} !important;
    }}

    .stSlider > div [data-baseweb="slider"] [role="slider"] {{ background-color: {cfg.COLOR_ACCENT_PLATINUM} !important; border: 2px solid {cfg.COLOR_BG_PRIMARY} !important; }}
    .stSlider > div [data-baseweb="slider"] > div > div {{ background: {cfg.COLOR_ACCENT_PLATINUM} !important; }}
    
    .stProgress > div > div > div > div {{ background-color: {cfg.COLOR_ACCENT_CYAN} !important; }}

    .stButton > button {{
        background-color: transparent !important;
        border: 1px solid {cfg.COLOR_ACCENT_CYAN} !important;
        color: {cfg.COLOR_ACCENT_CYAN} !important;
        border-radius: 2px;
        transition: all 0.3s ease;
        font-family: {cfg.FONT_MAIN} !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    .stButton > button:hover {{
        background-color: {cfg.COLOR_ACCENT_CYAN} !important;
        color: {cfg.COLOR_BG_PRIMARY} !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: {cfg.COLOR_BG_PRIMARY} !important;
        border-right: 1px solid #003366;
    }}

    [data-testid="stDataFrame"] {{
        font-family: {cfg.FONT_MONO} !important;
    }}

    /* CSS FIX FOR MITIGATION STRATEGY ALERTS */
    [data-testid="stAlert"] {{
        background-color: rgba(0, 229, 255, 0.05) !important;
        border: 1px solid {cfg.COLOR_ACCENT_CYAN} !important;
        color: {cfg.COLOR_ACCENT_PLATINUM} !important;
    }}
    [data-testid="stAlert"] p {{
        color: {cfg.COLOR_ACCENT_PLATINUM} !important;
        font-family: {cfg.FONT_MAIN} !important;
        font-size: 1rem !important;
    }}
    [data-testid="stAlert"] svg {{
        fill: {cfg.COLOR_ACCENT_CYAN} !important;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# STATE MANAGEMENT & NAVIGATION ROUTING
# ==========================================
if 'files' not in st.session_state: st.session_state['files'] = None
if 'results' not in st.session_state: st.session_state['results'] = []
if 'ai_cache' not in st.session_state: st.session_state['ai_cache'] = {}
if 'macro_plan' not in st.session_state: st.session_state['macro_plan'] = ""
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []
if 'nav_radio' not in st.session_state: st.session_state['nav_radio'] = cfg.TITLE_COVER
if 'active_threshold' not in st.session_state: st.session_state['active_threshold'] = cfg.THRESHOLD_CRITICAL

# --- NAVIGATION ROUTING INTERCEPTOR ---
if st.session_state.get('force_nav_dashboard', False):
    st.session_state['nav_radio'] = cfg.TITLE_DASHBOARD
    st.session_state['force_nav_dashboard'] = False

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("SYSTEM NAVIGATION")
    page = st.radio("MODULE SELECT:", [cfg.TITLE_COVER, cfg.TITLE_SIMULATION, cfg.TITLE_DASHBOARD], key="nav_radio")
    st.divider()
    if st.button("CLEAR MEMORY & RESET"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# HELPER FUNCTIONS & ENGINE LOGIC
# ==========================================

def safe_image(path, width=None):
    if os.path.exists(path):
        if width is not None:
            st.image(path, width=width)
        else:
            # FIX: Using the legacy command for cross-version Docker compatibility
            st.image(path, use_column_width=True)
    else:
        st.info(f"Missing Image: Save your logo as '{path}' in the same folder.")

def generate_files(profile, severity, length=10):
    timestamp = datetime.datetime.now()
    files = {"JSON_A": [], "JSON_B": [], "XML_A_RAW": [], "XML_B_RAW": [], "TEXT_A": [], "TEXT_B": [], "SYS_A": [], "SYS_B": [], "KV_A": [], "KV_B": [], "CSV_A": [], "CSV_B": []}
    root_a = ET.Element("ToolLog", {"Vendor": "Vendor_A"})
    root_b = ET.Element("SensorExport", {"Vendor": "Vendor_B"})

    pressure_a, pressure_b = cfg.BASELINE_DEFAULT, cfg.BASELINE_DEFAULT
    
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
            pressure_a = cfg.BASELINE_DEFAULT + (random.choice([0, 2.0, 0.5, 3.1]) * (severity / 5))
            pressure_b = cfg.BASELINE_DEFAULT + (random.choice([0, 0, 1.0, 3.5]) * (severity / 5))
        else: 
            pressure_a += random.uniform(-0.02, 0.02)
            pressure_b += random.uniform(-0.02, 0.02)

        p_val_a, p_val_b = round(pressure_a, 3), round(pressure_b, 3)
        status_a = "ALARM: VACUUM_FAULT" if p_val_a > cfg.THRESHOLD_CRITICAL else "STATUS_OK"
        status_b = "ALARM: VACUUM_FAULT" if p_val_b > cfg.THRESHOLD_CRITICAL else "STATUS_OK"

        files["JSON_A"].append({"id": "MCH_A01", "time": ts_iso, "val": p_val_a, "fw": "v2.1"})
        files["TEXT_A"].append(f"[{ts_text}] ID:MCH_A01 VENDOR:Vendor_A VAL:{p_val_a}Pa FW:v2.1 {status_a}")
        files["SYS_A"].append(f"<14> {ts_iso} MCH_A01 VENDOR_A - - VAL:{p_val_a}Pa FW:v2.1 {status_a}")
        files["KV_A"].append(f"timestamp={ts_iso} ID=MCH_A01 vendor=Vendor_A Pressure={p_val_a} FW=v2.1 status={status_a}")
        files["XML_A_RAW"].append(f"<Entry><T>{ts_iso}</T><P>{p_val_a}</P></Entry>")
        files["CSV_A"].append(f"{ts_iso},MCH_A01,Vendor_A,{p_val_a},v2.1,{status_a}")
        ea = ET.SubElement(root_a, "Entry"); ET.SubElement(ea, "T").text = ts_iso; ET.SubElement(ea, "P").text = str(p_val_a)

        files["JSON_B"].append({"machine_code": "MCH_B02", "timestamp": ts_iso, "pressure_reading": p_val_b, "ch": "C1"})
        files["TEXT_B"].append(f"{ts_text} | MCH_B02 | Vendor_B | Pressure={p_val_b} | CH=C1 | {status_b}")
        files["SYS_B"].append(f"<14> {ts_iso} MCH_B02 VENDOR_B - - Pressure={p_val_b}Pa CH=C1 {status_b}")
        files["KV_B"].append(f"timestamp={ts_iso} ID=MCH_B02 vendor=Vendor_B Pressure={p_val_b} CH=C1 status={status_b}")
        files["XML_B_RAW"].append(f"<Reading><DateTime>{ts_iso}</DateTime><Vacuum_Pa>{p_val_b}</Vacuum_Pa></Reading>")
        files["CSV_B"].append(f"{ts_iso},MCH_B02,Vendor_B,{p_val_b},C1,{status_b}")
        eb = ET.SubElement(root_b, "Reading"); ET.SubElement(eb, "DateTime").text = ts_iso; ET.SubElement(eb, "Vacuum_Pa").text = str(p_val_b)

    files["XML_A_DISPLAY"] = minidom.parseString(ET.tostring(root_a)).toprettyxml(indent=" ")
    files["XML_B_DISPLAY"] = minidom.parseString(ET.tostring(root_b)).toprettyxml(indent=" ")
    return files

def robust_parse(content, vendor, format_type):
    data = {"timestamp": None, "tool_id": "N/A", "vendor": vendor, "category": "SENSOR", "severity": "INFO", "value": 0.0, "metadata_payload": {}, "ai_summary": "", "rca_diagnosis": "N/A"}

    try:
        if format_type == "JSON":
            raw = content if isinstance(content, dict) else json.loads(content)
            data["timestamp"] = raw.get("time") or raw.get("timestamp")
            data["tool_id"] = raw.get("id") or raw.get("machine_code")
            data["value"] = float(raw.get("val") or raw.get("pressure_reading"))
        elif format_type == "XML":
            tree = ET.fromstring(content)
            data["timestamp"] = tree.find("T").text if tree.find("T") is not None else tree.find("DateTime").text
            data["value"] = float(tree.find("P").text if tree.find("P") is not None else tree.find("Vacuum_Pa").text)
            data["tool_id"] = "MCH_A01" if vendor == "Vendor A" else "MCH_B02"
        elif format_type == "CSV":
            parts = content.split(",")
            data["timestamp"] = parts[0]
            data["tool_id"] = parts[1]
            data["value"] = float(parts[3])
        elif format_type in ["TEXT", "SYS", "KV"]:
            ts_match = re.search(r"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?)", content)
            val_match = re.search(r"(?:VAL:|Pressure=)([\d.]+)", content)
            id_match = re.search(r"(MCH_[\w\d]+)", content)
            if ts_match: data["timestamp"] = ts_match.group(1).replace(" ", "T")
            if val_match: data["value"] = float(val_match.group(1))
            if id_match: data["tool_id"] = id_match.group(1)
    except Exception: pass

    cache_key = f"{vendor}_{data['timestamp']}"
    if cache_key in st.session_state['ai_cache']:
        data.update(st.session_state['ai_cache'][cache_key])
        return data

    if data["value"] <= cfg.THRESHOLD_CRITICAL:
        data.update({"category": "SENSOR", "severity": "INFO", "ai_summary": "Nominal operation.", "rca_diagnosis": "N/A"})
    else:
        data.update({"category": "ALARM", "severity": "CRITICAL"})
        try:
            prompt = f"Analyze anomaly: {content}. Return STRICT JSON with 'ai_summary' (one technical sentence) and 'rca_diagnosis' (e.g. 'Seal degradation in C1')."
            resp = requests.post(cfg.OLLAMA_URL, json={"model": cfg.MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"}, timeout=8)
            ai_res = json.loads(re.sub(r'```json|```', '', resp.json().get("response", "")).strip())
            data["ai_summary"] = ai_res.get("ai_summary", "Critical vacuum fault.")
            data["rca_diagnosis"] = ai_res.get("rca_diagnosis", "Hardware failure.")
        except Exception:
            data.update({"ai_summary": "Fault detected. AI skipped.", "rca_diagnosis": "Pending LLM."})

    st.session_state['ai_cache'][cache_key] = {"category": data["category"], "severity": data["severity"], "ai_summary": data["ai_summary"], "rca_diagnosis": data["rca_diagnosis"]}
    return data


# ==========================================
# PAGE 0: SYSTEM INITIALIZATION (Cover Page)
# ==========================================
if page == cfg.TITLE_COVER:
    st.write("<br><br>", unsafe_allow_html=True)
    
    c_pad1, c_main, c_pad2 = st.columns([1, 1.5, 1])
    
    with c_main:
        st.markdown(f"<p style='text-align: center; color: {cfg.COLOR_ACCENT_PLATINUM}; margin-bottom: 0px; font-size: 0.8rem;'>TRACK:</p>", unsafe_allow_html=True)
        
        m_pad1, m_logo, m_pad2 = st.columns([1, 3, 1])
        with m_logo:
            safe_image("micron_logo.png")
        
        st.markdown(f"<p style='text-align: center; color: {cfg.COLOR_ACCENT_CYAN}; font-size: 1.1rem; margin-top: 10px; font-weight: bold;'>NATIONAL STUDENT AI CHALLENGE 2026</p>", unsafe_allow_html=True)
        
        st.write("<br>", unsafe_allow_html=True)
        
        sub_pad1, sub_tp, sub_ael, sub_pad2 = st.columns([0.5, 1.5, 0.9, 0.5])
        with sub_tp:
            safe_image("tp_logo.png")
        with sub_ael:
            safe_image("ael_logo.png")
            
        st.write("<br><br>", unsafe_allow_html=True)
        
        # --- UPDATED TEAM CREDITS ---
        st.markdown(f"<p style='text-align: center; color: {cfg.COLOR_TEXT_MAIN}; font-family: {cfg.FONT_MONO}; font-size: 0.8rem; margin-bottom: 0px; letter-spacing: 2px;'>LEAD DEVELOPER</p>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; color: {cfg.COLOR_ACCENT_PLATINUM}; letter-spacing: 2px; font-size: 1.3rem; font-weight: 600; margin-top: 2px; margin-bottom: 15px;'>MUHAMMAD HAASHIR ISLAM</div>", unsafe_allow_html=True)
        
        st.markdown(f"<p style='text-align: center; color: {cfg.COLOR_TEXT_MAIN}; font-family: {cfg.FONT_MONO}; font-size: 0.8rem; margin-bottom: 0px; letter-spacing: 2px;'>PROJECT MEMBERS</p>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; color: {cfg.COLOR_ACCENT_PLATINUM}; font-size: 1rem; font-weight: 400; margin-top: 2px; letter-spacing: 1px;'>CHARLENE TAN YING JIE<br>GABRIEL LIM JUN HONG</div>", unsafe_allow_html=True)

# ==========================================
# PAGE 1: DATA INGESTION ENGINE
# ==========================================
elif page == cfg.TITLE_SIMULATION:
    st.header("01 - DATA INGESTION ENGINE")
    
    tab_synth, tab_ext = st.tabs(["SYNTHETIC GENERATION", "EXTERNAL ZERO-SHOT UPLOAD"])
    
    # --- TAB 1: SYNTHETIC ---
    with tab_synth:
        st.write("Generate high-fidelity, format-diverse equipment logs for target vendors.")
        
        c1, c2, c3 = st.columns(3)
        profile = c1.selectbox("FAILURE PROFILE", ["Normal Ops", "Slow Leak", "Sudden Burst", "Ghost Fault"])
        severity_val = c2.slider("FAILURE SEVERITY", cfg.SEVERITY_MIN, cfg.SEVERITY_MAX, cfg.SEVERITY_DEFAULT)
        log_len = c3.slider("LOG LENGTH (CYCLES)", cfg.LOG_LENGTH_MIN, cfg.LOG_LENGTH_MAX, cfg.LOG_LENGTH_DEFAULT)
        
        if st.button("GENERATE SYNTHETIC PAYLOAD"):
            with st.spinner("Compiling multi-format factory logs..."):
                st.session_state['files'] = generate_files(profile, severity_val, log_len)
                st.session_state['results'] = [] 
                st.session_state['ai_cache'] = {}
                st.session_state['macro_plan'] = ""
                st.session_state['chat_history'] = []
                st.session_state['active_threshold'] = cfg.THRESHOLD_CRITICAL # Reset to baseline
        
        # Display the full logs ONLY if files have been generated
        if st.session_state.get('files'):
            st.success("SYNTHETIC DATA STREAMS GENERATED SUCCESSFULLY")
            
            with st.expander("VIEW FULL SYNTHETIC PAYLOAD (ALL 12 FORMATS)", expanded=True):
                # Create 12 tabs for all generated streams
                tabs = st.tabs([
                    "JSON (A)", "JSON (B)", 
                    "XML (A)", "XML (B)", 
                    "CSV (A)", "CSV (B)", 
                    "TEXT (A)", "TEXT (B)", 
                    "SYSLOG (A)", "SYSLOG (B)", 
                    "KV (A)", "KV (B)"
                ])
                
                with tabs[0]: st.code(json.dumps(st.session_state['files']['JSON_A'], indent=2), language="json")
                with tabs[1]: st.code(json.dumps(st.session_state['files']['JSON_B'], indent=2), language="json")
                
                with tabs[2]: st.code(st.session_state['files']['XML_A_DISPLAY'], language="xml")
                with tabs[3]: st.code(st.session_state['files']['XML_B_DISPLAY'], language="xml")
                
                with tabs[4]: st.code("timestamp,id,vendor,val,fw,status\n" + "\n".join(st.session_state['files']['CSV_A']), language="csv")
                with tabs[5]: st.code("timestamp,machine_code,vendor,pressure_reading,ch,status\n" + "\n".join(st.session_state['files']['CSV_B']), language="csv")
                
                with tabs[6]: st.code("\n".join(st.session_state['files']['TEXT_A']), language="text")
                with tabs[7]: st.code("\n".join(st.session_state['files']['TEXT_B']), language="text")
                
                with tabs[8]: st.code("\n".join(st.session_state['files']['SYS_A']), language="text")
                with tabs[9]: st.code("\n".join(st.session_state['files']['SYS_B']), language="text")
                
                with tabs[10]: st.code("\n".join(st.session_state['files']['KV_A']), language="text")
                with tabs[11]: st.code("\n".join(st.session_state['files']['KV_B']), language="text")

            if st.button("PUSH TO FACTORY DASHBOARD"):
                st.session_state['force_nav_dashboard'] = True
                st.rerun()

    # --- TAB 2: ZERO SHOT UPLOAD ---
    with tab_ext:
        st.write("Upload undocumented fab CSV logs. The AI will autonomously deduce the schema and map the columns.")
        uploaded_file = st.file_uploader("DROP MYSTERY LOG FILE (CSV) HERE", type=["csv"])
        
        if uploaded_file is not None:
            import io
            raw_bytes = uploaded_file.getvalue()
            
            try:
                df_ext = pd.read_csv(io.BytesIO(raw_bytes))
                headers = list(df_ext.columns)
                sample_row = df_ext.iloc[0].astype(str).to_dict()
                
                st.markdown("**RAW SCHEMA DETECTED:**")
                st.code(f"Headers: {headers}\nSample Row Data: {sample_row}", language="json")
                
                if st.button("INITIATE AUTONOMOUS SCHEMA MAPPING"):
                    with st.spinner("AI deducing structural layout..."):
                        
                        mapping_prompt = f"""You are a strict data mapper. You must select the exact header names from the list below.
Available Headers: {headers}
Sample Data: {sample_row}

Find the headers that best match these 3 categories:
1. 'timestamp_col': The date/time column.
2. 'eqp_col': The unique ID column (Prioritize 'Process_ID', 'Equipment_ID', or 'Wafer_ID').
3. 'value_col': The primary metric (MUST be 'Vacuum_Pressure' if it exists, otherwise the main numerical value).

Return ONLY a valid JSON object with exactly these 3 keys. Values must be exact strings from the Available Headers."""
                        
                        try:
                            zs_resp = requests.post(cfg.OLLAMA_URL, json={"model": cfg.MODEL_NAME, "prompt": mapping_prompt, "stream": False, "format": "json"}, timeout=15)
                            ai_map = json.loads(re.sub(r'```json|```', '', zs_resp.json().get("response", "")).strip())
                            
                            t_col = ai_map.get("timestamp_col", "UNKNOWN")
                            e_col = ai_map.get("eqp_col", "UNKNOWN")
                            v_col = ai_map.get("value_col", ai_map.get("vacuum_pressure_col", "UNKNOWN"))

                            # --- TIMESTAMP VERIFIER & FALLBACK ---
                            def is_valid_time(col):
                                if col not in headers: return False
                                try:
                                    pd.to_datetime(sample_row.get(col))
                                    return True
                                except:
                                    return False

                            if not is_valid_time(t_col):
                                t_col = next((h for h in headers if "time" in h.lower() or "date" in h.lower()), headers[0])
                            
                            if e_col not in headers:
                                e_col = next((h for h in headers if "id" in h.lower() or "tool" in h.lower()), "UNKNOWN_TOOL")
                            if v_col not in headers:
                                v_col = next((h for h in headers if "pressure" in h.lower() or "val" in h.lower()), headers[-1])
                            
                            st.success(f"SCHEMA SUCCESSFULLY MAPPED: {{'timestamp_col': '{t_col}', 'eqp_col': '{e_col}', 'value_col': '{v_col}'}}")

                            # --- ADAPTIVE Z-SCORE THRESHOLDING (3-Sigma) ---
                            try:
                                v_series = pd.to_numeric(df_ext[v_col], errors='coerce').dropna()
                                if not v_series.empty:
                                    v_mean = v_series.mean()
                                    v_std = v_series.std()
                                    # If standard deviation is 0, just add 20% to the mean to establish a safe threshold
                                    active_thresh = round(v_mean + (3 * v_std), 3) if v_std > 0 else round(v_mean * 1.2, 3)
                                else:
                                    active_thresh = cfg.THRESHOLD_CRITICAL
                            except Exception:
                                active_thresh = cfg.THRESHOLD_CRITICAL
                            
                            st.session_state['active_threshold'] = active_thresh
                            # -----------------------------------------------

                            extracted_results = []
                            for _, row in df_ext.iterrows():
                                ts_val = str(row[t_col]) if t_col in df_ext.columns else datetime.datetime.now().isoformat()
                                eqp_val = str(row[e_col]) if e_col in df_ext.columns else "UNKNOWN_TOOL"
                                
                                try:
                                    val_val = float(row[v_col]) if v_col in df_ext.columns else 0.9
                                except ValueError:
                                    val_val = 0.9

                                is_critical = val_val > active_thresh
                                cat_val = "ALARM" if is_critical else "SENSOR"
                                sev_val = "CRITICAL" if is_critical else "INFO"
                                rca_val = f"Statistical Anomaly: Exceeds 3-Sigma threshold ({active_thresh})." if is_critical else "N/A"

                                extracted_results.append({
                                    "timestamp": ts_val,
                                    "tool_id": eqp_val,
                                    "vendor": "External_Vendor",
                                    "category": cat_val,
                                    "severity": sev_val,
                                    "value": val_val,
                                    "Confidence_Score": "100%",
                                    "rca_diagnosis": rca_val
                                })
                            
                            st.session_state['results'] = extracted_results
                            st.session_state['files'] = None 
                            st.session_state['macro_plan'] = ""
                            st.session_state['chat_history'] = []
                            
                            st.session_state['force_nav_dashboard'] = True
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Schema mapping failure. Ensure LLM is running. Error: {e}")
            except Exception as e:
                st.error(f"Could not read CSV file. {e}")


# ==========================================
# PAGE 2: FACTORY DASHBOARD (The Frontend)
# ==========================================
elif page == cfg.TITLE_DASHBOARD:
    st.header(cfg.TITLE_DASHBOARD)
    
    # Retrieve the dynamic threshold calculated during ingestion
    active_thresh = st.session_state.get('active_threshold', cfg.THRESHOLD_CRITICAL)
    
    has_raw_files = st.session_state.get('files') is not None
    has_processed_results = len(st.session_state.get('results', [])) > 0
    
    if not has_raw_files and not has_processed_results:
        st.warning("Awaiting data stream. Initiate generation sequence in the Simulation Engine.")
    else:
        if has_raw_files:
            col1, col2 = st.columns([1, 3])
            batch = col1.slider("INGESTION BATCH SIZE", 1, len(st.session_state['files']['JSON_A']), min(cfg.BATCH_SIZE_MAX_DISPLAY, len(st.session_state['files']['JSON_A'])))
            
            if col1.button("INITIATE DATA NORMALIZATION"):
                timer_container = st.empty()
                
                llm_trigger_count = 0
                for i in range(batch):
                    idx = -(i + 1)
                    if st.session_state['files']['JSON_A'][idx]['val'] > active_thresh:
                        llm_trigger_count += 1
                    if st.session_state['files']['JSON_B'][idx]['pressure_reading'] > active_thresh:
                        llm_trigger_count += 1
                
                true_calculated_time = (batch * 0.1) + (llm_trigger_count * 3.0)
                est_time = int(true_calculated_time) + 20
                
                with timer_container:
                    components.html(f"""
                        <div style="font-family: {cfg.FONT_MONO}; padding: 15px; border: 1px solid {cfg.COLOR_ACCENT_CYAN}; border-radius: 5px; background: {cfg.COLOR_BG_PRIMARY}; display: flex; flex-direction: column; gap: 10px;">
                            <div style="display: flex; justify-content: space-between; font-size: 18px; font-weight: bold;">
                                <span style="color: {cfg.COLOR_ACCENT_CYAN};">ELAPSED TIME: <span id="timer">0.0</span>s</span>
                                <span style="color: {cfg.COLOR_ACCENT_PLATINUM};">ESTIMATED TIME: {est_time}.0s</span>
                            </div>
                            <div style="font-family: {cfg.FONT_MAIN}; font-size: 14px; color: {cfg.COLOR_TEXT_MAIN}; background: rgba(0, 229, 255, 0.05); padding: 10px; border-radius: 4px; border-left: 3px solid {cfg.COLOR_ACCENT_CYAN};">
                                <strong style="color: {cfg.COLOR_ACCENT_CYAN}; letter-spacing: 1px;">FAB FACT: </strong> 
                                <span id="fact-display" style="font-style: italic;">Initializing databanks...</span>
                            </div>
                        </div>
                        <script>
                            var start = Date.now();
                            setInterval(function() {{ 
                                document.getElementById('timer').innerHTML = ((Date.now() - start) / 1000).toFixed(1); 
                            }}, 100);

                            var facts = {json.dumps(cfg.SEMICONDUCTOR_FACTS)};
                            var factEl = document.getElementById('fact-display');
                            
                            factEl.innerHTML = facts[Math.floor(Math.random() * facts.length)];
                            
                            setInterval(function() {{
                                factEl.style.opacity = 0; 
                                setTimeout(function() {{
                                    factEl.innerHTML = facts[Math.floor(Math.random() * facts.length)];
                                    factEl.style.opacity = 1;
                                }}, 200);
                            }}, 5000); 
                        </script>
                    """, height=110)

                status_box = st.empty()
                prog = st.progress(0)
                results = []
                
                start_time = time.time()
                for i in range(batch):
                    idx = -(i + 1)
                    status_box.text(f"Fusing Data Vectors: Array Index {i+1} / {batch} ...")
                    
                    formats_a = [
                        robust_parse(st.session_state['files']['JSON_A'][idx], "Vendor A", "JSON"),
                        robust_parse(st.session_state['files']['XML_A_RAW'][idx], "Vendor A", "XML"),
                        robust_parse(st.session_state['files']['TEXT_A'][idx], "Vendor A", "TEXT"),
                        robust_parse(st.session_state['files']['SYS_A'][idx], "Vendor A", "SYS"),
                        robust_parse(st.session_state['files']['KV_A'][idx], "Vendor A", "KV"),
                        robust_parse(st.session_state['files']['CSV_A'][idx], "Vendor A", "CSV")
                    ]
                    
                    vals_a = [res["value"] for res in formats_a if res["value"] is not None]
                    if vals_a:
                        mode_val_a = max(set(vals_a), key=vals_a.count)
                        conf_score_a = int((vals_a.count(mode_val_a) / len(formats_a)) * 100)
                        base_a = formats_a[0]
                        base_a["value"] = mode_val_a
                        base_a["Confidence_Score"] = f"{conf_score_a}%"
                        results.append(base_a)

                    formats_b = [
                        robust_parse(st.session_state['files']['JSON_B'][idx], "Vendor B", "JSON"),
                        robust_parse(st.session_state['files']['XML_B_RAW'][idx], "Vendor B", "XML"),
                        robust_parse(st.session_state['files']['TEXT_B'][idx], "Vendor B", "TEXT"),
                        robust_parse(st.session_state['files']['SYS_B'][idx], "Vendor B", "SYS"),
                        robust_parse(st.session_state['files']['KV_B'][idx], "Vendor B", "KV"),
                        robust_parse(st.session_state['files']['CSV_B'][idx], "Vendor B", "CSV")
                    ]
                    
                    vals_b = [res["value"] for res in formats_b if res["value"] is not None]
                    if vals_b:
                        mode_val_b = max(set(vals_b), key=vals_b.count)
                        conf_score_b = int((vals_b.count(mode_val_b) / len(formats_b)) * 100)
                        base_b = formats_b[0]
                        base_b["value"] = mode_val_b
                        base_b["Confidence_Score"] = f"{conf_score_b}%"
                        results.append(base_b)
                    
                    prog.progress((i + 1) / batch)

                timer_container.success(f"NORMALIZATION & FUSION COMPLETE [{time.time() - start_time:.2f}s]")
                status_box.empty()
                st.session_state['results'] = results
                st.session_state['macro_plan'] = "" 
                st.session_state['chat_history'] = []

        if has_processed_results or (has_raw_files and st.session_state['results']):
            df = pd.DataFrame(st.session_state['results'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce', utc=True)
            
            # --- GRAPH RESILIENCE: Drop unparseable dates to prevent graph from breaking ---
            df = df.dropna(subset=['timestamp']).sort_values('timestamp', ascending=True)
            df['value'] = pd.to_numeric(df['value'], errors='coerce')

            df['baseline'] = df.groupby('vendor')['value'].transform(lambda x: x.rolling(window=3, min_periods=1).mean().shift(1).fillna(cfg.BASELINE_DEFAULT))
            drift_condition = (abs(df['value'] - df['baseline']) / df['baseline'] > cfg.DRIFT_TOLERANCE) & (df['value'] <= active_thresh)
            df['drift_warning'] = drift_condition.map({True: "Drift Detected", False: "Nominal"})
            
            # Use dynamic active_thresh for yield calculation
            df['yield_scrap_est'] = df.apply(lambda row: round((row['value'] - active_thresh) * cfg.YIELD_SCRAP_COEF, 1) if row['category'] == 'ALARM' else 0, axis=1)

            st.subheader("DYNAMIC DRIFT & ANOMALY MATRIX")
            fig = go.Figure()
            
            unique_vendors = df['vendor'].unique()
            for vendor in unique_vendors:
                v_df = df[df['vendor'] == vendor]
                line_color = cfg.COLOR_ACCENT_CYAN if vendor == 'Vendor A' else (cfg.COLOR_TEXT_MAIN if vendor == 'Vendor B' else '#FFD700')
                
                fig.add_trace(go.Scatter(x=v_df['timestamp'], y=v_df['value'], mode='lines', name=vendor, line=dict(color=line_color)))
                anomalies = v_df[v_df['value'] > active_thresh]
                if not anomalies.empty:
                    fig.add_trace(go.Scatter(x=anomalies['timestamp'], y=anomalies['value'], mode='markers', 
                                             marker=dict(color=cfg.COLOR_WARN_AMBER, size=12, line=dict(color=cfg.COLOR_DANGER_RED, width=2)), 
                                             name=f"{vendor} Critical Event"))

            # Dynamic Horizontal Line Placement based on the adaptive threshold
            fig.add_hline(y=active_thresh, line_dash="dash", line_color=cfg.COLOR_DANGER_RED, annotation_text=f"CRITICAL ACTION THRESHOLD ({active_thresh})")
            fig.update_layout(template="plotly_dark", plot_bgcolor=cfg.COLOR_BG_PRIMARY, paper_bgcolor=cfg.COLOR_BG_PRIMARY, xaxis_title="TIMESTAMP", yaxis_title="METRIC VALUE", height=500)
            st.plotly_chart(fig, use_container_width=True)

            alarms_df = df[df['category'] == 'ALARM'].drop_duplicates(subset=['rca_diagnosis'])
            if not alarms_df.empty:
                st.divider()
                st.subheader("EXECUTIVE MACRO MITIGATION PLAN")
                if st.button("GENERATE MITIGATION STRATEGY"):
                    with st.spinner("Compiling structural analysis..."):
                        faults = " | ".join(alarms_df['rca_diagnosis'].astype(str).tolist())
                        prompt = f"You are a fab manager. Based on these concurrent faults: [{faults}], generate a concise, 3-step physical mitigation plan for the floor technicians. Do not use markdown."
                        try:
                            resp = requests.post(cfg.OLLAMA_URL, json={"model": cfg.MODEL_NAME, "prompt": prompt, "stream": False}, timeout=15)
                            st.session_state['macro_plan'] = resp.json().get("response", "Error generating plan.")
                        except Exception:
                            st.session_state['macro_plan'] = "Macro Plan generation timed out. Local LLM may be busy."
                if st.session_state['macro_plan']: st.info(st.session_state['macro_plan'])

            st.divider()
            m1, m2, m3 = st.columns(3)
            alarms = len(df[df['category'] == 'ALARM'])
            availability = ((len(df) - alarms) / len(df)) * 100 if len(df) > 0 else 100
            drift_count = len(df[df['drift_warning'] == "Drift Detected"])
            scrap_est = df['yield_scrap_est'].sum()
            
            m1.metric("TOOL AVAILABILITY", f"{availability:.1f}%")
            m2.metric("PREDICTIVE DRIFT EVENTS", drift_count)
            m3.metric("ESTIMATED SCRAP", f"{scrap_est:.1f} Units")

            st.subheader("UNIFIED INTELLIGENCE SCHEMA")
            
            with st.expander("VIEW SEMI E30/GEM TERMINOLOGY GLOSSARY"):
                st.markdown(f"""
                <div style='color: {cfg.COLOR_ACCENT_PLATINUM}; font-family: {cfg.FONT_MAIN}; font-size: 0.9rem;'>
                <strong>EQP_ID (Equipment ID):</strong> The unique identifier for the specific manufacturing tool or machine.<br><br>
                <strong>CEID_Class (Collection Event ID):</strong> The classification of the event type (e.g., standard SENSOR telemetry vs. a critical ALARM).<br><br>
                <strong>SVID_Value (Status Variable ID):</strong> The actual numerical reading extracted from the tool's sensor log.<br><br>
                <strong>FDC_Diagnosis (Fault Detection and Classification):</strong> The root cause analysis or assigned fault category determined by the AI Copilot.
                </div>
                """, unsafe_allow_html=True)
            
            display_mapping = {
                'timestamp': 'Timestamp',
                'tool_id': 'EQP_ID',
                'vendor': 'Vendor',
                'category': 'CEID_Class',
                'severity': 'Severity',
                'value': 'SVID_Value',
                'Confidence_Score': 'Confidence_Score',
                'drift_warning': 'Drift_Status',
                'rca_diagnosis': 'FDC_Diagnosis',
                'yield_scrap_est': 'Yield_Scrap_Est'
            }
            
            df_display = df.rename(columns=display_mapping)
            cols = list(display_mapping.values())
            df_display = df_display.reindex(columns=cols).fillna("N/A")
            
            c_table, c_btn = st.columns([8, 1])
            c_table.dataframe(df_display, use_container_width=True)
            csv = df_display.to_csv(index=False).encode('utf-8')
            c_btn.download_button("EXPORT CSV", data=csv, file_name="normalized_fab_logs.csv", mime="text/csv")

            # --- FACTORY AI COPILOT ---
            st.divider()
            st.subheader(cfg.TITLE_COPILOT)
            st.caption("Query normalized data vectors or ask general knowledge questions.")

            # Render existing chat history
            for msg in st.session_state['chat_history']:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if user_q := st.chat_input("Enter diagnostic query or general question..."):
                # Append user question to UI
                st.session_state['chat_history'].append({"role": "user", "content": user_q})
                with st.chat_message("user"): 
                    st.markdown(user_q)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing parameters..."):
                        
                        # Build the contextual factory data
                        context_blocks = []
                        context_blocks.append("=== SYSTEM-WIDE ANALYTICS (REAL-TIME) ===")
                        context_blocks.append(f"Current Tool Availability: {availability:.1f}%")
                        context_blocks.append(f"Predictive Drift Events Flagged: {drift_count}")
                        if has_raw_files:
                            context_blocks.append(f"Current Batch Size: {batch} time steps")
                        context_blocks.append(f"Estimated Wafer Scrap: {scrap_est:.1f} Units")
                        context_blocks.append(f"Estimated Financial Loss: ${scrap_est * cfg.WAFER_UNIT_COST:,.2f}") 
                        context_blocks.append(f"Action Threshold: {active_thresh:.2f}")
                        context_blocks.append("=========================================\n")

                        alarm_rows = df_display[df_display['CEID_Class'] == 'ALARM']
                        if alarm_rows.empty:
                            context_blocks.append("No critical alarms detected in this batch.")
                        else:
                            unique_alarms = alarm_rows.drop_duplicates(subset=['Timestamp', 'Vendor'])
                            for _, row in unique_alarms.iterrows():
                                context_blocks.append(f"At exact time {row['Timestamp']}, {row['Vendor']} (Tool: {row['EQP_ID']}) triggered an ALARM with metric spiking to {row['SVID_Value']}. Root cause: {row['FDC_Diagnosis']}.")
                        
                        info_rows = df_display[df_display['CEID_Class'] == 'INFO']
                        if not info_rows.empty:
                            context_blocks.append(f"There were {len(info_rows)} normal operational events recorded.")

                        clean_context = "\n".join(context_blocks)
                        
                        # --- THE DUAL-MODE PROMPT ---
                        copilot_prompt = f"""You are the advanced Fab Diagnostic AI Copilot. You are highly intelligent, helpful, and conversational.

=== LIVE FACTORY DATA STREAM ===
{clean_context}
================================

User Question: {user_q}

INSTRUCTIONS:
1. FACTORY QUERIES: If the user asks about the factory data, alarms, or status, answer using ONLY the Live Factory Data Stream above.
2. GENERAL QUERIES: If the user asks a general question (like math, greetings, coding, or science), completely ignore the factory data and answer it normally and politely.
3. ALWAYS output a text response. Never remain silent.
"""
                        
                        try:
                            # Temperature raised to 0.5 to allow for conversational flexibility
                            resp = requests.post(cfg.OLLAMA_URL, json={
                                "model": cfg.MODEL_NAME, 
                                "prompt": copilot_prompt, 
                                "stream": False,
                                "options": {"temperature": 0.5}
                            }, timeout=15)
                            
                            # Safely extract the response and strip whitespace
                            answer = resp.json().get("response", "").strip()
                            
                            # --- THE FAILSAFE SHIELD ---
                            if not answer:
                                answer = "I processed your request, but my logic core returned an empty response. Could you try rephrasing that?"
                            
                            st.markdown(answer)
                            st.session_state['chat_history'].append({"role": "assistant", "content": answer})
                            
                        except requests.exceptions.RequestException as e:
                            err_msg = f"Connection error to AI Core. Is Docker bridging correctly? Error: {e}"
                            st.error(err_msg)
                            st.session_state['chat_history'].append({"role": "assistant", "content": err_msg})
                        except Exception as e:
                            err_msg = f"An unexpected error occurred in the logic core: {e}"
                            st.error(err_msg)
                            st.session_state['chat_history'].append({"role": "assistant", "content": err_msg})