import pytest
from services.ai import is_ai

def test_is_ai():
    # Test cases where the username is in the ai_names list
    assert is_ai('ai_easy') == True
    assert is_ai('ai_medium') == True
    assert is_ai('ai_hard') == True

    # Test cases where the username is not in the ai_names list
    assert is_ai('ai_expert') == False
    assert is_ai('user123') == False
    assert is_ai('') == False

if __name__ == '__main__':
    pytest.main()