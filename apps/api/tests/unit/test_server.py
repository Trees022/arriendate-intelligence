import asyncio

from app import server


def test_windows_server_uses_selector_event_loop(monkeypatch) -> None:
    monkeypatch.setattr(server.sys, "platform", "win32")

    loop = server.compatible_event_loop()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()
