def test_app_exception_handler(client) -> None:
    response = client.get("/raise-not-found")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "NOT_FOUND"
    assert body["message"] == "Item not found"
