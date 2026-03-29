"""
streamlit_app.py  —  Parasite Classifier Frontend
===================================================
Run:
    streamlit run streamlit_app.py

Requires the FastAPI backend running at API_URL (default: http://localhost:8000).
Set API_URL env var to override.
"""

import base64
import io
import os
import time

import requests
import streamlit as st
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────

def _get_api_url() -> str:
    # 1. Streamlit Cloud secrets (st.secrets["API_URL"])
    try:
        return st.secrets["API_URL"]
    except Exception:
        pass
    # 2. Environment variable
    env = os.getenv("API_URL")
    if env:
        return env.rstrip("/")
    # 3. Local default
    return "http://localhost:8000"

API_URL = _get_api_url()

CLASS_COLORS = {
    "Babesia":     "#e74c3c",
    "Leishmania":  "#9b59b6",
    "Toxoplasma":  "#2ecc71",
    "Trichomonad": "#f39c12",
    "Trypanosome": "#3498db",
}

CLASS_ICONS = {
    "Babesia":     "🔴",
    "Leishmania":  "🟣",
    "Toxoplasma":  "🟢",
    "Trichomonad": "🟡",
    "Trypanosome": "🔵",
}

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ParaSight — Parasite Classifier",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;600;700;800&display=swap');

/* ── Root / tokens ── */
:root {
    --bg-base:      #0d0f14;
    --bg-surface:   #13161e;
    --bg-elevated:  #1a1e2a;
    --bg-hover:     #1f2435;
    --border:       #2a2f42;
    --border-light: #353b52;
    --text-primary: #e8eaf0;
    --text-secondary: #7c849e;
    --text-muted:   #4a5068;
    --accent:       #00e5a0;
    --accent-dim:   rgba(0, 229, 160, 0.12);
    --accent-glow:  rgba(0, 229, 160, 0.3);
    --danger:       #e74c3c;
    --mono:         'Space Mono', monospace;
    --display:      'Syne', sans-serif;
}

/* ── Global reset ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-base) !important;
    color: var(--text-primary) !important;
}

[data-testid="stAppViewContainer"] > .main {
    background-color: var(--bg-base);
}

[data-testid="stSidebar"] {
    background-color: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}

/* ── Typography ── */
h1, h2, h3 { font-family: var(--display) !important; letter-spacing: -0.02em; }
p, div, span, label { font-family: var(--mono) !important; font-size: 0.82rem; }

/* ── Streamlit widgets: inputs ── */
[data-testid="stFileUploader"] {
    background: var(--bg-surface) !important;
    border: 1px dashed var(--border-light) !important;
    border-radius: 8px !important;
    transition: border-color 0.2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
}

/* ── Sliders ── */
[data-testid="stSlider"] > div > div > div {
    background: var(--accent) !important;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
    background: var(--accent) !important;
    color: #0d0f14 !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: var(--mono) !important;
    font-weight: 700 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.4rem !important;
    transition: opacity 0.15s, box-shadow 0.15s !important;
}
[data-testid="stButton"] > button:hover {
    opacity: 0.88 !important;
    box-shadow: 0 0 16px var(--accent-glow) !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--text-primary) !important;
}

/* ── Metric boxes ── */
[data-testid="stMetric"] {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 1rem !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1.5rem 0; }

/* ── Status badge utility ── */
.status-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    margin-right: 6px;
    background: var(--accent);
    box-shadow: 0 0 6px var(--accent-glow);
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
}

/* ── Info cards ── */
.info-card {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.8rem;
}
.info-card .label {
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.3rem;
}
.info-card .value {
    font-family: var(--mono);
    font-size: 0.85rem;
    color: var(--text-primary);
    line-height: 1.5;
}

/* ── Prob bar ── */
.prob-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 0.55rem;
}
.prob-label {
    font-family: var(--mono);
    font-size: 0.75rem;
    width: 110px;
    flex-shrink: 0;
    color: var(--text-secondary);
}
.prob-bar-bg {
    flex: 1;
    height: 6px;
    background: var(--bg-surface);
    border-radius: 3px;
    overflow: hidden;
}
.prob-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s cubic-bezier(0.16,1,0.3,1);
}
.prob-value {
    font-family: var(--mono);
    font-size: 0.72rem;
    width: 44px;
    text-align: right;
    color: var(--text-secondary);
    flex-shrink: 0;
}

