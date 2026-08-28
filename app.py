import streamlit as st
import google.generativeai as genai
import json
import os
import warnings
from pathlib import Path
from pypdf import PdfReader
from dotenv import load_dotenv

# Suppress deprecation warning noise
warnings.filterwarnings("ignore")

# Load local environment variables (.env)
load_dotenv()

st.set_page_config(
    page_title="Multi-Agent AI Interview Panel Simulator",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Helper to load sample files
def load_sample_file(filename):
    path = Path("sample_data") / filename
    if path.exists():
        try:
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception:
            return ""
    return ""

# Auto-detect API key from secrets or env
def get_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""

# Extract PDF text helper
def extract_pdf(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

# LLM Caller with guaranteed working models
SUPPORTED_MODELS = [
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-lite-latest"
]

def call_gemini(prompt: str) -> str:
    key = get_api_key()
    if not key:
        raise ValueError("API Key not found in Streamlit secrets or environment variables.")
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

# Personas
AGENTS = {
    "Technical Agent": "Evaluates technical depth, systems design, concurrency, agentic workflows, production reliability, error-handling, and code rigor.",
    "HR / Culture Agent": "Evaluates communication clarity, teamwork, honesty, self-awareness, handling pressure, and cultural alignment.",
    "Hiring Manager Agent": "Evaluates business ROI, role fit against job description requirements, ownership mindset, and delivery velocity.",
    "Skeptic Agent": "Proactively identifies exaggerations, discrepancies between resume and transcript, unbacked claims, and red flags."
}

RULES = """
MANDATORY RULES:
1. EVIDENCE: Every score and opinion must cite specific, verbatim quotes or facts from the transcript/resume.
2. MISSING DATA: If there is not enough information to judge something, explicitly state "INSUFFICIENT INFORMATION" instead of making up a score.
"""

def run_panel_for_candidate(name, jd, resume, transcript):
    st.markdown(f"## Candidate {name} Evaluation")
    
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

    # 2. Independent Blind Reviews
    st.markdown(f"### Step 2: 4 Independent Blind Agent Reviews ({name})")
    opinions = {}
    cols = st.columns(4)
    
    for idx, (agent_name, role_desc) in enumerate(AGENTS.items()):
        with cols[idx]:
            st.markdown(f"**{agent_name}**")
            with st.spinner(f"{agent_name}..."):
                agent_prompt = f"""You are the {agent_name}. {role_desc}
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
                opinions[agent_name] = opinion
            with st.expander("View Evaluation", expanded=True):
                st.markdown(opinion)

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

def run_comparison(res_a, res_b, jd):
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

# ----------------- UI Layout ----------------- #

st.title("Multi-Agent AI Interview Panel Simulator")
st.caption("Autonomous hiring panel simulator with blind evaluations, adversarial multi-agent debate, evidence weighting, and candidate comparison.")

# Sidebar
with st.sidebar:
    st.header("Actions")
    if st.button("Load Hackathon Sample Files", use_container_width=True):
        st.session_state["jd_input"] = load_sample_file("02_Job_Description.pdf")
        st.session_state["ra_input"] = load_sample_file("03_Resume_A.pdf")
        st.session_state["ta_input"] = load_sample_file("05_Transcript_A.pdf")
        st.session_state["rb_input"] = load_sample_file("04_Resume_B.pdf")
        st.session_state["tb_input"] = load_sample_file("06_Transcript_B.pdf")
        st.rerun()

# Document Inputs
st.subheader("Job Description")
jd_upload = st.file_uploader("Upload Job Description (PDF)", type=["pdf"], key="jd_up")
jd_val = extract_pdf(jd_upload) or st.text_area("Job Description Text", value=st.session_state.get("jd_input", ""), height=120, placeholder="Paste Job Description or upload PDF above...")

st.markdown("---")
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Candidate A")
    ra_up = st.file_uploader("Resume A (PDF)", type=["pdf"], key="ra_up")
    ra_val = extract_pdf(ra_up) or st.text_area("Resume A Text", value=st.session_state.get("ra_input", ""), height=100, placeholder="Paste Resume A...")
    
    ta_up = st.file_uploader("Transcript A (PDF)", type=["pdf"], key="ta_up")
    ta_val = extract_pdf(ta_up) or st.text_area("Transcript A Text", value=st.session_state.get("ta_input", ""), height=120, placeholder="Paste Transcript A...")

with col_b:
    st.subheader("Candidate B")
    rb_up = st.file_uploader("Resume B (PDF)", type=["pdf"], key="rb_up")
    rb_val = extract_pdf(rb_up) or st.text_area("Resume B Text", value=st.session_state.get("rb_input", ""), height=100, placeholder="Paste Resume B...")
    
    tb_up = st.file_uploader("Transcript B (PDF)", type=["pdf"], key="tb_up")
    tb_val = extract_pdf(tb_up) or st.text_area("Transcript B Text", value=st.session_state.get("tb_input", ""), height=120, placeholder="Paste Transcript B...")

st.markdown("---")

# Execution Button
if st.button("Run Multi-Agent Panel Evaluation", type="primary", use_container_width=True):
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
