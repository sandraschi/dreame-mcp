"""Map fetch: the object name's key and the model IV.

Offline: the cloud, decoder and renderer are fakes; no robot or map file involved.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import dreame_mcp.client as client_mod
from dreame_mcp.client import DreameHomeClient, _map_aes_iv, _split_object_name


def test_split_object_name_with_key():
    assert _split_object_name("ali_dreame/M/1/1,abcKEY") == ("ali_dreame/M/1/1", "abcKEY")


def test_split_object_name_without_key():
    assert _split_object_name(" ali_dreame/M/1/9 ") == ("ali_dreame/M/1/9", None)


def test_no_iv_without_model():
    assert _map_aes_iv(None) is None
    assert _map_aes_iv("dreame.vacuum.nosuchmodel") is None


def test_iv_for_a_known_model():
    ref = os.environ.get("DREAME_REF_PATH")
    try:
        client_mod._bootstrap_protocol(Path(ref) if ref else None)
    except Exception:
        pytest.skip("reference clone not available")
    client_mod._IV_CACHE.clear()
    assert _map_aes_iv("dreame.vacuum.r2363a")


class FakeDecoder:
    calls: list[tuple] = []

    @classmethod
    def decode_map(cls, raw, version, rotation, iv, key):
        cls.calls.append((raw, version, rotation, iv, key))
        return (SimpleNamespace(segments={1: object()}, robot_position=None, charger_position=None),)


class FakeRenderer:
    def render_map(self, map_data, robot_status, station_status):
        return b"png"


@pytest.fixture
def map_client(monkeypatch):
    c = DreameHomeClient(username="u", password="p", did="42")
    c._protocol = object()
    c._model = "dreame.vacuum.test"
    c._map_renderer = FakeRenderer()
    FakeDecoder.calls = []
    monkeypatch.setattr(client_mod, "_map_decoder_cls", FakeDecoder)
    monkeypatch.setattr(client_mod, "_map_aes_iv", lambda model: "IV" if model == "dreame.vacuum.test" else None)
    monkeypatch.setattr(c, "_safe_call", lambda *a, **k: None)
    return c


def test_live_map_fetched_by_name_and_decrypted_with_key(map_client, monkeypatch):
    fetched = []
    monkeypatch.setattr(map_client, "_resolve_live_map_object_name", lambda: "obj/1,KEY")
    monkeypatch.setattr(map_client, "_fetch_map_bytes_from_cloud_url", lambda name: fetched.append(name) or b"RAWMAP")
    result = map_client._get_map_sync()
    assert fetched == ["obj/1"]
    assert FakeDecoder.calls == [("RAWMAP", 1, 0, "IV", "KEY")]
    assert result["success"]
    assert result["object_name"] == "obj/1"
    assert result["map_data"]["rooms"] == 1
