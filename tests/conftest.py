"""Shared pytest fixtures for Transcribbler tests."""
import json
import os
import sys
import tempfile

import pytest

# Make sure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture()
def tmp_project(tmp_path):
    """Return a minimal project structure (folder, project dict, transcripts dir)."""
    (tmp_path / "transcripts").mkdir()
    project = {
        "name": "TestProject",
        "transcripts": [],
        "codes": [],
        "speakers": [],
    }
    (tmp_path / "project.json").write_text(json.dumps(project), encoding="utf-8")
    return tmp_path, project


@pytest.fixture()
def flask_client(tmp_project):
    """Flask test client with an active project loaded into STATE."""
    tmp_path, project = tmp_project

    # Patch STATE before importing app to avoid side-effects
    import main
    main.STATE["folder"] = str(tmp_path)
    main.STATE["project"] = project
    main.STATE["coder"] = "testare"

    main.app.config["TESTING"] = True
    with main.app.test_client() as client:
        yield client

    # Cleanup
    main.STATE["folder"] = None
    main.STATE["project"] = None
    main.STATE["coder"] = None
