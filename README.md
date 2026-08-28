# 🎙️ Multi-Agent AI Interview Panel Simulator

An autonomous, multi-agent AI interview panel system built with **Streamlit** and the **Google Gemini API** (`gemini-2.5-flash` / `gemini-1.5-flash`). The simulator models an authentic hiring committee featuring 4 distinct AI personas, independent blind evaluations, an interactive adversarial debate with explicit opinion shifts, an evidence-weighed final verdict (avoiding naive score averaging), candidate comparison, and interactive multi-voice debate simulation.

---

## 🌟 Key Architecture & Capabilities

```
                       ┌────────────────────────────────────────┐
                       │  Job Description + Resume + Transcript  │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │   1. Candidate Profile Builder         │
                       │   (Structured dossier & verified facts)│
                       └───────────────────┬────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐              ┌──────────────────┐             ┌──────────────────┐
│ Technical Agent  │             │ HR/Culture Agent │              │ Hiring Manager   │             │  Skeptic Agent   │
│ (Depth/Systems)  │             │(Teamwork/Honesty)│              │  (Fit/Impact)    │             │  (Red Flags/Gaps)│
└────────┬─────────┘             └────────┬─────────┘              └────────┬─────────┘             └────────┬─────────┘
         │                                │                                 │                                │
         └────────────────────────────────┼─────────────────────────────────┴────────────────────────────────┘
                                          │
                                          ▼
                       ┌────────────────────────────────────────┐
                       │   2. Multi-Agent Interactive Debate    │
                       │   (Cross-examination & opinion shifts) │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │   3. Evidence-Weighed Synthesis        │
                       │   (Non-averaging reasoned verdict)     │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │   4. Head-to-Head Candidate Comparison │
                       │   (Candidate A vs Candidate B Matrix)  │
                       └────────────────────────────────────────┘
```

### 1. Candidate Profile Builder
Extracts shared factual foundations from candidate resumes and interview transcripts (timeline, core competencies, claimed metrics, and unverified areas).

### 2. Four Independent Blind Agent Personas (20 pts)
- **💻 Technical Agent**: Scrutinizes technical architecture, agentic workflows, scalability, concurrency, code quality, and production rigor.
- **🤝 HR / Culture Agent**: Evaluates communication transparency, honesty, emotional intelligence, stress management, and cultural values.
- **📈 Hiring Manager Agent**: Assesses business ROI, domain fit against the Job Description, ownership mindset, and delivery velocity.
- **🔍 Skeptic Agent**: Red-team auditor that systematically uncovers contradictions between resume claims and transcript statements, exaggerations, and hidden risks.
- *Blind Execution*: Each agent runs in isolation via separate LLM calls, preventing groupthink before the debate.

### 3. Interactive Multi-Agent Debate & Opinion Shift Tracking (20 pts)
- Agents address each other directly by name (`[Technical Agent to Skeptic Agent]`, etc.).
- Agents defend decisions or update their positions when confronted with concrete quotes.
- Automatically captures and highlights explicit opinion and score revisions:
  `[OPINION SHIFT: Technical Agent updates score from 8 to 6 after Skeptic highlights lack of automated testing]`.

### 4. Evidence-Weighed Final Decision Step (15 pts)
- **Zero naive averaging**: Avoids simplistic mathematical score averaging.
- Uses multi-criteria evidence weighting that weighs critical red flags, confirmed architectural depth, and cultural alignment.
- Outputs structured recommendations: `HIRE`, `NO HIRE`, or `BORDERLINE`, with confidence ratings, verified quotes, and unresolved split votes.

### 5. Creative Extras & Usability (20 pts)
- **🎙️ Multi-Voice Audio Debate Simulation**: Web Speech API integration that renders distinct voice pitches and rates for each agent persona with interactive playback.
- **🏆 Head-to-Head Candidate Matrix**: Side-by-side comparative table evaluating Candidate A vs Candidate B.
- **🚀 1-Click Sample Dataset Loader**: Pre-loads the official hackathon problem PDFs for instant zero-setup demonstration.
- **📥 JSON Export**: Full evaluation trace and transcripts exportable with one click.

---

## 🚀 Quick Start (Local)

### 1. Clone the Repository
```bash
git clone https://github.com/the-name-is-shelby/Multi-Agent-AI-Interview-Panel-Simulator.git
cd Multi-Agent-AI-Interview-Panel-Simulator
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Key
Create a `.env` file in the root directory (or use the UI sidebar input):
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```

---

## ☁️ Deployment to Streamlit Community Cloud

1. Fork or push this repository to GitHub (`main` branch).
2. Go to [share.streamlit.io](https://share.streamlit.io/) and create a new app.
3. Select your repository: `Multi-Agent-AI-Interview-Panel-Simulator`.
4. Set Main file path: `app.py`.
5. Under **Advanced Settings** -> **Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your-actual-gemini-api-key"
   ```
6. Click **Deploy!**

---

## 📋 Evaluation Rubric Alignment

| Rubric Dimension | Max Pts | Implementation Highlight in Simulator |
|---|---|---|
| **Independent Personas** | 20 | 4 distinct system prompts with isolated LLM calls (zero cross-talk before debate) |
| **Quality of Debate & Decision** | 20 | Multi-turn cross-examination with explicit `[OPINION SHIFT]` markers and non-averaging synthesis |
| **Evidence Traceability** | 15 | Strict quote requirements on all opinions, claims, and risks |
| **Code & Architecture Quality** | 15 | Modular Streamlit UI, robust PDF parsing, environment key loading, zero hardcoded secrets |
| **Handling Unclear Info** | 10 | `INSUFFICIENT INFORMATION` protocol enforced across all agent prompts |
| **Usability & UX** | 10 | 1-Click sample loader, status containers, expandable cards, badge metrics |
| **Creative / Bonus Features** | 10 | Live multi-voice audio debate player + Candidate A vs B Head-to-Head matrix |

---

## 🔒 Security
- API keys are retrieved securely through `st.secrets`, environment variables, or password-masked sidebar input.
- Secrets and temporary files are strictly ignored via `.gitignore`.
- No API keys are present in source files or git history.
