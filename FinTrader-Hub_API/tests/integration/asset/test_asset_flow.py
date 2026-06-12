import uuid

from fastapi.testclient import TestClient


def _unique_symbol() -> str:
    return f"TST{uuid.uuid4().hex[:6].upper()}"


def _asset_payload(symbol: str | None = None) -> dict:
    return {
        "symbol": symbol or _unique_symbol(),
        "external_id": "bitcoin",
        "name": "Bitcoin",
        "market": "CRYPTO",
        "asset_type": "CRYPTO",
        "currency": "usd",
    }


def _create_asset(
    client: TestClient,
    headers: dict[str, str],
    payload: dict | None = None,
) -> dict:
    response = client.post("/assets", json=payload or _asset_payload(), headers=headers)
    assert response.status_code == 201
    return response.json()["data"]


def test_create_asset_success(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    symbol = _unique_symbol()
    payload = _asset_payload(symbol)
    asset = _create_asset(app_client, auth_headers, payload)

    assert asset["symbol"] == symbol.upper()
    assert asset["name"] == "Bitcoin"
    assert asset["market"] == "CRYPTO"
    assert asset["asset_type"] == "CRYPTO"
    assert asset["currency"] == "USD"
    assert asset["is_active"] is True


def test_create_asset_requires_authentication(app_client: TestClient) -> None:
    response = app_client.post("/assets", json=_asset_payload())

    assert response.status_code == 401


def test_create_asset_duplicate_symbol(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    symbol = _unique_symbol()
    payload = _asset_payload(symbol)
    _create_asset(app_client, auth_headers, payload)

    response = app_client.post("/assets", json=payload, headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "SYMBOL_EXISTS"


def test_update_asset_success(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    created = _create_asset(app_client, auth_headers)

    response = app_client.put(
        f"/assets/{created['id']}",
        json={
            "name": "Bitcoin Updated",
            "currency": "eur",
            "is_active": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    updated = response.json()["data"]
    assert updated["name"] == "Bitcoin Updated"
    assert updated["currency"] == "EUR"


def test_update_asset_requires_authentication(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    created = _create_asset(app_client, auth_headers)

    response = app_client.put(
        f"/assets/{created['id']}",
        json={"name": "Unauthorized Update"},
    )

    assert response.status_code == 401


def test_update_asset_duplicate_symbol(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    first = _create_asset(app_client, auth_headers, _asset_payload(_unique_symbol()))
    second = _create_asset(app_client, auth_headers, _asset_payload(_unique_symbol()))

    response = app_client.put(
        f"/assets/{second['id']}",
        json={"symbol": first["symbol"]},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "SYMBOL_EXISTS"


def test_list_assets_success(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    symbol_a = _unique_symbol()
    symbol_b = _unique_symbol()
    _create_asset(app_client, auth_headers, _asset_payload(symbol_a))
    _create_asset(app_client, auth_headers, {**_asset_payload(symbol_b), "name": "Ethereum"})

    response = app_client.get("/assets")

    assert response.status_code == 200
    assets = response.json()["data"]
    symbols = {asset["symbol"] for asset in assets}
    assert symbol_a in symbols
    assert symbol_b in symbols


def test_search_asset_by_symbol(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    symbol = _unique_symbol()
    _create_asset(app_client, auth_headers, _asset_payload(symbol))

    response = app_client.get("/assets/search", params={"symbol": symbol[:4]})

    assert response.status_code == 200
    results = response.json()["data"]
    assert any(asset["symbol"] == symbol for asset in results)


def test_search_asset_by_name(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    symbol = _unique_symbol()
    _create_asset(
        app_client,
        auth_headers,
        {
            **_asset_payload(symbol),
            "name": "Solana Token",
        },
    )

    response = app_client.get("/assets/search", params={"name": "Solana"})

    assert response.status_code == 200
    results = response.json()["data"]
    assert any(asset["name"] == "Solana Token" for asset in results)


def test_search_asset_requires_parameter(app_client: TestClient) -> None:
    response = app_client.get("/assets/search")

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
