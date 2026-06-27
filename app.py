import streamlit as st
from deep_translator import GoogleTranslator, MyMemoryTranslator
from langdetect import detect as detect_language
from gtts import gTTS
import base64
import io
import time

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LinguaAI — Language Translation Tool",
    page_icon="🌐",
    layout="centered"
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Background */
.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}

/* Hide Streamlit default elements */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

/* Hero Header */
.hero {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
}
.hero h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.6rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
    margin-bottom: 0.3rem;
}
.hero h1 span {
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero p {
    color: #94a3b8;
    font-size: 1rem;
    font-weight: 300;
}

/* Card */
.card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 1.8rem;
    margin-bottom: 1.2rem;
    backdrop-filter: blur(10px);
}

/* Labels */
.field-label {
    color: #cbd5e1;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 0.4rem;
}

/* Translation Output Box */
.output-box {
    background: rgba(167, 139, 250, 0.08);
    border: 1px solid rgba(167, 139, 250, 0.3);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    color: #e2e8f0;
    font-size: 1.05rem;
    line-height: 1.7;
    min-height: 80px;
    word-break: break-word;
}

/* Stat Pills */
.stat-row {
    display: flex;
    gap: 0.8rem;
    flex-wrap: wrap;
    margin-top: 1rem;
}
.stat-pill {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 0.35rem 0.9rem;
    color: #94a3b8;
    font-size: 0.78rem;
    font-weight: 500;
}
.stat-pill span {
    color: #a78bfa;
    font-weight: 600;
}

/* Badge */
.badge {
    display: inline-block;
    background: rgba(96, 165, 250, 0.15);
    color: #60a5fa;
    border-radius: 6px;
    padding: 0.15rem 0.6rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 0.6rem;
}

/* Divider */
.divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.07);
    margin: 1rem 0;
}

/* Success Banner */
.success-banner {
    background: rgba(52, 211, 153, 0.1);
    border: 1px solid rgba(52, 211, 153, 0.25);
    border-radius: 10px;
    padding: 0.8rem 1.2rem;
    color: #34d399;
    font-size: 0.85rem;
    font-weight: 500;
    margin-top: 0.8rem;
}

/* Engine Tag */
.engine-tag {
    display: inline-block;
    background: rgba(148, 163, 184, 0.1);
    color: #94a3b8;
    border-radius: 6px;
    padding: 0.1rem 0.5rem;
    font-size: 0.68rem;
    font-weight: 500;
    margin-left: 0.4rem;
}

