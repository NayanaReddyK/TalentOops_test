# Testing Guide

## Overview

TalentOps has a comprehensive test suite covering configuration, agents, services, and models.

## Test Structure

```
app/tests/
├── __init__.py
├── config.py                  # Configuration tests
├── models.py                  # Pydantic model tests
├── test_suite.py              # Comprehensive test suite
└── agents/
    ├── __init__.py
    ├── test_manager_agent.py  # Manager Agent tests
    ├── test_interviewer_fsm.py # Interviewer FSM tests
    └── test_scorecard_agent.py # Scorecard Agent tests
└── services/
    └── __init__.py
        └── test_voice_chain.py # Voice Chain tests
```

## Installation

Install testing dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest app/tests/ -v
```

### Run Specific Test File

```bash
pytest app/tests/config.py -v
```

### Run Specific Test Class

```bash
pytest app/tests/test_suite.py::TestConfigurationSystem -v
```

### Run Specific Test Method

```bash
pytest app/tests/test_suite.py::TestConfigurationSystem::test_settings_loads_all_environment_variables -v
```

### Run with Coverage

```bash
pytest app/tests/ --cov=app --cov-report=html --cov-report=term
```

### Run Tests in Parallel

```bash
pytest app/tests/ -n auto
```

## Test Categories

### 1. Configuration Tests (`app/tests/config.py`)

Tests for the Settings class:
- Default values
- CORS origins parsing
- Offline mode detection
- Type validation
- Property methods

### 2. Model Tests (`app/tests/models.py`)

Tests for Pydantic schemas:
- Envelope validation
- Voice ownership enforcement
- Competency scores
- Scorecard results
- Escalation payloads

### 3. Agent Tests

#### Manager Agent (`app/tests/agents/test_manager_agent.py`)

- Escalation rules validation
- Scheduling conflict handling
- Sourcing cycle management
- Email notification tests

#### Interviewer FSM (`app/tests/agents/test_interviewer_fsm.py`)

- State transitions
- State cues
- State sequence validation
- Custom threshold handling

#### Scorecard Agent (`app/tests/agents/test_scorecard_agent.py`)

- Extractive evaluation
- Quote parsing
- OpenRouter/Groq fallback
- Retry logic
- Minimum quote length validation

### 4. Service Tests (`app/tests/services/test_voice_chain.py`)

- Consent management
- Call gating
- Timestamp handling
- Consent flow validation

### 5. Comprehensive Test Suite (`app/tests/test_suite.py`)

Complete integration tests covering:
- Configuration system
- CORS security
- Manager Agent flow
- Interviewer FSM
- Voice Chain
- Envelope validation
- Data models

## Test Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| Configuration | 90% |
| Agents | 85% |
| Services | 80% |
| Models | 95% |
| Overall | 85% |

## Mocking Strategy

Tests use mocking to isolate components:

```python
from unittest.mock import AsyncMock, MagicMock, patch

mock_db = AsyncMock()
monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_db)
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest app/tests/ --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Test Best Practices

1. **Use descriptive test names**: `test_function_description_when_condition`
2. **Test one behavior per test**: Keep tests focused
3. **Use fixtures**: Avoid code duplication
4. **Mock external dependencies**: Isolate unit tests
5. **Keep tests fast**: Avoid slow operations in tests
6. **Check coverage**: Maintain high test coverage

## Writing New Tests

When adding new functionality:

1. Create test file in appropriate directory
2. Follow naming convention: `test_*.py`
3. Use descriptive test method names
4. Include clear docstrings
5. Use fixtures for common setup
6. Mock external dependencies
7. Test both happy and error paths

### Example Test Template

```python
import pytest
from app.your_module import YourClass


class TestYourClass:
    """Test cases for YourClass."""

    def test_feature_works(self, monkeypatch):
        """Test that the feature works correctly."""
        # Setup
        mock_dependency = AsyncMock()
        monkeypatch.setattr("app.your_module.dependency", mock_dependency)

        # Act
        result = YourClass.method()

        # Assert
        assert result == expected
        mock_dependency.assert_called_once()
```

## Debugging Tests

### Run with Print Statements

```bash
pytest app/tests/test_suite.py -v -s
```

### Run Specific Test with Details

```bash
pytest app/tests/test_suite.py::TestConfigurationSystem::test_settings_validation -vv
```

### Profile Test Performance

```bash
pytest app/tests/ -v --tb=short
```

## Troubleshooting

### Import Errors

If you encounter import errors:

```bash
export PYTHONPATH=/Users/apple/TalentOops:$PYTHONPATH
pytest app/tests/
```

### Mock Issues

If mock objects aren't working correctly:

```python
# Check if mock was called
mock_function.assert_called()
mock_function.assert_called_with(expected_args)

# Print mock call details
print(mock_function.call_args)
```

### Test Data Issues

Use test fixtures for consistent test data:

```python
@pytest.fixture
def sample_transcript():
    return "Sample transcript with valid JSON quotes"
```

## Updating Test Suite

When making code changes:

1. Update existing tests if behavior changed
2. Add tests for new features
3. Run full test suite: `pytest app/tests/ -v`
4. Check coverage report: `pytest app/tests/ --cov=app`
5. Update this documentation if needed