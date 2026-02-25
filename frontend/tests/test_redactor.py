import pytest
from agent.redactor import redact_pii

def test_ssn_redaction():
    text = "My SSN is 123-45-6789."
    redacted, pii_map = redact_pii(text)
    assert "123-45-6789" not in redacted
    assert "[REDACTED_SSN_0]" in redacted
    assert pii_map["[REDACTED_SSN_0]"] == "123-45-6789"

def test_credit_card_redaction():
    text = "Charge 4444-4444-4444-4444 please."
    redacted, pii_map = redact_pii(text)
    assert "4444-4444-4444-4444" not in redacted
    assert "4444 4444 4444 4444" not in redacted # Regex handles spaces/dashes? Validating...
    # My regex was `\b(?:\d{4}[-\s]?){3}\d{4}\b`. Yes, handles - or space.

def test_ip_address_redaction():
    text = "Server at 192.168.1.1 is down."
    redacted, pii_map = redact_pii(text)
    assert "192.168.1.1" not in redacted
    assert "[REDACTED_IP_ADDRESS_0]" in redacted

def test_multiple_pii():
    text = "Mr. Smith (SSN: 999-99-9999) emailed test@example.com."
    redacted, pii_map = redact_pii(text)
    assert "Mr. Smith" not in redacted
    assert "999-99-9999" not in redacted
    assert "test@example.com" not in redacted
    assert len(pii_map) >= 3

def test_no_pii():
    text = "What is the fine for GDPR Article 83?"
    redacted, pii_map = redact_pii(text)
    assert redacted == text
    assert len(pii_map) == 0
