"""Hermetic tests for release.py (DEP-01) — no git, no network, no real machine state.

The pipeline's end-to-end behaviour is exercised by its --dry-run mode and the journaled
failure-path demonstrations; these tests lock the pure logic a regression could silently
break: the version gate, the registry shape validator (charter A1 — the non-string
installPath is the known poison shape), the atomic registry write, and the tripwire's
derivation from bump_version.py's own config.
"""
import importlib.util
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("release_pipeline", os.path.join(_HERE, "release.py"))
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)


def test_version_regex_accepts_and_rejects():
    assert rp._VERSION_RE.match("1.3.6")
    assert rp._VERSION_RE.match("10.0.99")
    for bad in ("v1.3.6", "1.3", "1.3.6-beta", "1.3.6.7", "", "1.a.3"):
        assert not rp._VERSION_RE.match(bad), bad


def _write_registry(tmp_path, entry):
    p = tmp_path / "installed_plugins.json"
    p.write_text(json.dumps({"plugins": {rp.PLUGIN_KEY: [entry]}}), encoding="utf-8")
    return str(p)


def test_registry_validator_accepts_good_shape(tmp_path, monkeypatch):
    good = {"installPath": str(tmp_path), "version": "1.3.5"}
    monkeypatch.setattr(rp, "REGISTRY", _write_registry(tmp_path, good))
    _data, e = rp._validated_registry()
    assert e["version"] == "1.3.5"


def test_registry_validator_refuses_non_string_install_path(tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "REGISTRY", _write_registry(tmp_path, {"installPath": 12345, "version": "1.3.5"}))
    try:
        rp._validated_registry()
        raise AssertionError("non-string installPath must raise Gate")
    except rp.Gate as exc:
        assert "shape" in str(exc)


def test_registry_validator_refuses_malformed_json(tmp_path, monkeypatch):
    p = tmp_path / "installed_plugins.json"
    p.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(rp, "REGISTRY", str(p))
    try:
        rp._validated_registry()
        raise AssertionError("malformed JSON must raise Gate")
    except rp.Gate:
        pass


def test_update_registry_is_atomic_and_backed_up(tmp_path, monkeypatch):
    reg = _write_registry(tmp_path, {"installPath": str(tmp_path), "version": "1.3.5"})
    monkeypatch.setattr(rp, "REGISTRY", reg)
    monkeypatch.setattr(rp, "LAST_UPDATE_CHECK", str(tmp_path / ".last-update-check"))
    cache_dir = str(tmp_path / "cache" / "1.3.6")
    rp.update_registry("1.3.6", cache_dir)
    data = json.loads(open(reg, encoding="utf-8").read())
    e = data["plugins"][rp.PLUGIN_KEY][0]
    assert e["version"] == "1.3.6" and e["installPath"] == cache_dir
    names = os.listdir(str(tmp_path))
    assert not any(n.endswith(".tmp") for n in names), "tmp file must not survive os.replace"
    assert any(".bak-" in n for n in names), "a timestamped backup must exist"


def test_tripwire_derivation_matches_bump_config():
    with open(os.path.join(rp.PLUGIN, ".version-bump.json"), encoding="utf-8") as f:
        declared = json.load(f)["files"]
    derived = {
        os.path.relpath(os.path.normpath(os.path.join(rp.PLUGIN, d["path"])), rp.REPO).replace("\\", "/")
        for d in declared
    }
    assert derived == {"plugins/virtuoso/.claude-plugin/plugin.json",
                       ".claude-plugin/marketplace.json"}, derived
