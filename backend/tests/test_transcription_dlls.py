import os

from backend.app.services.transcription import register_cuda_dll_dirs


def test_cuda_dirs_go_on_path_and_dll_search(tmp_path, monkeypatch):
    site_dir = tmp_path / "site-packages"
    for lib in ("cublas", "cudnn"):
        (site_dir / "nvidia" / lib / "bin").mkdir(parents=True)
    registered = []
    monkeypatch.setattr(os, "add_dll_directory", registered.append, raising=False)
    monkeypatch.setenv("PATH", "C:\\existing")

    added = register_cuda_dll_dirs([str(site_dir), str(site_dir)])

    expected = [str(site_dir / "nvidia" / lib / "bin") for lib in ("cublas", "cudnn")]
    assert added == expected
    assert registered == expected
    path_entries = os.environ["PATH"].split(os.pathsep)
    # CTranslate2 loads cuBLAS lazily through PATH, so both dirs must be on it.
    assert all(d in path_entries for d in expected)
    assert "C:\\existing" in path_entries

    # Calling again (e.g. module reload) must not duplicate PATH entries.
    register_cuda_dll_dirs([str(site_dir)])
    assert os.environ["PATH"].split(os.pathsep).count(expected[0]) == 1


def test_missing_cuda_packages_are_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "add_dll_directory", lambda d: None, raising=False)
    monkeypatch.setenv("PATH", "C:\\existing")
    assert register_cuda_dll_dirs([str(tmp_path)]) == []
    assert os.environ["PATH"] == "C:\\existing"
