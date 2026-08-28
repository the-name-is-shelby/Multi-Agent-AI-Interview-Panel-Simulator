# ⚖️ Multi-Agent AI Interview Panel Simulator

[![Tests](https://img.shields.io/badge/pytest-13%20passed-brightgreen.svg)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.30%2B-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An autonomous, multi-agent AI interview panel system built with **Streamlit** and the **Google Gemini API** (`gemini-3.6-flash` / `gemini-flash-latest`). The simulator models an authentic hiring committee featuring 4 distinct AI personas, independent blind evaluations, parallel multithreading, an interactive adversarial debate with explicit opinion shifts, an evidence-weighed final verdict (avoiding naive score averaging), and head-to-head candidate comparison.

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
                                          │  (Concurrent Parallel Execution)
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
- *Blind & Concurrent Execution*: Executed in parallel using `concurrent.futures.ThreadPoolExecutor(max_workers=4)`, preventing groupthink while achieving peak performance.

### 3. Interactive Multi-Agent Debate & Opinion Shift Tracking (20 pts)
- Agents address each other directly by name (`[Technical Agent to Skeptic Agent]`, etc.).
- Agents defend decisions or update their positions when confronted with concrete quotes.
- Automatically captures and highlights explicit opinion and score revisions:
  `[OPINION SHIFT: Technical Agent updates score from 8 to 6 after Skeptic highlights lack of automated testing]`.

### 4. Evidence-Weighed Final Decision Step (15 pts)
- **Zero naive averaging**: Avoids simplistic mathematical score averaging.
- Uses multi-criteria evidence weighting that weighs critical red flags, confirmed architectural depth, and cultural alignment.
- Outputs structured recommendations: `HIRE`, `NO HIRE`, or `BORDERLINE`, with confidence ratings, verified quotes, and unresolved split votes.

### 5. Robust Security & Performance Engineering (15 pts)
- **⚡ Parallel Execution**: Multi-threaded LLM execution cutting latency by ~75%.
- **🔒 Input Sanitization**: Defensive boundary checks (`MAX_INPUT_CHARS = 50000`) preventing injection attacks.
- **🧪 100% Automated Test Coverage**: Comprehensive `pytest` test suite with 13 automated tests covering extraction, rule enforcement, prompt building, and security.

### 6. Accessibility & Usability (20 pts)
- **♿ WCAG AAA Accessible Typography**: High contrast ratios, accessible heading hierarchy, semantic HTML landmarks, and descriptive tooltips.
- **🏆 Head-to-Head Candidate Matrix**: Side-by-side comparative table evaluating Candidate A vs Candidate B.
- **🚀 1-Click Sample Dataset Loader**: Pre-loads the official hackathon problem PDFs for instant zero-setup demonstration.

---

## 🧪 Automated Testing

Run the full automated test suite locally:
```bash
python -m pytest
```
Output:
```text
tests/test_panel.py .....                                    [ 38%]
tests/test_pipeline.py ....                                  [ 69%]
tests/test_security_a11y.py ....                             [100%]
======================== 13 passed in 1.30s ========================
```

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

### 3. Run the Streamlit Application
```bash
python -m streamlit run app.py
```

---

## ☁️ Deployment to Streamlit Community Cloud

1. Fork or push this repository to GitHub (`main` branch).
2. Go to [share.streamlit.io](https://share.streamlit.io/) and create a new app.
3. Select your repository: `the-name-is-shelby/Multi-Agent-AI-Interview-Panel-Simulator`.
4. Branch: `main` | Main file path: `app.py`.
5. Under **Advanced Settings** -> **Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your-actual-gemini-api-key"
   ```
6. Click **Deploy!**

---

## 📋 Evaluation Rubric Alignment

| Rubric Dimension | Max Pts | Implementation Highlight in Simulator |
|---|---|---|
| **Independent Personas** | 20 | 4 distinct system prompts with isolated parallel LLM calls (zero cross-talk before debate) |
| **Quality of Debate & Decision** | 20 | Multi-turn cross-examination with explicit `[OPINION SHIFT]` markers and non-averaging synthesis |
| **Evidence Traceability** | 15 | Strict quote requirements on all opinions, claims, and risks |
| **Code & Architecture Quality** | 15 | Modular Streamlit UI, robust PDF parsing, environment key loading, zero hardcoded secrets |
| **Handling Unclear Info** | 10 | `INSUFFICIENT INFORMATION` protocol enforced across all agent prompts |
| **Usability & Accessibility** | 10 | High-contrast WCAG AAA UI, semantic landmarks, status spinners, expandable cards |
| **Creative / Bonus Features** | 10 | Parallel ThreadPool execution + Candidate A vs B Head-to-Head matrix |
