import json
import pytest
from pathlib import Path
from server.state_store import write_json_atomic, read_json, update_json_locked


def test_write_and_read(tmp_path):
    target = tmp_path / "data.json"
    write_json_atomic(target, {"hello": "world"})
    assert read_json(target) == {"hello": "world"}


def test_atomic_write_preserves_on_crash(tmp_path, monkeypatch):
    target = tmp_path / "data.json"
    write_json_atomic(target, {"v": 1})

    original = Path.replace
    calls = {"n": 0}

    def failing(self, dst):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("simulated crash")
        return original(self, dst)

    monkeypatch.setattr(Path, "replace", failing)
    with pytest.raises(OSError):
        write_json_atomic(target, {"v": 2})
    assert read_json(target) == {"v": 1}


def test_read_missing_returns_none(tmp_path):
    assert read_json(tmp_path / "nope.json") is None


def test_read_corrupt_returns_none(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("not json")
    assert read_json(p) is None
    assert "corrupt JSON" in capsys.readouterr().err


def _increment_worker(target_str, times):
    from pathlib import Path
    from server.state_store import update_json_locked
    target = Path(target_str)
    for _ in range(times):
        update_json_locked(target, lambda d: {**d, "count": d.get("count", 0) + 1})


def test_concurrent_updates_serialize(tmp_path):
    import multiprocessing as mp
    target = tmp_path / "counter.json"
    write_json_atomic(target, {"count": 0})
    procs = [mp.Process(target=_increment_worker, args=(str(target), 100)) for _ in range(5)]
    for p in procs: p.start()
    for p in procs:
        p.join(30)
        assert p.exitcode == 0
    assert read_json(target) == {"count": 500}
