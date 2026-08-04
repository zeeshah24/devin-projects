from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_list(client: TestClient) -> None:
    created = client.post("/todos", json={"title": "write tests"})
    assert created.status_code == 201
    assert created.json() == {"id": 1, "title": "write tests", "done": False}

    listed = client.get("/todos")
    assert listed.status_code == 200
    assert listed.json() == [{"id": 1, "title": "write tests", "done": False}]


def test_get_todo(client: TestClient) -> None:
    client.post("/todos", json={"title": "read docs"})
    assert client.get("/todos/1").json()["title"] == "read docs"
    assert client.get("/todos/99").status_code == 404


def test_update_todo(client: TestClient) -> None:
    client.post("/todos", json={"title": "ship it"})
    updated = client.patch("/todos/1", json={"done": True})
    assert updated.json() == {"id": 1, "title": "ship it", "done": True}

    renamed = client.patch("/todos/1", json={"title": "ship it twice"})
    assert renamed.json() == {"id": 1, "title": "ship it twice", "done": True}
    assert client.patch("/todos/99", json={"done": True}).status_code == 404


def test_delete_todo(client: TestClient) -> None:
    client.post("/todos", json={"title": "temporary"})
    assert client.delete("/todos/1").status_code == 204
    assert client.get("/todos").json() == []
    assert client.delete("/todos/1").status_code == 404


def test_rejects_empty_title(client: TestClient) -> None:
    assert client.post("/todos", json={"title": ""}).status_code == 422
