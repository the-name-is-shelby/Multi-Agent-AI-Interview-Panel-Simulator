import streamlit as st
import google.generativeai as genai
import json
import os
from pathlib import Path
from pypdf import PdfReader
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

# Streamlit Page Config
st.set_page_config(
    page_title="Multi-Agent AI Interview Panel Simulator",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished, hackathon-winning UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .status-banner {
        background: linear-gradient(90deg, #1E293B 0%, #334155 100%);
        color: #F8FAFC;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .agent-box {
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid #E2E8F0;
        background-color: #F8FAFC;
    }
    .badge-hire {
        background-color: #10B981;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .badge-nohire {
        background-color: #EF4444;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .badge-borderline {
        background-color: #F59E0B;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Helper Functions ----------------- #

def load_local_sample(filename):
    path = Path("sample_data") / filename
    if path.exists():
        try:
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception:
            return ""
    return ""

# Auto-initialize session state with official hackathon problem files if not already set
if "initialized_defaults" not in st.session_state:
    st.session_state["jd_text_val"] = load_local_sample("02_Job_Description.pdf")
    st.session_state["ra_text_val"] = load_local_sample("03_Resume_A.pdf")
    st.session_state["ta_text_val"] = load_local_sample("05_Transcript_A.pdf")
    st.session_state["rb_text_val"] = load_local_sample("04_Resume_B.pdf")
    st.session_state["tb_text_val"] = load_local_sample("06_Transcript_B.pdf")
    st.session_state["initialized_defaults"] = True

def get_active_api_key():
    # 1. Streamlit Secrets (Cloud deployment)
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
        if "gemini_api_key" in st.secrets:
            return st.secrets["gemini_api_key"]
    except Exception:
        pass

    # 2. Environment Variables (.env / system)
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("gemini_api_key")
    if env_key:
        return env_key

    # 3. Session state fallback
    return st.session_state.get("custom_api_key", "")

active_api_key = get_active_api_key()

# ----------------- Sidebar Configuration ----------------- #

with st.sidebar:
    st.title("⚙️ Panel Settings")
    
    if active_api_key:
        st.success("🟢 API Connected & Ready", icon="✅")
    else:
        st.warning("⚠️ No API Key found in secrets or environment.", icon="🔑")
    
    # Model Selection with smart defaults
    model_choice = st.selectbox(
        "🧠 Gemini Model",
        options=["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "Custom"],
        index=0,
        help="Primary model used for multi-agent reasoning."
    )
    if model_choice == "Custom":
        selected_model = st.text_input("Custom Model Name", value="gemini-2.5-flash")
    else:
        selected_model = model_choice

    # Optional Override Collapsible
    with st.expander("🔑 Override API Key (Optional)", expanded=not bool(active_api_key)):
        custom_key_input = st.text_input(
            "Custom Gemini API Key",
            value=st.session_state.get("custom_api_key", ""),
            type="password",
            help="Leave blank to use pre-configured Cloud Secret / Environment Key."
        )
        if custom_key_input:
            st.session_state["custom_api_key"] = custom_key_input
            active_api_key = custom_key_input

    st.divider()
    st.markdown("### 📂 Sample Data Controls")
    if st.button("🔄 Reset / Reload Hackathon Dataset", use_container_width=True):
        st.session_state["jd_text_val"] = load_local_sample("02_Job_Description.pdf")
        st.session_state["ra_text_val"] = load_local_sample("03_Resume_A.pdf")
        st.session_state["ta_text_val"] = load_local_sample("05_Transcript_A.pdf")
        st.session_state["rb_text_val"] = load_local_sample("04_Resume_B.pdf")
        st.session_state["tb_text_val"] = load_local_sample("06_Transcript_B.pdf")
        st.toast("Reloaded official sample dataset!", icon="🚀")

# ----------------- Robust LLM Caller ----------------- #

def call_gemini(prompt: str, model_name: str, api_key: str) -> str:
    if not api_key:
        raise ValueError("No Gemini API Key found. Please add GEMINI_API_KEY to Streamlit Secrets or provide it in the sidebar.")
    
    genai.configure(api_key=api_key)
    
    # Try preferred model first, with seamless fallback if model is unavailable
    models_to_try = [model_name]
    for fallback in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]:
        if fallback not in models_to_try:
            models_to_try.append(fallback)
            
    last_err = None
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_err = e
            continue
            
    raise RuntimeError(f"Failed to generate response: {last_err}")

# Extract text from uploaded PDF
def extract_pdf_text(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

# ----------------- Persona Definitions ----------------- #

AGENTS = {
    "Technical Agent": {
        "role": "Chief Systems Architect / Senior AI Engineer",
        "focus": "Evaluates technical depth, concurrency, agentic workflows, production reliability, error-handling, and code rigor.",
        "icon": "💻"
    },
    "HR / Culture Agent": {
        "role": "Head of People & Organizational Culture",
        "focus": "Evaluates communication clarity, teamwork, honesty, self-awareness, handling pressure, and values alignment.",
        "icon": "🤝"
    },
    "Hiring Manager Agent": {
        "role": "VP of Engineering & Freight Ops Lead",
        "focus": "Evaluates business ROI, role fit against job description requirements, ownership mindset, and delivery velocity.",
        "icon": "📈"
    },
    "Skeptic Agent": {
        "role": "Lead Technical Auditor & Adversarial Reviewer",
        "focus": "Proactively identifies exaggerations, discrepancies between resume and transcript, vague claims, and potential red flags.",
        "icon": "🔍"
    }
}

CORE_RULES = """
EVALUATION RULES (MANDATORY):
1. EVIDENCE MANDATE: Every opinion, claim, and score MUST cite specific, verifiable quotes or facts from the transcript or resume. No vague assertions.
2. MISSING DATA HONESTY: If there is insufficient information to evaluate a specific skill or criterion, explicitly state "INSUFFICIENT INFORMATION" instead of hallucinating or assuming a score.
3. OBJECTIVITY: Base judgments solely on demonstrated competence and concrete statements made during the interview or in the resume.
"""

# Voice Debate Simulation Generator (Web Speech API)
def render_voice_debate_player(debate_text, candidate_name):
    clean_text = debate_text.replace("`", "'").replace('"', '\\"').replace("\n", "\\n")
    html_code = f"""
    <div style="background-color: #1E293B; color: #F8FAFC; padding: 18px; border-radius: 10px; margin-top: 15px; margin-bottom: 20px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
            <h4 style="margin: 0; color: #60A5FA;">🎙️ Live AI Multi-Persona Voice Debate Simulation ({candidate_name})</h4>
            <div>
                <button onclick="playDebate_{candidate_name}()" style="background: #10B981; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-right: 6px;">▶ Play Debate</button>
                <button onclick="stopDebate()" style="background: #EF4444; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600;">⏹ Stop</button>
            </div>
        </div>
        <p style="font-size: 0.85rem; color: #94A3B8; margin: 0;">Click Play to hear the 4 AI agent personas debate using distinct synthesized voice timbres.</p>
        <div id="status_{candidate_name}" style="font-size: 0.85rem; color: #38BDF8; margin-top: 8px; min-height: 20px;"></div>
    </div>
    
    <script>
    function stopDebate() {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
        }}
        var status = document.getElementById('status_{candidate_name}');
        if(status) status.innerText = 'Debate audio stopped.';
    }}

    function playDebate_{candidate_name}() {{
        if (!('speechSynthesis' in window)) {{
            alert('Speech synthesis is not supported in this browser.');
            return;
        }}
        window.speechSynthesis.cancel();
        
        var rawText = "{clean_text}";
        var lines = rawText.split('\\n');
        
        var agentVoiceSettings = {{
            'Technical Agent': {{ pitch: 0.9, rate: 1.05 }},
            'HR / Culture Agent': {{ pitch: 1.25, rate: 0.95 }},
            'Hiring Manager Agent': {{ pitch: 1.0, rate: 1.0 }},
            'Skeptic Agent': {{ pitch: 0.75, rate: 1.1 }}
        }};

        var queue = [];
        for (var i = 0; i < lines.length; i++) {{
            var line = lines[i].trim();
            if (line.length === 0) continue;
            
            var matchedAgent = 'Hiring Manager Agent';
            var textToSpeak = line;
            
            for (var agent in agentVoiceSettings) {{
                if (line.includes(agent) || line.startsWith(agent)) {{
                    matchedAgent = agent;
                    break;
                }}
            }}
            
            var utter = new SpeechSynthesisUtterance(textToSpeak);
            var settings = agentVoiceSettings[matchedAgent] || {{ pitch: 1.0, rate: 1.0 }};
            utter.pitch = settings.pitch;
            utter.rate = settings.rate;
            
            (function(spokenLine, agentName) {{
                utter.onstart = function() {{
                    var status = document.getElementById('status_{candidate_name}');
                    if(status) status.innerText = 'Speaking [' + agentName + ']: ' + spokenLine.substring(0, 80) + '...';
                }};
            }})(line, matchedAgent);
            
            queue.push(utter);
        }}
        
        if (queue.length > 0) {{
            queue[queue.length - 1].onend = function() {{
                var status = document.getElementById('status_{candidate_name}');
                if(status) status.innerText = 'Debate playback completed.';
            }};
            for (var j = 0; j < queue.length; j++) {{
                window.speechSynthesis.speak(queue[j]);
            }}
        }}
    }}
    </script>
    """
    st.components.v1.html(html_code, height=135)

# ----------------- Core Multi-Agent Pipeline ----------------- #

def evaluate_candidate(name: str, job_desc: str, resume: str, transcript: str, model_name: str, api_key: str):
    st.markdown(f"## 👤 Evaluation for Candidate: **{name}**")
    
    # 1. Candidate Profile Builder
    with st.status(f"🛠️ Step 1: Building Candidate Profile for {name}...", expanded=True) as status_profile:
        st.write("Extracting structured competencies, timeline, and verified claims from documents...")
        profile_prompt = f"""
You are the Candidate Profile Builder. Your mission is to extract an objective, structured factual dossier from the candidate's resume and interview transcript against the Job Description.

Job Description:
{job_desc}

Resume:
{resume}

Transcript:
{transcript}

{CORE_RULES}

Extract and present in structured Markdown:
1. **Executive Profile & Career Summary**
2. **Technical & Domain Competencies** (Split into explicitly demonstrated vs merely listed)
3. **Experience & Key Projects Timeline** (Include scale, tech stacks, and team context)
4. **Concrete Claims & Metrics Made** (List specific claims with corresponding quotes from transcript or resume)
5. **Notable Observations or Ambiguities** (Facts that seem vague or require verification)
"""
        profile = call_gemini(profile_prompt, model_name, api_key)
        status_profile.update(label=f"✅ Candidate Profile Built ({name})", state="complete", expanded=False)
    
    with st.expander(f"📋 View Shared Candidate Profile ({name})", expanded=False):
        st.markdown(profile)

    # 2. Independent Blind Agent Reviews (Parallel / Separate Calls)
    st.markdown("### 🏛️ Step 2: Independent Agent Evaluations (Blind & Evidence-Based)")
    st.info("🔒 Each agent evaluates the candidate independently in isolation without seeing other agents' assessments.", icon="ℹ️")
    
    opinions = {}
    cols = st.columns(4)
    
    for idx, (agent_name, agent_meta) in enumerate(AGENTS.items()):
        with cols[idx]:
            st.markdown(f"#### {agent_meta['icon']} {agent_name}")
            with st.spinner(f"{agent_name} analyzing..."):
                agent_prompt = f"""
You are the **{agent_name}** ({agent_meta['role']}).
Your Mission: {agent_meta['focus']}

CRITICAL CONSTRAINT: You are in the INDEPENDENT BLIND EVALUATION stage. You have NOT seen and CANNOT see what other panel agents think. Judge entirely on your own domain perspective.

{CORE_RULES}

Shared Candidate Profile:
{profile}

Job Description:
{job_desc}

Interview Transcript:
{transcript}

Candidate Resume:
{resume}

Please provide your evaluation in the following structure:
1. **Independent Score**: (1-10 or "INSUFFICIENT INFORMATION")
2. **Confidence Level**: (High / Medium / Low)
3. **Primary Assessment & Domain Analysis**:
4. **Key Direct Evidence Quotes**: (Provide verbatim quotes from transcript/resume supporting your judgment)
5. **Strengths Identified**:
6. **Key Risks & Concerns**:
"""
                opinion = call_gemini(agent_prompt, model_name, api_key)
                opinions[agent_name] = opinion
                
            with st.expander(f"View {agent_name} Review", expanded=True):
                st.markdown(opinion)

    # 3. Multi-Agent Debate Step
    st.markdown("### ⚔️ Step 3: Multi-Agent Interactive Debate & Opinion Shifts")
    with st.status(f"💬 Step 3: Simulating Live Panel Debate for Candidate {name}...", expanded=True) as status_debate:
        st.write("Agents are cross-examining points, defending claims, and revising opinions based on peer arguments...")
        
        debate_prompt = f"""
You are orchestrating a live, high-stakes debate between the 4 interview panel agents regarding Candidate {name}.

The agents and their independent initial opinions are:
{json.dumps(opinions, indent=2)}

Job Description:
{job_desc}

DEBATE REQUIREMENTS (CRITICAL):
1. **Direct Interaction**: Agents must talk to each other BY NAME (e.g., "Technical Agent to Skeptic Agent:", "HR / Culture Agent responding to Hiring Manager:").
2. **Real Pushback & Defenses**: At least two agents must challenge another agent's interpretation or point out missed evidence.
3. **Explicit Opinion / Score Shifts**: Show at least one moment where an agent explicitly changes or refines their score/opinion after being convinced by another agent's counter-evidence or quote.
4. **Explicit Marker**: Highlight any opinion shift with a bold tag like:
   `[OPINION SHIFT: <Agent Name> updates score from X to Y because of <reason/quote cited by other agent>]`
5. Format the output as an engaging, authentic dialogue transcript between the personas, followed by a brief "Debate Summary & Consensus Shifts" section.
"""
        debate = call_gemini(debate_prompt, model_name, api_key)
        status_debate.update(label=f"✅ Panel Debate Completed ({name})", state="complete", expanded=False)

    st.markdown(debate)
    
    # Bonus: Audio simulation component
    render_voice_debate_player(debate, name)

    # 4. Final Decision Step (Evidence-Weighed, Non-Averaging)
    st.markdown("### 🎯 Step 4: Evidence-Weighed Final Decision & Executive Report")
    with st.status(f"⚖️ Step 4: Synthesizing Evidence & Weighing Final Decision for {name}...", expanded=True) as status_decision:
        st.write("Applying multi-criteria evidence weighting (not simple score averaging)...")
        
        decision_prompt = f"""
You are the Lead Panel Arbiter. You must produce the Final Panel Recommendation for Candidate {name}.

IMPORTANT RULE: DO NOT simply calculate a mathematical average of the agent scores. Instead, conduct an evidence-weighted reasoning synthesis. Weigh the gravity of the Skeptic's findings, the depth verified by the Technical Agent, the operational value assessed by the Hiring Manager, and the culture/communication indicators from HR.

Candidate Profile:
{profile}

Independent Opinions:
{json.dumps(opinions, indent=2)}

Debate Transcript & Shifts:
{debate}

{CORE_RULES}

Deliver the final executive report with these exact sections:
1. **Final Recommendation**: [HIRE / NO HIRE / BORDERLINE]
2. **Overall Confidence Level**: [High / Medium / Low] (Explain why)
3. **Evidence-Weighed Synthesis**: (Detailed rationale explaining why specific evidence outweighed opposing points)
4. **Top Verified Strengths**: (Include verbatim quote for each)
5. **Critical Concerns & Red Flags**: (Include verbatim quote or noted absence for each)
6. **Unresolved Disagreements Among Agents**: (Highlight lingering tensions between personas that remained split)
7. **Actionable Next Steps / Conditions**: (e.g., reference check on specific claim, technical take-home, or immediate offer)
"""
        final_decision = call_gemini(decision_prompt, model_name, api_key)
        status_decision.update(label=f"✅ Final Decision Ready ({name})", state="complete", expanded=False)

    # Render Final Decision with Badge
    rec_badge = "badge-borderline"
    if "RECOMMENDATION: HIRE" in final_decision.upper() or "**FINAL RECOMMENDATION**: HIRE" in final_decision.upper() or "RECOMMENDATION: [HIRE]" in final_decision.upper():
        rec_badge = "badge-hire"
    elif "NO HIRE" in final_decision.upper():
        rec_badge = "badge-nohire"

    st.markdown(f"""
    <div style="background-color: #FFFFFF; border: 2px solid #E2E8F0; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <h3 style="margin: 0; color: #0F172A;">📊 Executive Panel Verdict: Candidate {name}</h3>
            <span class="{rec_badge}" style="font-size: 1rem;">STATUS EVALUATED</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(final_decision)
    
    return {
        "profile": profile,
        "opinions": opinions,
        "debate": debate,
        "final_decision": final_decision
    }

# Head-to-Head Comparison Matrix Generator
def generate_comparison_matrix(res_a, res_b, job_desc, model_name, api_key):
    st.markdown("---")
    st.markdown("## 🏆 Candidate Comparison: Head-to-Head (Candidate A vs Candidate B)")
    
    with st.status("🧠 Generating Head-to-Head Comparative Synthesis...", expanded=True) as status_comp:
        comp_prompt = f"""
You are the Senior Hiring Committee Chair. You have completed the comprehensive multi-agent panels for both Candidate A and Candidate B for the role described in the Job Description.

Job Description:
{job_desc}

Candidate A Summary & Final Decision:
{res_a['final_decision']}

Candidate B Summary & Final Decision:
{res_b['final_decision']}

Provide a clear Head-to-Head Comparison:
1. **Comparative Matrix Table**: (Columns: Evaluation Dimension, Candidate A, Candidate B, Winner/Edge)
   - Technical Architecture & Production Rigor
   - Communication, Culture & Honesty
   - Execution Speed & Freight Ops Alignment
   - Risk / Red Flag Factor
2. **Key Trade-off Analysis**: (What is the core trade-off between hiring Candidate A vs Candidate B?)
3. **Final Selection Decision**: (Who should receive the offer? Rank 1st and 2nd with decisive justification).
"""
        comparison = call_gemini(comp_prompt, model_name, api_key)
        status_comp.update(label="✅ Head-to-Head Comparison Completed", state="complete", expanded=False)

    st.markdown(comparison)
    return comparison

# ----------------- Main UI Layout ----------------- #

st.markdown('<div class="main-header">🎙️ Multi-Agent AI Interview Panel Simulator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Collaborative multi-persona panel with blind independent reviews, adversarial debate, evidence weighting, and voice simulation.</div>', unsafe_allow_html=True)

# Banner confirming status
if active_api_key:
    st.markdown("""
    <div class="status-banner">
        <div>⚡ <b>Status</b>: System is fully initialized with official hackathon dataset. Ready to evaluate.</div>
        <div><span style="background: #10B981; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">API Ready</span></div>
    </div>
    """, unsafe_allow_html=True)

# Tabs
tab_input, tab_panel = st.tabs(["📝 1. Documents & Candidate Materials", "🤖 2. Multi-Agent Simulation"])

with tab_input:
    st.subheader("1. Job Description")
    col_jd1, col_jd2 = st.columns([1, 2])
    with col_jd1:
        jd_file = st.file_uploader("Upload Custom Job Description PDF", type=["pdf"], key="jd_upload")
    with col_jd2:
        jd_text_default = st.session_state.get("jd_text_val", "")
        jd_text = st.text_area("Job Description Text", value=jd_text_default, height=140, placeholder="Paste or load Job Description text here...", key="jd_input_box")

    st.divider()
    st.subheader("2. Candidate Materials")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 🅰️ Candidate A")
        ra_file = st.file_uploader("Upload Resume A (PDF)", type=["pdf"], key="ra_upload")
        ra_text_default = st.session_state.get("ra_text_val", "")
        ra_text = st.text_area("Resume A Text", value=ra_text_default, height=120, placeholder="Paste Resume A text...", key="ra_input_box")
        
        ta_file = st.file_uploader("Upload Transcript A (PDF)", type=["pdf"], key="ta_upload")
        ta_text_default = st.session_state.get("ta_text_val", "")
        ta_text = st.text_area("Transcript A Text", value=ta_text_default, height=140, placeholder="Paste Transcript A text...", key="ta_input_box")

    with col_b:
        st.markdown("### 🅱️ Candidate B")
        rb_file = st.file_uploader("Upload Resume B (PDF)", type=["pdf"], key="rb_upload")
        rb_text_default = st.session_state.get("rb_text_val", "")
        rb_text = st.text_area("Resume B Text", value=rb_text_default, height=120, placeholder="Paste Resume B text...", key="rb_input_box")
        
        tb_file = st.file_uploader("Upload Transcript B (PDF)", type=["pdf"], key="tb_upload")
        tb_text_default = st.session_state.get("tb_text_val", "")
        tb_text = st.text_area("Transcript B Text", value=tb_text_default, height=140, placeholder="Paste Transcript B text...", key="tb_input_box")

with tab_panel:
    st.subheader("🚀 Live Multi-Agent Simulation")
    st.write("Run the full 4-persona panel, observe the independent blind scoring, listen to the debate, and inspect the final evidence-weighed decisions.")
    
    run_btn = st.button("🔥 Start Multi-Agent Panel Evaluation (Candidates A & B)", type="primary", use_container_width=True)

    if run_btn:
        # Extract materials
        final_jd = extract_pdf_text(jd_file) or jd_text
        final_ra = extract_pdf_text(ra_file) or ra_text
        final_ta = extract_pdf_text(ta_file) or ta_text
        final_rb = extract_pdf_text(rb_file) or rb_text
        final_tb = extract_pdf_text(tb_file) or tb_text

        # Validate inputs
        if not active_api_key:
            st.error("❌ Missing Gemini API Key! Please ensure GEMINI_API_KEY is configured in Streamlit Secrets or in the sidebar.", icon="🚨")
        elif not final_jd:
            st.error("❌ Please provide the Job Description.", icon="🚨")
        elif not (final_ra and final_ta):
            st.error("❌ Please provide Candidate A's Resume and Interview Transcript.", icon="🚨")
        else:
            try:
                # Process Candidate A
                st.markdown("---")
                results_a = evaluate_candidate("A", final_jd, final_ra, final_ta, selected_model, active_api_key)
                st.session_state["results_a"] = results_a
                
                # Process Candidate B if available
                if final_rb and final_tb:
                    st.markdown("---")
                    results_b = evaluate_candidate("B", final_jd, final_rb, final_tb, selected_model, active_api_key)
                    st.session_state["results_b"] = results_b
                    
                    # Generate Head-to-Head Comparison
                    comp_result = generate_comparison_matrix(results_a, results_b, final_jd, selected_model, active_api_key)
                    st.session_state["comparison_result"] = comp_result
                else:
                    st.info("ℹ️ Candidate B materials were not provided. Processed Candidate A only.", icon="📌")
                    
                st.balloons()
                st.success("🎉 Multi-Agent Interview Panel Evaluation Complete!", icon="✨")
                
            except Exception as e:
                st.error(f"❌ An error occurred during evaluation: {str(e)}", icon="💥")
                st.info("Tip: Check your API key, rate limits, or try switching models in the sidebar.")

# Download section if results exist
if "results_a" in st.session_state:
    st.sidebar.divider()
    st.sidebar.subheader("📥 Export Reports")
    export_data = {
        "candidate_a": st.session_state.get("results_a"),
        "candidate_b": st.session_state.get("results_b"),
        "comparison": st.session_state.get("comparison_result")
    }
    st.sidebar.download_button(
        label="Download Full Evaluation JSON",
        data=json.dumps(export_data, indent=2),
        file_name="multi_agent_interview_evaluation.json",
        mime="application/json",
        use_container_width=True
    )