/* ── Prediction headline ── */
.pred-headline {
    font-family: var(--display);
    font-weight: 800;
    font-size: 2.4rem;
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin-bottom: 0.2rem;
}
.confidence-chip {
    display: inline-block;
    font-family: var(--mono);
    font-size: 0.75rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.05em;
}

/* ── Upload zone label ── */
.upload-hint {
    font-family: var(--mono);
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.4rem;
}

/* ── Scanline overlay on images ── */
.img-wrapper {
    position: relative;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid var(--border);
}
.img-corner-tl, .img-corner-br {
    position: absolute;
    width: 14px; height: 14px;
    border-color: var(--accent);
    border-style: solid;
    opacity: 0.7;
}
.img-corner-tl { top: 8px; left: 8px; border-width: 2px 0 0 2px; }
.img-corner-br { bottom: 8px; right: 8px; border-width: 0 2px 2px 0; }
.img-label {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted);
    background: linear-gradient(to top, rgba(13,15,20,0.9), transparent);
    padding: 18px 10px 8px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def api_get(path: str) -> dict | None:
    try:
        r = requests.get(f"{API_URL}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_predict(file_bytes: bytes, filename: str, model_id: str,
                gradcam: bool, alpha: float, target_class: int | None) -> dict | None:
    params = {"model_id": model_id, "gradcam": gradcam, "alpha": alpha}
    if target_class is not None:
        params["target_class"] = target_class
    try:
        r = requests.post(
            f"{API_URL}/predict",
            params=params,
            files={"file": (filename, file_bytes, "image/jpeg")},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def b64_to_pil(b64_str: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64_str)))


def render_prob_bars(probs: dict, predicted_class: str):
    bars_html = ""
    for cls, prob in probs.items():
        color    = CLASS_COLORS.get(cls, "#7c849e")
        is_pred  = cls == predicted_class
        opacity  = "1.0" if is_pred else "0.45"
        label_color = "var(--text-primary)" if is_pred else "var(--text-secondary)"
        pct      = prob * 100
        bars_html += f"""
        <div class="prob-row">
          <span class="prob-label" style="color:{label_color};{'font-weight:700;' if is_pred else ''}">{CLASS_ICONS.get(cls,'')} {cls}</span>
          <div class="prob-bar-bg">
            <div class="prob-bar-fill" style="width:{pct:.1f}%;background:{color};opacity:{opacity};"></div>
          </div>
          <span class="prob-value" style="{'color:'+color+';font-weight:700;' if is_pred else ''}">{pct:.1f}%</span>
        </div>"""
    st.markdown(bars_html, unsafe_allow_html=True)


