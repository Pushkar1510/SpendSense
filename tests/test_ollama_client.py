import httpx

from app.services import ollama_client


def test_is_up_true(monkeypatch):
    def fake_get(url, timeout=0.5):
        req = httpx.Request("GET", url)
        return httpx.Response(200, request=req)

    monkeypatch.setattr(ollama_client.httpx, "get", fake_get)
    assert ollama_client.is_up() is True


def test_is_up_false(monkeypatch):
    def fake_get(url, timeout=0.5):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(ollama_client.httpx, "get", fake_get)
    assert ollama_client.is_up() is False