/* Footer */
.footer {
    text-align: center;
    color: #475569;
    font-size: 0.75rem;
    margin-top: 2.5rem;
    padding-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ─── Language Map ───────────────────────────────────────────────────────────────
LANGUAGES = {
    "Auto Detect": "auto",
    "English": "en",
    "Hindi": "hi",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Chinese (Simplified)": "zh-CN",
    "Arabic": "ar",
    "Japanese": "ja",
    "Korean": "ko",
    "Portuguese": "pt",
    "Russian": "ru",
    "Italian": "it",
    "Dutch": "nl",
    "Turkish": "tr",
    "Bengali": "bn",
    "Punjabi": "pa",
    "Tamil": "ta",
    "Telugu": "te",
    "Urdu": "ur",
    "Gujarati": "gu",
    "Marathi": "mr",
    "Malay": "ms",
    "Indonesian": "id",
    "Thai": "th",
    "Vietnamese": "vi",
    "Polish": "pl",
    "Ukrainian": "uk",
    "Swedish": "sv",
    "Norwegian": "no",
}

LANG_NAMES = {v.lower(): k for k, v in LANGUAGES.items()}


def get_lang_name(code):
    """Map a language code back to its display name, falling back to the
    raw code (uppercased) if we don't have it in our dictionary."""
    return LANG_NAMES.get(code.lower(), code.upper())


# ─── Core Translation Logic (with automatic fallback) ──────────────────────────
def translate_text(text, src_code, tgt_code):
    """
    Translate `text` from src_code to tgt_code.

    Tries Google Translate first (via deep-translator). If that fails for
    any reason (network hiccup, rate limit, temporary block), it
    automatically falls back to the MyMemory translation engine so the
    user almost never sees a hard failure.

    Returns a dict: translated_text, detected_source_name, engine_used, elapsed_ms
    Raises the last exception only if BOTH engines fail.
    """
    start = time.time()

    # ── Attempt 1: Google Translate ──
    try:
        translated = GoogleTranslator(source=src_code, target=tgt_code).translate(text)

        if src_code == "auto":
            try:
                detected_code = detect_language(text)
            except Exception:
                detected_code = "auto"
        else:
            detected_code = src_code

        elapsed_ms = round((time.time() - start) * 1000)
        return {
            "translated_text": translated,
            "detected_source_name": get_lang_name(detected_code),
            "engine_used": "Google",
            "elapsed_ms": elapsed_ms,
        }

    except Exception:
        pass  # fall through to backup engine

    # ── Attempt 2: MyMemory (backup engine, no API key needed) ──
    # MyMemory doesn't support "auto" as a source — detect locally first.
    if src_code == "auto":
        try:
            mm_source = detect_language(text)
        except Exception:
            mm_source = "en"  # safe fallback
    else:
        mm_source = src_code

    translated = MyMemoryTranslator(source=mm_source, target=tgt_code).translate(text)
    elapsed_ms = round((time.time() - start) * 1000)

    return {
        "translated_text": translated,
        "detected_source_name": get_lang_name(mm_source),
        "engine_used": "MyMemory (backup)",
        "elapsed_ms": elapsed_ms,
    }


translator_ready = True  # kept for symmetry with earlier version; no persistent client needed

# ─── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="badge">AI POWERED</div>
    <h1>Lingua<span>AI</span></h1>
    <p>Translate instantly across 30+ languages · Text-to-Speech included</p>
</div>
""", unsafe_allow_html=True)

# ─── Language Selection ─────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="field-label">🌍 Language Settings</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    src_lang_name = st.selectbox(
        "Source Language",
        options=list(LANGUAGES.keys()),
        index=0,
        key="src"
    )
with col2:
    tgt_options = [k for k in LANGUAGES.keys() if k != "Auto Detect"]
    tgt_lang_name = st.selectbox(
        "Target Language",
        options=tgt_options,
        index=tgt_options.index("Hindi"),
        key="tgt"
    )

src_code = LANGUAGES[src_lang_name]
tgt_code = LANGUAGES[tgt_lang_name]
st.markdown('</div>', unsafe_allow_html=True)

# ─── Input ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="field-label">✏️ Enter Text</div>', unsafe_allow_html=True)

input_text = st.text_area(
    label="",
    placeholder="Type or paste your text here...",
    height=130,
    key="input_text",
    label_visibility="collapsed"
)

char_count = len(input_text)
word_count = len(input_text.split()) if input_text.strip() else 0

st.markdown(f"""
<div class="stat-row">
    <div class="stat-pill">Characters: <span>{char_count}</span></div>
    <div class="stat-pill">Words: <span>{word_count}</span></div>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ─── Translate Button ──────────────────────────────────────────────────────────
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    translate_btn = st.button("🔄 Translate Now", use_container_width=True, type="primary")

# ─── Output ────────────────────────────────────────────────────────────────────
if translate_btn:
    if not input_text.strip():
        st.warning("⚠️ Please enter some text to translate.")
    else:
        with st.spinner("Translating..."):
            try:
                result = translate_text(input_text, src_code, tgt_code)

                translated_text = result["translated_text"]
                detected_lang = result["detected_source_name"]
                elapsed = result["elapsed_ms"]
                engine_used = result["engine_used"]

                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="field-label">📄 Translated Output '
                    f'<span class="engine-tag">via {engine_used}</span></div>',
                    unsafe_allow_html=True
                )
                st.markdown(f'<div class="output-box">{translated_text}</div>', unsafe_allow_html=True)

                st.markdown(f"""
                <div class="stat-row">
                    <div class="stat-pill">Detected: <span>{detected_lang}</span></div>
                    <div class="stat-pill">→ <span>{tgt_lang_name}</span></div>
                    <div class="stat-pill">Time: <span>{elapsed}ms</span></div>
                </div>
                """, unsafe_allow_html=True)

                # ─ Copy Button ─
                st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                st.markdown('<div class="field-label">📋 Copy & Audio</div>', unsafe_allow_html=True)

                col_a, col_b = st.columns(2)
                with col_a:
                    st.code(translated_text, language=None)

                # ─ Text-to-Speech ─
                with col_b:
                    try:
                        # gTTS expects short codes like "hi", not "zh-CN" style
                        tts_lang = tgt_code.split("-")[0] if tgt_code != "auto" else "en"
                        tts = gTTS(text=translated_text, lang=tts_lang, slow=False)
                        audio_buf = io.BytesIO()
                        tts.write_to_fp(audio_buf)
                        audio_buf.seek(0)
                        audio_b64 = base64.b64encode(audio_buf.read()).decode()
                        st.markdown(f"""
                        <audio controls style="width:100%; margin-top:0.5rem; border-radius:8px;">
                            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                        </audio>
                        """, unsafe_allow_html=True)
                        st.caption("🔊 Listen to the translation")
                    except Exception:
                        st.info("Audio not available for this language.")

                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('<div class="success-banner">✅ Translation completed successfully</div>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"❌ Translation failed (both engines unavailable): {str(e)}")
                st.info("💡 Check your internet connection and try again in a few seconds.")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    Built with ❤️ by Navya · CodeAlpha AI Internship · Task 1 — Language Translation Tool
</div>
""", unsafe_allow_html=True)