def render_image_with_overlay(img: Image.Image, label: str):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    st.markdown(f"""
    <div class="img-wrapper">
      <img src="data:image/png;base64,{b64}" style="width:100%;display:block;" />
      <div class="img-corner-tl"></div>
      <div class="img-corner-br"></div>
      <div class="img-label">{label}</div>
    </div>""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="margin-bottom:1.6rem;">
      <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.35rem;
                  letter-spacing:-0.02em;color:#e8eaf0;">🔬 ParaSight</div>
      <div style="font-family:'Space Mono',monospace;font-size:0.68rem;
                  letter-spacing:0.1em;text-transform:uppercase;color:#4a5068;
                  margin-top:2px;">Parasite Classification System</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Backend health ────────────────────────────────────────────────────────
    health = api_get("/health")
    if health:
        st.markdown(f"""
        <div class="info-card" style="margin-bottom:1.2rem;">
          <div class="label">Backend Status</div>
          <div class="value">
            <span class="status-dot"></span>Online · {health.get('device','cpu').upper()}
          </div>
          <div style="margin-top:6px;font-family:'Space Mono',monospace;
                      font-size:0.7rem;color:#4a5068;">
            Uptime {health.get('uptime_seconds',0):.0f}s &nbsp;·&nbsp;
            {', '.join(health.get('loaded_models',[])) or 'no models'}
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-card" style="border-color:#e74c3c33;margin-bottom:1.2rem;">
          <div class="label">Backend Status</div>
          <div class="value" style="color:#e74c3c;">
            ⚠ Offline — start uvicorn
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    # ── Model selector ────────────────────────────────────────────────────────
    st.markdown('<div class="label" style="font-family:\'Space Mono\',monospace;font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;color:#4a5068;margin-bottom:6px;">Model</div>', unsafe_allow_html=True)
    models_data  = api_get("/models")
    model_options = (
        {m["model_id"]: m["display_name"] for m in models_data.get("models", [])}
        if models_data else {"parasite_cnn_v1": "ParasiteCNN v1 (5-class)"}
    )
    selected_model_id = st.selectbox(
        label="model", label_visibility="collapsed",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
    )

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

    # ── Grad-CAM settings ─────────────────────────────────────────────────────
    st.markdown('<div class="label" style="font-family:\'Space Mono\',monospace;font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;color:#4a5068;margin-bottom:6px;">Grad-CAM</div>', unsafe_allow_html=True)
    gradcam_on = st.toggle("Enable Grad-CAM overlay", value=True)

    alpha = 0.5
    if gradcam_on:
        alpha = st.slider("Heatmap intensity", 0.1, 0.9, 0.5, 0.05)

    class_names = ["Babesia", "Leishmania", "Toxoplasma", "Trichomonad", "Trypanosome"]
    force_class_name = st.selectbox(
        "Force target class (optional)",
        options=["— auto (predicted) —"] + class_names,
    )
    target_class = (
        None if force_class_name.startswith("—")
        else class_names.index(force_class_name)
    )

    st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)

    # ── Model info ─────────────────────────────────────────────────────────────
    model_info = api_get(f"/models/{selected_model_id}/info") if health else None
    if model_info:
        with st.expander("Model details"):
            st.markdown(f"""
            <div style="font-family:'Space Mono',monospace;font-size:0.74rem;line-height:1.7;color:#7c849e;">
              <b style="color:#e8eaf0;">{model_info['display_name']}</b><br/>
              {model_info['description']}<br/><br/>
              <span style="color:#4a5068;">Architecture</span> {model_info['architecture']}<br/>
              <span style="color:#4a5068;">Input size</span> {model_info['input_size']}×{model_info['input_size']}<br/>
              <span style="color:#4a5068;">Classes</span> {model_info['num_classes']}<br/>
            </div>""", unsafe_allow_html=True)


# ── Main layout ───────────────────────────────────────────────────────────────

