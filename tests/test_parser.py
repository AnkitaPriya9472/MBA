"""Unit tests for ResponseParser.

Story 20: Test the parser's JSON extraction, validation, and coercion logic.
"""

import pytest
import json

from agents.parser import ResponseParser, ParseError, CompanyResponse
from models.agent_types import CompanyAction


def test_valid_json_parses_correctly():
    """Valid JSON should parse to CompanyResponse correctly."""
    parser = ResponseParser()
    
    valid_json = {
        "action_id": "export_diversion",
        "reasoning": "US tariffs make diversion necessary to maintain revenue streams.",
        "public_signal": "Announcing reallocation to ASEAN markets.",
        "private_signal": "Will also explore joint ventures in EU quietly.",
        "confidence": 0.75,
        "target_markets": ["TH", "VN", "SG"],
        "capex_commitment_usd_mn": 100.0,
        "lobby_target": None,
        "lobby_amount_usd_mn": 0.0
    }
    
    agent_state = {"cash_usd_mn": 2000.0}
    available_actions = [action.value for action in CompanyAction]
    
    result = parser.parse(
        json.dumps(valid_json),
        "company",
        agent_state,
        available_actions,
        attempt=0
    )
    
    assert isinstance(result, CompanyResponse)
    assert result.action_id == "export_diversion"
    assert result.confidence == 0.75
    assert result.target_markets == ["TH", "VN", "SG"]


def test_json_in_code_fences_is_extracted():
    """JSON wrapped in markdown fences should be extracted and parsed."""
    parser = ResponseParser()
    
    raw_with_fences = """```json
{
    "action_id": "export_diversion",
    "reasoning": "This is a test with fences around the JSON payload.",
    "public_signal": "Announcing export strategy shift.",
    "private_signal": "Internal memo only.",
    "confidence": 0.80,
    "target_markets": ["EU"],
    "capex_commitment_usd_mn": 50.0
}
```"""
    
    agent_state = {"cash_usd_mn": 2000.0}
    available_actions = [action.value for action in CompanyAction]
    
    result = parser.parse(
        raw_with_fences,
        "company",
        agent_state,
        available_actions,
        attempt=0
    )
    
    assert isinstance(result, CompanyResponse)
    assert result.action_id == "export_diversion"


def test_unknown_action_coerced_via_difflib():
    """Unknown action should be coerced to closest valid action."""
    parser = ResponseParser()
    
    # "export_diversification" should fuzzy match to "export_diversion"
    json_data = {
        "action_id": "export_diversification",  # Typo
        "reasoning": "Diversifying markets away from US due to tariff shock.",
        "public_signal": "Pivoting export strategy.",
        "private_signal": "Board approved EU expansion.",
        "confidence": 0.70,
        "target_markets": ["EU"],
        "capex_commitment_usd_mn": 0.0
    }
    
    agent_state = {"cash_usd_mn": 2000.0}
    available_actions = [action.value for action in CompanyAction]
    
    result = parser.parse(
        json.dumps(json_data),
        "company",
        agent_state,
        available_actions,
        attempt=0
    )
    
    # Should be corrected to "export_diversion"
    assert result.action_id == "export_diversion"


def test_completely_invalid_json_raises_parse_error():
    """Completely invalid JSON should raise ParseError."""
    parser = ResponseParser()
    
    invalid_raw = "This is not JSON at all, just plain text."
    
    agent_state = {"cash_usd_mn": 2000.0}
    available_actions = [action.value for action in CompanyAction]
    
    with pytest.raises(ParseError) as exc_info:
        parser.parse(
            invalid_raw,
            "company",
            agent_state,
            available_actions,
            attempt=0
        )
    
    assert "No JSON object found" in str(exc_info.value) or "Invalid JSON" in str(exc_info.value)


def test_confidence_below_zero_clamped():
    """Confidence < 0.0 should be clamped to 0.0."""
    parser = ResponseParser()
    
    json_data = {
        "action_id": "wait_and_observe",
        "reasoning": "Holding position due to high uncertainty in market conditions.",
        "public_signal": "Monitoring situation closely.",
        "private_signal": "Internal risk assessment pending.",
        "confidence": -0.2,  # Invalid
        "target_markets": [],
        "capex_commitment_usd_mn": 0.0
    }
    
    agent_state = {"cash_usd_mn": 2000.0}
    available_actions = [action.value for action in CompanyAction]
    
    result = parser.parse(
        json.dumps(json_data),
        "company",
        agent_state,
        available_actions,
        attempt=0
    )
    
    # Should be clamped to 0.0
    assert result.confidence == 0.0


def test_confidence_above_one_clamped():
    """Confidence > 1.0 should be clamped to 1.0."""
    parser = ResponseParser()
    
    json_data = {
        "action_id": "price_war",
        "reasoning": "Aggressive market capture strategy based on strong cash position.",
        "public_signal": "Launching promotional pricing campaign.",
        "private_signal": "Targeting competitor market share directly.",
        "confidence": 1.5,  # Invalid
        "target_markets": ["IN"],
        "capex_commitment_usd_mn": 0.0
    }
    
    agent_state = {"cash_usd_mn": 2000.0}
    available_actions = [action.value for action in CompanyAction]
    
    result = parser.parse(
        json.dumps(json_data),
        "company",
        agent_state,
        available_actions,
        attempt=0
    )
    
    # Should be clamped to 1.0
    assert result.confidence == 1.0


def test_long_assessment_truncated():
    """Assessment over 800 chars should be truncated."""
    parser = ResponseParser()
    
    long_reasoning = "A" * 900  # 900 characters
    
    json_data = {
        "action_id": "export_diversion",
        "reasoning": long_reasoning,
        "public_signal": "Market shift announcement.",
        "private_signal": "Internal only.",
        "confidence": 0.65,
        "target_markets": ["EU"],
        "capex_commitment_usd_mn": 0.0
    }
    
    agent_state = {"cash_usd_mn": 2000.0}
    available_actions = [action.value for action in CompanyAction]
    
    result = parser.parse(
        json.dumps(json_data),
        "company",
        agent_state,
        available_actions,
        attempt=0
    )
    
    # Should be truncated to 800 chars with "..."
    assert len(result.reasoning) <= 800
    assert result.reasoning.endswith("...")


def test_company_capex_exceeds_cash_raises_error():
    """Company capex + lobby > 80% cash should raise ParseError."""
    parser = ResponseParser()
    
    json_data = {
        "action_id": "fdi",
        "reasoning": "Large FDI commitment in EU operations.",
        "public_signal": "Announcing major investment.",
        "private_signal": "Board approved.",
        "confidence": 0.80,
        "target_markets": ["EU"],
        "capex_commitment_usd_mn": 1500.0,  # 75% of cash
        "lobby_amount_usd_mn": 200.0  # Total = 85% > 80%
    }
    
    agent_state = {"cash_usd_mn": 2000.0}
    available_actions = [action.value for action in CompanyAction]
    
    with pytest.raises(ParseError) as exc_info:
        parser.parse(
            json.dumps(json_data),
            "company",
            agent_state,
            available_actions,
            attempt=0
        )
    
    assert "exceeds 80%" in str(exc_info.value) or "cash" in str(exc_info.value).lower()
