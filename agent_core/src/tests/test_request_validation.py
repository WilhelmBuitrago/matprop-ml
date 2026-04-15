import pytest
from pydantic import ValidationError

from api.v4.scheme import CompletionRequestV4


def test_rejects_blank_query():
    with pytest.raises(ValidationError):
        CompletionRequestV4(query="   ")


def test_rejects_query_too_long():
    with pytest.raises(ValidationError):
        CompletionRequestV4(query="a" * 10001)


def test_accepts_and_strips_valid_query():
    request = CompletionRequestV4(query="   find Si band gap   ")
    assert request.query == "find Si band gap"


def test_rejects_max_tokens_below_lower_bound():
    with pytest.raises(ValidationError):
        CompletionRequestV4(query="find silicon", max_tokens_for_response=16)


def test_rejects_temperature_above_upper_bound():
    with pytest.raises(ValidationError):
        CompletionRequestV4(query="find silicon", temperature=2.5)
