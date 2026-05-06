"""Shared pytest fixtures for Transcribbler tests."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make sure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="class")
def tmp_project(tmp_path_factory):
    """Return a minimal project structure (folder, project dict, transcripts dir).

    Class-scoped so that step-chain tests (TestT1_… → test_step1, test_step2)
    can share the same project state, which is how those suites are written.
    Single-test classes still get a fresh directory per class.
    """
    tmp_path = tmp_path_factory.mktemp("project")
    (tmp_path / "transcripts").mkdir()
    project = {
        "name": "TestProject",
        "transcripts": [],
        "codes": [],
        "speakers": [],
    }
    (tmp_path / "project.json").write_text(json.dumps(project), encoding="utf-8")
    return tmp_path, project


@pytest.fixture(scope="class")
def flask_client(tmp_project, tmp_path_factory):
    """Flask test client with an active project loaded into STATE.

    Class-scoped — shares STATE across tests in the same class so the
    test_stepN_… chains in test_bug_scenarios work as authored.
    """
    tmp_path, project = tmp_project

    # Patch STATE before importing app to avoid side-effects
    import main
    main.STATE["folder"] = str(tmp_path)
    main.STATE["project"] = project
    main.STATE["coder"] = "testare"

    # Redirect recent-projects file so tests don't pollute ~/.transcribbler_recent.json
    fake_recent = tmp_path_factory.mktemp("recent") / "recent.json"
    original_recent = main.RECENT_FILE
    main.RECENT_FILE = fake_recent

    main.app.config["TESTING"] = True
    with main.app.test_client() as client:
        yield client

    # Cleanup
    main.RECENT_FILE = original_recent
    main.STATE["folder"] = None
    main.STATE["project"] = None
    main.STATE["coder"] = None
