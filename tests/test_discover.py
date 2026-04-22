"""Tests for markcrawl.discover — seed packs, CLI main, and seed-file parsing."""

from __future__ import annotations

import io
import os
from unittest.mock import patch

import pytest

from markcrawl.discover import list_packs, load_seed_pack
from markcrawl.discover import main as discover_main

# ---------------------------------------------------------------------------
# list_packs
# ---------------------------------------------------------------------------

class TestListPacks:
    def test_finds_bundled_pack(self):
        packs = list_packs()
        assert "game-dashboards" in packs

    def test_sorted(self):
        packs = list_packs()
        assert packs == sorted(packs)


# ---------------------------------------------------------------------------
# load_seed_pack
# ---------------------------------------------------------------------------

class TestLoadSeedPack:
    def test_bundled_pack_has_urls(self):
        urls = load_seed_pack("game-dashboards")
        assert len(urls) > 5
        assert all(u.startswith("http") for u in urls)

    def test_bundled_pack_strips_comments(self):
        urls = load_seed_pack("game-dashboards")
        assert not any(u.startswith("#") for u in urls)
        assert not any(u == "" for u in urls)

    def test_unknown_pack_raises(self):
        with pytest.raises(FileNotFoundError):
            load_seed_pack("no-such-pack-exists")


# ---------------------------------------------------------------------------
# discover CLI main()
# ---------------------------------------------------------------------------

class TestDiscoverMain:
    def test_list_packs_exits_zero(self, capsys):
        rc = discover_main(["--list-packs"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "game-dashboards" in out

    def test_pack_prints_urls(self, capsys):
        rc = discover_main(["--pack", "game-dashboards"])
        assert rc == 0
        out = capsys.readouterr().out
        lines = [line for line in out.splitlines() if line]
        assert len(lines) > 5
        assert all(line.startswith("http") for line in lines)

    def test_unknown_pack_exits_two(self, capsys):
        rc = discover_main(["--pack", "does-not-exist"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "not found" in err.lower() or "error" in err.lower()

    def test_provider_stub_exits_two(self, capsys):
        rc = discover_main(["--provider", "brave", "query"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "not yet implemented" in err

    def test_no_args_prints_help_error(self, capsys):
        rc = discover_main([])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()


# ---------------------------------------------------------------------------
# _read_seed_file in cli.py
# ---------------------------------------------------------------------------

class TestReadSeedFile:
    def test_reads_file(self, tmp_path):
        from markcrawl.cli import _read_seed_file
        seed = tmp_path / "seeds.txt"
        seed.write_text(
            "# comment line\n"
            "\n"
            "https://a.com/\n"
            "https://b.com/\n"
            "   # indented comment — still dropped after strip\n"
            "https://c.com/\n"
        )
        urls = _read_seed_file(str(seed))
        assert urls == ["https://a.com/", "https://b.com/", "https://c.com/"]

    def test_reads_stdin(self):
        from markcrawl.cli import _read_seed_file
        stdin_data = "https://x.com/\n# skip\nhttps://y.com/\n"
        with patch("sys.stdin", io.StringIO(stdin_data)):
            urls = _read_seed_file("-")
        assert urls == ["https://x.com/", "https://y.com/"]

    def test_empty_file_returns_empty(self, tmp_path):
        from markcrawl.cli import _read_seed_file
        seed = tmp_path / "seeds.txt"
        seed.write_text("# only comments\n\n# more comments\n")
        assert _read_seed_file(str(seed)) == []


# ---------------------------------------------------------------------------
# _safe_netloc_dir
# ---------------------------------------------------------------------------

class TestSafeNetlocDir:
    def test_extracts_domain(self):
        from markcrawl.cli import _safe_netloc_dir
        assert _safe_netloc_dir("https://steamcharts.com/top") == "steamcharts.com"

    def test_strips_port(self):
        from markcrawl.cli import _safe_netloc_dir
        assert _safe_netloc_dir("http://example.com:8080/path") == "example.com"

    def test_lowercases(self):
        from markcrawl.cli import _safe_netloc_dir
        assert _safe_netloc_dir("https://Example.COM/") == "example.com"

    def test_missing_netloc_fallback(self):
        from markcrawl.cli import _safe_netloc_dir
        assert _safe_netloc_dir("not-a-url") == "unknown"


# ---------------------------------------------------------------------------
# Seed pack file structure
# ---------------------------------------------------------------------------

def test_seeds_dir_ships_with_package():
    """The seeds/ directory must live next to discover.py so it ships on install."""
    from markcrawl import discover
    seeds_path = os.path.join(os.path.dirname(discover.__file__), "seeds")
    assert os.path.isdir(seeds_path)
    # At least the game-dashboards pack must exist
    assert os.path.isfile(os.path.join(seeds_path, "game-dashboards.txt"))