st.markdown("""
<div style="margin-bottom:2rem;">
  <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:2rem;
              letter-spacing:-0.03em;color:#e8eaf0;line-height:1.1;">
    Parasite Classification
  </div>
  <div style="font-family:'Space Mono',monospace;font-size:0.72rem;
              color:#4a5068;letter-spacing:0.06em;text-transform:uppercase;
              margin-top:4px;">
    Upload a microscopy image to identify the parasite and visualise discriminative regions
  </div>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────

st.markdown('<div class="upload-hint">Drop image or click to browse — JPG / PNG</div>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    label="upload", label_visibility="collapsed",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False,
)

if not uploaded:
    # ── Empty state ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-top:3rem;text-align:center;padding:4rem 2rem;
                border:1px dashed #2a2f42;border-radius:12px;background:#13161e;">
      <div style="font-size:3rem;margin-bottom:1rem;">🔬</div>
      <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem;
                  color:#e8eaf0;margin-bottom:0.5rem;">No image uploaded</div>
      <div style="font-family:'Space Mono',monospace;font-size:0.72rem;color:#4a5068;">
        Supports: Babesia · Leishmania · Toxoplasma · Trichomonad · Trypanosome
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Load uploaded image ───────────────────────────────────────────────────────

file_bytes = uploaded.read()
pil_input  = Image.open(io.BytesIO(file_bytes)).convert("RGB")

st.markdown("<hr/>", unsafe_allow_html=True)

# ── Run inference ─────────────────────────────────────────────────────────────

col_btn, col_spacer = st.columns([1, 5])
with col_btn:
    run = st.button("▶ Analyse")

if "last_result"    not in st.session_state: st.session_state.last_result = None
if "last_filename"  not in st.session_state: st.session_state.last_filename = None

if run:
    if not health:
        st.error("Backend is offline. Start the FastAPI server first.")
        st.stop()

    with st.spinner("Running inference..."):
        result = api_predict(
            file_bytes   = file_bytes,
            filename     = uploaded.name,
            model_id     = selected_model_id,
            gradcam      = gradcam_on,
            alpha        = alpha,
            target_class = target_class,
        )
    if result:
        st.session_state.last_result   = result
        st.session_state.last_filename = uploaded.name

# ── Render result ─────────────────────────────────────────────────────────────

result = st.session_state.last_result

if result is None:
    # Show uploaded image preview while waiting
    st.markdown('<div style="margin-top:1rem;max-width:400px;">', unsafe_allow_html=True)
    render_image_with_overlay(pil_input, "Uploaded image — awaiting analysis")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ── Results are ready ─────────────────────────────────────────────────────────

pred_class  = result["predicted_class"]
confidence  = result["confidence"]
probs       = result["probabilities"]
class_info  = result["class_info"]
overlay_b64 = result.get("gradcam_overlay")
inf_ms      = result.get("inference_ms", 0)
accent      = CLASS_COLORS.get(pred_class, "#00e5a0")

# ── Top: prediction headline ──────────────────────────────────────────────────

conf_pct = confidence * 100
conf_color = "#00e5a0" if conf_pct >= 90 else "#f39c12" if conf_pct >= 70 else "#e74c3c"

st.markdown(f"""
<div style="display:flex;align-items:center;gap:1.2rem;margin:1.2rem 0 1.6rem;">
  <div>
    <div class="pred-headline" style="color:{accent};">
      {CLASS_ICONS.get(pred_class,'')} {pred_class}
    </div>
    <div style="margin-top:6px;display:flex;align-items:center;gap:10px;">
      <span class="confidence-chip"
            style="background:{conf_color}22;color:{conf_color};border:1px solid {conf_color}44;">
        {conf_pct:.1f}% confidence
      </span>
      <span style="font-family:'Space Mono',monospace;font-size:0.68rem;color:#4a5068;">
        {inf_ms:.0f} ms · {st.session_state.last_filename or ''}
      </span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Two-column main view ──────────────────────────────────────────────────────

col_images, col_details = st.columns([3, 2], gap="large")

with col_images:
    if overlay_b64:
        overlay_pil = b64_to_pil(overlay_b64)
        img_cols = st.columns(2, gap="small")
        with img_cols[0]:
            render_image_with_overlay(pil_input.resize((256, 256), Image.LANCZOS), "Original")
        with img_cols[1]:
            render_image_with_overlay(overlay_pil, f"Grad-CAM · {pred_class}")
    else:
        render_image_with_overlay(pil_input.resize((256, 256), Image.LANCZOS), "Original")

with col_details:
    # ── Probability bars ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-family:'Space Mono',monospace;font-size:0.68rem;
                letter-spacing:0.1em;text-transform:uppercase;color:#4a5068;
                margin-bottom:0.75rem;">Class Probabilities</div>
    """, unsafe_allow_html=True)
    render_prob_bars(probs, pred_class)

    st.markdown("<hr/>", unsafe_allow_html=True)

    # ── Class info ────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="info-card" style="border-left:3px solid {accent};">
      <div class="label">Description</div>
      <div class="value">{class_info.get('description','')}</div>
    </div>
    <div class="info-card">
      <div class="label">Morphology</div>
      <div class="value">{class_info.get('morphology','')}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Raw JSON (collapsed) ──────────────────────────────────────────────────
    with st.expander("Raw API response"):
        safe = {k: v for k, v in result.items() if k != "gradcam_overlay"}
        st.json(safe)
