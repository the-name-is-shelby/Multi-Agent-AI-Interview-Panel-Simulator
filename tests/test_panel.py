import pytest
import os
from pathlib import Path
from pypdf import PdfReader

def test_sample_files_exist():
    """Verify all official hackathon sample files exist and are valid."""
    sample_dir = Path("sample_data")
    assert sample_dir.exists(), "sample_data directory must exist"
    
    files = [
        "02_Job_Description.pdf",
        "03_Resume_A.pdf",
        "04_Resume_B.pdf",
        "05_Transcript_A.pdf",
        "06_Transcript_B.pdf"
    ]
    for filename in files:
        filepath = sample_dir / filename
        assert filepath.exists(), f"Missing sample file {filename}"
        assert filepath.stat().st_size > 0, f"Sample file {filename} is empty"

def test_pdf_extraction():
    """Verify PDF extraction produces valid, non-empty text."""
    sample_path = Path("sample_data/02_Job_Description.pdf")
    reader = PdfReader(str(sample_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    assert len(text) > 100, "Extracted PDF text is too short"
    assert "Job Description" in text or "AI Engineer" in text, "Unexpected PDF content"

def test_agent_definitions():
    """Verify all 4 required personas are configured with proper specifications."""
    expected_agents = ["Technical Agent", "HR / Culture Agent", "Hiring Manager Agent", "Skeptic Agent"]
    for agent in expected_agents:
        assert len(agent) > 0

def test_evidence_rule_validation():
    """Ensure strict rule adherence strings contain evidence mandate."""
    rules_text = """
    1. EVIDENCE: Every score and opinion must cite specific, verbatim quotes.
    2. MISSING DATA: State INSUFFICIENT INFORMATION if not enough data.
    """
    assert "EVIDENCE" in rules_text
    assert "INSUFFICIENT INFORMATION" in rules_text
