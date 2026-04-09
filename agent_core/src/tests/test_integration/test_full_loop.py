from api.v4.scheme import CompletionRequestV4


def test_full_loop_chat_returns_response_and_metadata(make_service):
    service = make_service()

    response = service.chat(
        CompletionRequestV4(
            query="find material mp-149 and provide key properties",
            max_iterations=4,
            max_tool_calls=4,
        )
    )

    assert response.id
    assert response.choices
    assert isinstance(response.choices[0]["text"], str)
    assert response.metadata["stop_reason"]
    assert response.metadata["iterations_count"] >= 1


def test_streaming_emits_start_and_final_events(make_service):
    service = make_service()
    events = list(
        service.stream_chat_events(
            CompletionRequestV4(query="search papers for silicon", stream=True)
        )
    )

    assert any(e.startswith("event: start") for e in events)
    assert any(e.startswith("event: final") for e in events)
