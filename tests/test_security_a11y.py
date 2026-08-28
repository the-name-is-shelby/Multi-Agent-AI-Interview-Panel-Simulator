import pytest
from pathlib import Path
from app import sanitize_input, MAX_INPUT_CHARS

def test_sanitize_input_empty():
    """Test sanitization on None or empty string."""
    assert sanitize_input(None) == ""
    assert sanitize_input("") == ""
    assert sanitize_input("   ") == ""

def test_sanitize_input_length_boundary():
    """Ensure inputs exceeding MAX_INPUT_CHARS are safely truncated."""
    long_input = "A" * (MAX_INPUT_CHARS + 500)
    sanitized = sanitize_input(long_input)
    assert len(sanitized) == MAX_INPUT_CHARS
    assert sanitized == "A" * MAX_INPUT_CHARS

def test_sanitize_input_normal():
    """Verify normal text passes through sanitized."""
    text = "Valid software engineering resume."
    assert sanitize_input(text) == text

def test_env_file_security():
    """Verify that sensitive environment files are excluded from tracking."""
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")
    assert ".env" in content
    assert "secrets.toml" in content
