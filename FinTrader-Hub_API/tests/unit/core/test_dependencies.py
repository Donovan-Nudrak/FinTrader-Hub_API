def test_settings_dependency(client) -> None:
    response = client.get("/settings-check")

    assert response.status_code == 200
    assert response.json()["app_name"] == "FinTrader Hub"


def test_database_dependency(client) -> None:
    response = client.get("/db-check")

    assert response.status_code == 200
    assert response.json()["db_dependency"] == "ok"
