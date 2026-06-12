from core.schemas import APIResponse, ErrorResponse, PaginatedResponse, PaginationMeta


def test_api_response_model() -> None:
    response = APIResponse(message="ok", data={"id": 1})

    assert response.success is True
    assert response.data == {"id": 1}


def test_error_response_model() -> None:
    response = ErrorResponse(message="failed", code="TEST_ERROR")

    dumped = response.model_dump()
    assert dumped["success"] is False
    assert dumped["code"] == "TEST_ERROR"


def test_paginated_response_model() -> None:
    response = PaginatedResponse(
        data=[{"id": 1}],
        meta=PaginationMeta(page=1, page_size=10, total_items=1, total_pages=1),
    )

    assert len(response.data) == 1
    assert response.meta.total_items == 1


def test_response_check_endpoint(client) -> None:
    response = client.get("/response-check")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["value"] == 1
