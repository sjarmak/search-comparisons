"""
Tests for the QueryAgent class.

This module contains tests for the QueryAgent class which is responsible
for transforming user queries based on inferred intent.
"""
import pytest
import typing
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from app.services.llm.agent import QueryAgent
from app.services.llm.llm_service import LLMService

if typing.TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def mock_llm_service(mocker: "MockerFixture") -> MagicMock:
    """
    Create a mock LLM service for testing.
    
    Args:
        mocker: Pytest mocker fixture
        
    Returns:
        MagicMock: Mocked LLM service
    """
    mock_service = mocker.Mock(spec=LLMService)
    mock_service.interpret_query.return_value = {
        "original_query": "test query",
        "intent": "test_intent",
        "intent_confidence": 0.8,
        "transformed_query": "transformed test query",
        "explanation": "Test explanation"
    }
    mock_service.health_check.return_value = {
        "status": "ok",
        "provider": "test",
        "model": "test-model",
        "message": "LLM service is operational"
    }
    return mock_service


def test_query_agent_initialization() -> None:
    """Test that QueryAgent initializes correctly with default configuration."""
    with patch.object(LLMService, 'from_config') as mock_from_config:
        mock_llm = MagicMock()
        mock_from_config.return_value = mock_llm
        
        agent = QueryAgent()
        
        assert agent.llm_service is mock_llm
        mock_from_config.assert_called_once()


def test_transform_query_with_empty_query() -> None:
    """Test that transform_query handles empty queries correctly."""
    agent = QueryAgent(llm_service=MagicMock())
    
    result = agent.transform_query("")
    
    assert result["intent"] == "empty"
    assert result["intent_confidence"] == 1.0
    assert result["transformed_query"] == ""
    assert "Empty query" in result["explanation"]


def test_transform_query_with_rule_based_match(mocker: "MockerFixture") -> None:
    """Test that transform_query uses rule-based transformation when confident."""
    agent = QueryAgent(llm_service=MagicMock())
    
    # Mock the rule-based transformation to return a confident result
    mock_rule_result = {
        "original_query": "recent papers on black holes",
        "intent": "recent",
        "intent_confidence": 0.9,
        "transformed_query": "black holes year:2023-2024",
        "explanation": "Test explanation"
    }
    mocker.patch.object(
        agent, '_apply_rule_based_transformation', 
        return_value=mock_rule_result
    )
    
    result = agent.transform_query("recent papers on black holes")
    
    assert result == mock_rule_result
    agent.llm_service.interpret_query.assert_not_called()


def test_transform_query_with_llm_when_no_rule_match(
    mock_llm_service: MagicMock, mocker: "MockerFixture"
) -> None:
    """Test that transform_query uses LLM when no rule-based match is confident."""
    agent = QueryAgent(llm_service=mock_llm_service)
    
    # Mock the rule-based transformation to return None (no match)
    mocker.patch.object(
        agent, '_apply_rule_based_transformation', 
        return_value=None
    )
    
    # Mock the enhance_llm_result to just return the input
    mocker.patch.object(
        agent, '_enhance_llm_result', 
        side_effect=lambda x: x
    )
    
    test_query = "papers about black holes"
    result = agent.transform_query(test_query)
    
    mock_llm_service.interpret_query.assert_called_once_with(test_query)
    assert result == mock_llm_service.interpret_query.return_value


def test_analyze_query_complexity() -> None:
    """Test that analyze_query_complexity returns correct analysis for different queries."""
    agent = QueryAgent(llm_service=MagicMock())
    
    # Test a simple query
    simple_query = "black holes"
    simple_result = agent.analyze_query_complexity(simple_query)
    assert simple_result["complexity_level"] == "basic"
    
    # Test a more complex query
    complex_query = 'author:"Smith, J" AND year:2020-2022 AND title:"black hole*"'
    complex_result = agent.analyze_query_complexity(complex_query)
    assert complex_result["complexity_level"] in ["intermediate", "advanced"]
    assert complex_result["field_count"] >= 2
    assert complex_result["has_wildcards"] is True


def test_suggest_improvements() -> None:
    """Test that suggest_improvements returns appropriate suggestions."""
    agent = QueryAgent(llm_service=MagicMock())
    
    # Test query that could use improvements
    query = "black holes recent"
    suggestions = agent.suggest_improvements(query)
    
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    for suggestion in suggestions:
        assert "type" in suggestion
        assert "description" in suggestion 