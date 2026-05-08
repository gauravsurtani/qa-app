import os
import socket
import subprocess
import time
from pathlib import Path

import pytest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    port = _free_port()
    db = tmp_path_factory.mktemp("e2e") / "qa.db"
    env = {
        **os.environ,
        "SESSION_SECRET": "x" * 32,
        "SQLITE_PATH": str(db),
        "APP_BASE_URL": f"http://127.0.0.1:{port}",
        "EMAIL_API_KEY": "",
    }
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    deadline = time.time() + 15
    import urllib.request

    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def playwright_instance():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


@pytest.fixture
def browser(playwright_instance):
    br = playwright_instance.chromium.launch()
    yield br
    br.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.set_default_timeout(8000)
    yield pg
