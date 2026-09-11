"""Prove the API key never leaks into logs, exception messages, or tracebacks
on a failed request (mocked 429/500 and network errors)."""

import io
import os
import sys
import traceback
import urllib.error
from contextlib import redirect_stdout

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from pipeline import fetch  # noqa: E402

SECRET = "FAKEtestKEYdeadbeef0123456789abcdef012345"  # fabricated key for the test only


def _assert_clean(text):
    assert SECRET not in text, "API key leaked!"
    # also no api-key=<value> with a real value
    assert "api-key=" + SECRET not in text


def test_redact_replaces_registered_secret():
    fetch._register_secret(SECRET)
    msg = f"boom https://api.data.gov.in/resource/x?api-key={SECRET}&format=json"
    out = fetch._redact(msg)
    _assert_clean(out)
    assert "***" in out


def test_redact_scrubs_apikey_param_even_if_unregistered():
    out = fetch._redact("GET .../resource/x?api-key=UNREGISTERED_SECRET_ABC&offset=0")
    assert "UNREGISTERED_SECRET_ABC" not in out
    assert "api-key=***" in out


def test_http_error_does_not_leak_key(monkeypatch):
    fetch._register_secret(SECRET)
    url = f"https://api.data.gov.in/resource/x?api-key={SECRET}&format=json&offset=0"

    # Force the urllib path (no curl) and raise a 429 HTTPError whose message
    # includes the full URL, as real urllib does.
    import shutil as _sh
    monkeypatch.setattr(_sh, "which", lambda _name: None)

    class _FakeOpen:
        def __enter__(self):
            raise urllib.error.HTTPError(url, 429, f"Too Many Requests {url}", {}, None)

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _FakeOpen().__enter__())

    with pytest.raises(fetch.FetchError) as ei:
        fetch._http_get(url)
    _assert_clean(str(ei.value))
    # traceback must be clean too
    tb = "".join(traceback.format_exception(type(ei.value), ei.value, ei.value.__traceback__))
    _assert_clean(tb)


def test_backoff_failure_message_is_redacted(monkeypatch):
    fetch._register_secret(SECRET)
    url = f"https://api.data.gov.in/resource/x?api-key={SECRET}"

    def _boom(_url):
        raise RuntimeError(f"connection reset for {_url}")

    monkeypatch.setattr(fetch, "_http_get", _boom)
    monkeypatch.setattr(fetch.time, "sleep", lambda *_a: None)

    buf = io.StringIO()
    with redirect_stdout(buf):
        with pytest.raises(fetch.FetchError) as ei:
            fetch._get_with_backoff(url, max_retries=2)

    _assert_clean(str(ei.value))       # raised message
    _assert_clean(buf.getvalue())      # printed logs
