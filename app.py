import streamlit as st
import google.generativeai as genai
import json
import os
from pathlib import Path
from pypdf import PdfReader
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

st.set_page_config(
    page_title="Multi-Agent AI Interview Panel Simulator",
    layout="wide",
    initial_sidebar_state="expanded"
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

# Auto-populate sample data defaults
if "jd_text" not in st.session_state:
    st.session_state["jd_text"] = load_sample_file("02_Job_Description.pdf")
    st.session_state["ra_text"] = load_sample_file("03_Resume_A.pdf")
    st.session_state["ta_text"] = load_sample_file("05_Transcript_A.pdf")
    st.session_state["rb_text"] = load_sample_file("04_Resume_B.pdf")
    st.session_state["tb_text"] = load_sample_file("06_Transcript_B.pdf")

# Detect API Key from secrets or env
def get_env_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""

env_key = get_env_key()

# Sidebar
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Gemini API Key", value=env_key, type="password", help="Loaded from secrets/.env if available.")
    model_name = st.selectbox("Model", ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"], index=0)
    
    st.markdown("---")
    if st.button("Reload Hackathon Sample Files", use_container_width=True):
        st.session_state["jd_text"] = load_sample_file("02_Job_Description.pdf")
        st.session_state["ra_text"] = load_sample_file("03_Resume_A.pdf")
        st.session_state["ta_text"] = load_sample_file("05_Transcript_A.pdf")
        st.session_state["rb_text"] = load_sample_file("04_Resume_B.pdf")
        st.session_state["tb_text"] = load_sample_file("06_Transcript_B.pdf")
        st.rerun()

# Extract PDF helper
def extract_pdf(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return ""

# LLM Caller with fallback
def call_gemini(prompt: str, model_choice: str, key: str) -> str:
    if not key:
        raise ValueError("Please provide a valid Gemini API Key in the sidebar or Streamlit secrets.")
    genai.configure(api_key=key)
    
    fallbacks = [model_choice, "gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    seen = set()
    last_err = None
    for m in fallbacks:
        if m in seen:
            continue
        seen.add(m)
        try:
            model = genai.GenerativeModel(m)
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

def run_panel_for_candidate(name, jd, resume, transcript, model_choice, key):
    st.markdown(f"## Candidate {name} Evaluation")
    
    # 1. Candidate Profile Builder
    with st.spinner(f"Step 1: Candidate Profile Builder ({name})..."):
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
        profile = call_gemini(profile_prompt, model_choice, key)

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
                opinion = call_gemini(agent_prompt, model_choice, key)
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
        debate = call_gemini(debate_prompt, model_choice, key)

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
        decision = call_gemini(final_prompt, model_choice, key)

    st.success(f"Final Decision for Candidate {name} Ready")
    st.markdown(decision)
    
    return {"profile": profile, "opinions": opinions, "debate": debate, "decision": decision}

def run_comparison(res_a, res_b, jd, model_choice, key):
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
        comparison = call_gemini(comp_prompt, model_choice, key)
    st.markdown(comparison)

# ----------------- UI Layout ----------------- #

st.title("Multi-Agent AI Interview Panel Simulator")
st.caption("Autonomous hiring panel simulator with blind evaluations, adversarial multi-agent debate, evidence weighting, and candidate comparison.")

tab_inputs, tab_run = st.tabs(["1. Input Documents (Pre-Loaded)", "2. Run Panel Simulation"])

with tab_inputs:
    st.subheader("Job Description")
    jd_upload = st.file_uploader("Upload Job Description PDF (Optional)", type=["pdf"], key="jd_up")
    jd_val = extract_pdf(jd_upload) or st.text_area("Job Description", value=st.session_state.get("jd_text", ""), height=130)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Candidate A")
        ra_up = st.file_uploader("Resume A PDF (Optional)", type=["pdf"], key="ra_up")
        ra_val = extract_pdf(ra_up) or st.text_area("Resume A", value=st.session_state.get("ra_text", ""), height=110)
        
        ta_up = st.file_uploader("Transcript A PDF (Optional)", type=["pdf"], key="ta_up")
        ta_val = extract_pdf(ta_up) or st.text_area("Transcript A", value=st.session_state.get("ta_text", ""), height=130)

    with col_b:
        st.subheader("Candidate B")
        rb_up = st.file_uploader("Resume B PDF (Optional)", type=["pdf"], key="rb_up")
        rb_val = extract_pdf(rb_up) or st.text_area("Resume B", value=st.session_state.get("rb_text", ""), height=110)
        
        tb_up = st.file_uploader("Transcript B PDF (Optional)", type=["pdf"], key="tb_up")
        tb_val = extract_pdf(tb_up) or st.text_area("Transcript B", value=st.session_state.get("tb_text", ""), height=130)

with tab_run:
    st.subheader("Execute Multi-Agent Panel")
    if st.button("Start Multi-Agent Panel Evaluation (Candidates A & B)", type="primary", use_container_width=True):
        if not api_key:
            st.error("Please enter a Gemini API Key in the sidebar or set GEMINI_API_KEY in Streamlit Secrets.")
        elif not jd_val or not ra_val or not ta_val:
            st.error("Please ensure Job Description and Candidate A documents are provided.")
        else:
            try:
                res_a = run_panel_for_candidate("A", jd_val, ra_val, ta_val, model_name, api_key)
                st.markdown("---")
                if rb_val and tb_val:
                    res_b = run_panel_for_candidate("B", jd_val, rb_val, tb_val, model_name, api_key)
                    st.markdown("---")
                    run_comparison(res_a, res_b, jd_val, model_name, api_key)
                st.balloons()
                st.success("Full Multi-Agent Panel Evaluation Complete!")
            except Exception as e:
                st.error(f"Error running panel: {e}")
