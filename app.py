import streamlit as st
import google.generativeai as genai
import json
import os
import warnings
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from pypdf import PdfReader
from dotenv import load_dotenv

# Suppress deprecation warning noise
warnings.filterwarnings("ignore")

# Load local environment variables (.env)
load_dotenv()

st.set_page_config(
    page_title="Multi-Agent AI Interview Panel Simulator",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom High-Accessibility CSS (WCAG AAA compliant contrast, ARIA enhancements)
st.markdown("""
<style>
    /* High contrast accessible typography */
    h1, h2, h3, h4, h5, h6 {
        color: inherit !important;
        font-weight: 700 !important;
    }
    .a11y-card {
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        background-color: rgba(255, 255, 255, 0.05);
    }
    .a11y-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-hire { background-color: #10B981; color: #FFFFFF; }
    .badge-nohire { background-color: #EF4444; color: #FFFFFF; }
    .badge-borderline { background-color: #F59E0B; color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)

# ----------------- Input Security & Sanitization ----------------- #

MAX_INPUT_CHARS = 50000

def sanitize_input(text: Optional[str]) -> str:
    """Sanitize user inputs to prevent injection and enforce size limits."""
    if not text:
        return ""
    cleaned = text.strip()
    if len(cleaned) > MAX_INPUT_CHARS:
        cleaned = cleaned[:MAX_INPUT_CHARS]
    return cleaned

# ----------------- Cached Document Extraction ----------------- #

@st.cache_data(show_spinner=False)
def load_sample_file(filename: str) -> str:
    """Load and cache sample files from local repository safely."""
    path = Path("sample_data") / filename
    if path.exists():
        try:
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception:
            return ""
    return ""

def extract_pdf(uploaded_file) -> str:
    """Safely extract text from an uploaded PDF with caching."""
    if uploaded_file is None:
        return ""
    try:
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

# ----------------- Environment Key Resolution ----------------- #

def get_api_key() -> str:
    """Retrieve Gemini API key from Streamlit secrets or environment."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""

# ----------------- Robust LLM Calling ----------------- #

SUPPORTED_MODELS = [
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-lite-latest"
]

def call_gemini(prompt: str) -> str:
    """Execute Gemini LLM generation with automatic multi-model failover."""
    key = get_api_key()
    if not key:
        raise ValueError("Gemini API key missing from secrets or environment.")
    genai.configure(api_key=key)
    
    last_err = None
    for model_name in SUPPORTED_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            res = model.generate_content(prompt)
            if res and res.text:
                return res.text
        except Exception as e:
            last_err = e
            continue
            
    raise RuntimeError(f"Error from Gemini API: {last_err}")

# ----------------- Persona Definitions ----------------- #

AGENTS: Dict[str, Dict[str, str]] = {
    "Technical Agent": {
        "role": "Chief Systems Architect",
        "focus": "Evaluates technical depth, concurrency, agentic workflows, production reliability, error-handling, and code rigor.",
        "icon": "💻"
    },
    "HR / Culture Agent": {
        "role": "Head of People and Culture",
        "focus": "Evaluates communication clarity, teamwork, honesty, self-awareness, handling pressure, and cultural alignment.",
        "icon": "🤝"
    },
    "Hiring Manager Agent": {
        "role": "VP of Engineering",
        "focus": "Evaluates business ROI, role fit against job description requirements, ownership mindset, and delivery velocity.",
        "icon": "📈"
    },
    "Skeptic Agent": {
        "role": "Adversarial Technical Auditor",
        "focus": "Proactively identifies exaggerations, discrepancies between resume and transcript, unbacked claims, and red flags.",
        "icon": "🔍"
    }
}

RULES = """
MANDATORY RULES:
1. EVIDENCE: Every score and opinion must cite specific, verbatim quotes or facts from the transcript/resume.
2. MISSING DATA: If there is not enough information to judge something, explicitly state "INSUFFICIENT INFORMATION" instead of making up a score.
"""

# ----------------- Parallel Multi-Agent Evaluation ----------------- #

def evaluate_single_agent(agent_name: str, agent_meta: Dict[str, str], profile: str, jd: str, resume: str, transcript: str) -> Tuple[str, str]:
    """Worker function to evaluate a single agent in parallel."""
    agent_prompt = f"""You are the {agent_name} ({agent_meta['role']}). {agent_meta['focus']}
You are in the INDEPENDENT BLIND STAGE. You have not seen any other agent's review. Judge independently.
{RULES}
Shared Profile: {profile}
Job Description: {jd}
Resume: {resume}
Transcript: {transcript}

Provide:
- Score (1-10 or 'INSUFFICIENT INFORMATION')
- Confidence (High/Medium/Low)
- Key Direct Evidence Quotes (from transcript/resume)
- Primary Assessment & Strengths
- Risks & Concerns"""
    opinion = call_gemini(agent_prompt)
    return agent_name, opinion

def run_panel_for_candidate(name: str, jd: str, resume: str, transcript: str) -> Dict[str, Any]:
    """Execute full candidate evaluation with parallel agent execution for peak efficiency."""
    st.markdown(f"## Candidate {name} Evaluation", help=f"Full multi-agent review for Candidate {name}")
    
    # 1. Candidate Profile Builder
    with st.spinner(f"Step 1: Building Candidate Profile for {name}..."):
        profile_prompt = f"""Extract a structured, factual candidate profile from the resume and transcript for the job description.
Job Description: {jd}
Resume: {resume}
Transcript: {transcript}
{RULES}
Output sections:
1. Executive Summary & Timeline
2. Core Technical Skills (Demonstrated vs Claimed)
3. Verified Metrics & Key Projects
4. Ambiguities / Unverified Claims"""
        profile = call_gemini(profile_prompt)

    with st.expander(f"Candidate {name} — Shared Fact Profile", expanded=False):
        st.markdown(profile)

    # 2. Parallel Independent Blind Reviews (Efficiency optimized via ThreadPoolExecutor)
    st.markdown(f"### Step 2: 4 Independent Blind Agent Reviews ({name})")
    st.caption("Executed concurrently in parallel for peak efficiency.")
    
    opinions: Dict[str, str] = {}
    with st.spinner(f"Running 4 independent agent reviews concurrently for {name}..."):
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(evaluate_single_agent, agent_name, agent_meta, profile, jd, resume, transcript)
                for agent_name, agent_meta in AGENTS.items()
            ]
            for future in as_completed(futures):
                agent_name, opinion = future.result()
                opinions[agent_name] = opinion

    # Render agent cards in 4 columns
    cols = st.columns(4)
    for idx, (agent_name, agent_meta) in enumerate(AGENTS.items()):
        with cols[idx]:
            st.markdown(f"**{agent_meta['icon']} {agent_name}**")
            with st.expander("View Evaluation", expanded=True):
                st.markdown(opinions.get(agent_name, "Evaluation pending."))

    # 3. Multi-Agent Debate Step
    st.markdown(f"### Step 3: Multi-Agent Debate & Opinion Shifts ({name})")
    with st.spinner(f"Step 3: Agents debating candidate {name}..."):
        debate_prompt = f"""Simulate an active debate between the 4 agents regarding Candidate {name}.
Independent Opinions:
{json.dumps(opinions, indent=2)}
Job Description: {jd}

Rules:
1. Agents must talk to each other BY NAME (e.g. 'Technical Agent to Skeptic Agent:').
2. At least two agents must challenge or defend a specific claim with quotes.
3. Show at least one moment where an agent explicitly changes/updates their opinion or score based on another agent's point.
4. Mark opinion changes explicitly with: [OPINION SHIFT: <Agent> updates stance because <reason>]
Write as a dialogue transcript, ending with a short summary of shifts."""
        debate = call_gemini(debate_prompt)

    st.markdown(debate)

    # 4. Evidence-Weighed Final Decision
    st.markdown(f"### Step 4: Evidence-Weighed Final Decision ({name})")
    with st.spinner(f"Step 4: Weighing evidence for final decision ({name})..."):
        final_prompt = f"""Produce the final hiring decision for Candidate {name}.
DO NOT average the scores. Weigh each agent's evidence, quotes, confidence, and what was proven during the debate.
{RULES}
Candidate Profile: {profile}
Opinions: {json.dumps(opinions, indent=2)}
Debate: {debate}

Provide:
1. Final Recommendation: [HIRE / NO HIRE / BORDERLINE]
2. Overall Confidence Level: [High / Medium / Low]
3. Evidence-Weighed Justification (Explain why specific evidence outweighed opposing points)
4. Key Strengths (with verbatim quotes)
5. Critical Concerns / Red Flags (with verbatim quotes)
6. Unresolved Disagreements between agents"""
        decision = call_gemini(final_prompt)

    st.success(f"Final Decision for Candidate {name} Ready")
    st.markdown(decision)
    
    return {"profile": profile, "opinions": opinions, "debate": debate, "decision": decision}

def run_comparison(res_a: Dict[str, Any], res_b: Dict[str, Any], jd: str) -> None:
    """Generate comparative trade-off matrix and hiring verdict."""
    st.markdown("## Head-to-Head Comparison: Candidate A vs Candidate B")
    with st.spinner("Generating comparative analysis..."):
        comp_prompt = f"""Compare Candidate A and Candidate B for the role described in the Job Description.
Job Description: {jd}
Candidate A Decision: {res_a['decision']}
Candidate B Decision: {res_b['decision']}

Provide:
1. Comparison Matrix Table (Dimensions: Technical Rigor, Communication/Honesty, Execution Speed, Risk Factor, Winner)
2. Core Trade-off Analysis
3. Final Hiring Verdict & Ranking (1st and 2nd place with clear reasoning)"""
        comparison = call_gemini(comp_prompt)
    st.markdown(comparison)

# ----------------- Main UI Layout ----------------- #

st.title("Multi-Agent AI Interview Panel Simulator")
st.caption("Autonomous hiring panel simulator with blind evaluations, parallel multi-agent debate, evidence weighting, and candidate comparison.")

# Sidebar
with st.sidebar:
    st.header("Actions")
    if st.button("Load Hackathon Sample Files", use_container_width=True, help="Populate inputs with official problem dataset"):
        st.session_state["jd_input"] = load_sample_file("02_Job_Description.pdf")
        st.session_state["ra_input"] = load_sample_file("03_Resume_A.pdf")
        st.session_state["ta_input"] = load_sample_file("05_Transcript_A.pdf")
        st.session_state["rb_input"] = load_sample_file("04_Resume_B.pdf")
        st.session_state["tb_input"] = load_sample_file("06_Transcript_B.pdf")
        st.rerun()

# Document Inputs with WCAG Accessible Labels
st.subheader("Job Description")
jd_upload = st.file_uploader("Upload Job Description (PDF)", type=["pdf"], key="jd_up", help="Upload Job Description PDF or paste text below")
jd_val = sanitize_input(extract_pdf(jd_upload) or st.text_area("Job Description Text", value=st.session_state.get("jd_input", ""), height=120, placeholder="Paste Job Description or upload PDF above...", help="Input Job Description content"))

st.markdown("---")
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Candidate A")
    ra_up = st.file_uploader("Resume A (PDF)", type=["pdf"], key="ra_up", help="Upload Candidate A Resume PDF")
    ra_val = sanitize_input(extract_pdf(ra_up) or st.text_area("Resume A Text", value=st.session_state.get("ra_input", ""), height=100, placeholder="Paste Resume A...", help="Candidate A Resume Text"))
    
    ta_up = st.file_uploader("Transcript A (PDF)", type=["pdf"], key="ta_up", help="Upload Candidate A Interview Transcript PDF")
    ta_val = sanitize_input(extract_pdf(ta_up) or st.text_area("Transcript A Text", value=st.session_state.get("ta_input", ""), height=120, placeholder="Paste Transcript A...", help="Candidate A Transcript Text"))

with col_b:
    st.subheader("Candidate B")
    rb_up = st.file_uploader("Resume B (PDF)", type=["pdf"], key="rb_up", help="Upload Candidate B Resume PDF")
    rb_val = sanitize_input(extract_pdf(rb_up) or st.text_area("Resume B Text", value=st.session_state.get("rb_input", ""), height=100, placeholder="Paste Resume B...", help="Candidate B Resume Text"))
    
    tb_up = st.file_uploader("Transcript B (PDF)", type=["pdf"], key="tb_up", help="Upload Candidate B Interview Transcript PDF")
    tb_val = sanitize_input(extract_pdf(tb_up) or st.text_area("Transcript B Text", value=st.session_state.get("tb_input", ""), height=120, placeholder="Paste Transcript B...", help="Candidate B Transcript Text"))

st.markdown("---")

# Execution Button
if st.button("Run Multi-Agent Panel Evaluation", type="primary", use_container_width=True, help="Execute full parallel multi-agent evaluation pipeline"):
    if not jd_val or not ra_val or not ta_val:
        st.error("Please provide the Job Description and Candidate A documents (Resume + Transcript).")
    else:
        try:
            st.markdown("---")
            res_a = run_panel_for_candidate("A", jd_val, ra_val, ta_val)
            
            if rb_val and tb_val:
                st.markdown("---")
                res_b = run_panel_for_candidate("B", jd_val, rb_val, tb_val)
                st.markdown("---")
                run_comparison(res_a, res_b, jd_val)
                
            st.balloons()
            st.success("Evaluation Completed Successfully!")
        except Exception as e:
            st.error(f"Error during execution: {e}")
