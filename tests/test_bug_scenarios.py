"""
Bug scenario tests T1–T8 for Transcribbler.

T1 — Kod-i-kod dubbel-escape (overlapping annotations + search highlighting)
T2 — Uppdatera-knapp sparar memo/ankar (persistence after reload)
T3 — Export utan kodval (all export types with no tid filter)
T5 — Popup overlap vid borttagning (delete annotation consistency)
T6 — Kodbok antal med bildpins (counts include point annotations)
T7 — Slå ihop koder: avbryt + funktion + varning (merge codes)
T8 — Regressionstest att projektmerge fortfarande fungerar
T4 — Avbryt vid projektbyte (full state reset) — SIST, ändrar STATE
"""
import json
import uuid
import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_transcript(flask_client, tid=None, text_content="", **fields):
    """Insert a transcript + text file into the test project."""
    import main
    folder = main.STATE["folder"]
    tid = tid or str(uuid.uuid4())[:8]
    text_file = f"{tid}.txt"
    txt_path = os.path.join(folder, "transcripts", text_file)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text_content)
    t = {"id": tid, "name": f"Transcript-{tid}", "text_file": text_file, **fields}
    main.STATE["project"]["transcripts"].append(t)
    return t


def _add_code(flask_client, name, parent=None, color="#4a90d9", description=""):
    """Add a code via the API and return the new code dict."""
    r = flask_client.post("/api/codes", json={
        "name": name, "parent": parent, "color": color, "description": description,
    }, content_type="application/json")
    assert r.status_code == 200, r.get_json()
    codes = r.get_json()["project"]["codes"]
    return codes[-1]


def _add_annotation(flask_client, tid, code_id, start, end, text,
                    memo="", weight=50, anchor=False):
    """Add a text annotation via the API."""
    r = flask_client.post(f"/api/transcripts/{tid}/annotations", json={
        "code_id": code_id, "start": start, "end": end, "text": text,
        "memo": memo, "weight": weight, "anchor": anchor,
    }, content_type="application/json")
    assert r.status_code == 200, r.get_json()
    return r.get_json()["annotation"]


def _add_point_annotation(flask_client, tid, code_id, x, y,
                          memo="", weight=50, anchor=False):
    """Add a point (image pin) annotation via the API."""
    r = flask_client.post(f"/api/transcripts/{tid}/annotations", json={
        "code_id": code_id, "kind": "point", "x": x, "y": y,
        "memo": memo, "weight": weight, "anchor": anchor,
    }, content_type="application/json")
    assert r.status_code == 200, r.get_json()
    return r.get_json()["annotation"]


# ===========================================================================
# T1 — Kod-i-kod dubbel-escape (overlapping annotations + search)
# ===========================================================================

class TestT1_OverlappingAnnotationsAndSearch:
    """
    When two annotations overlap on the same text, data must be stored
    correctly and search highlighting must compute correct offsets.
    """

    def test_step1_create_overlapping_annotations(self, flask_client):
        """Two codes can annotate overlapping character ranges."""
        text = "Det här är en exempeltext med överlappande kodning i mitten."
        t = _add_transcript(flask_client, text_content=text)
        c1 = _add_code(flask_client, "Tema A")
        c2 = _add_code(flask_client, "Tema B")

        a1 = _add_annotation(flask_client, t["id"], c1["id"], 10, 30,
                             text[10:30])
        a2 = _add_annotation(flask_client, t["id"], c2["id"], 20, 45,
                             text[20:45])

        # Overlapping region [20,30) should be annotated by both
        assert a1["start"] == 10 and a1["end"] == 30
        assert a2["start"] == 20 and a2["end"] == 45

    def test_step2_annotations_persisted(self, flask_client):
        """Previously added overlapping annotations are retrievable."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        r = flask_client.get(f"/api/transcripts/{tid}/annotations")
        anns = r.get_json()["annotations"]
        assert len(anns) == 2

    def test_step3_search_finds_overlapping_text(self, flask_client):
        """Search returns correct snippet for text in the overlap zone."""
        r = flask_client.get("/api/search?q=exempeltext")
        data = r.get_json()
        assert data["total_matches"] >= 1
        match = data["results"][0]["matches"][0]
        assert match["start"] >= 0
        assert "snippet_match_start" in match

    def test_step4_search_snippet_offset_correct(self, flask_client):
        """snippet_match_start correctly points to the query inside the snippet."""
        r = flask_client.get("/api/search?q=exempeltext")
        match = r.get_json()["results"][0]["matches"][0]
        snippet = match["snippet"]
        sms = match["snippet_match_start"]
        # The snippet at offset sms should contain our query
        assert snippet[sms:sms + len("exempeltext")].lower() == "exempeltext"

    def test_step5_html_special_chars_in_text(self, flask_client):
        """Text with HTML-like content (<b>, &amp;) stored verbatim, not escaped."""
        text = "Kod <b>fetstil</b> och &amp; tecken i text"
        t = _add_transcript(flask_client, text_content=text)
        c = _add_code(flask_client, "HTMLtest")
        a = _add_annotation(flask_client, t["id"], c["id"], 4, 18,
                            text[4:18])
        assert a["text"] == "<b>fetstil</b>"

    def test_step6_search_html_content(self, flask_client):
        """Search for HTML-like content works without double-escaping."""
        r = flask_client.get("/api/search?q=fetstil")
        data = r.get_json()
        assert data["total_matches"] >= 1
        snippet = data["results"][0]["matches"][0]["snippet"]
        assert "<b>" in snippet  # raw HTML in snippet, not &lt;b&gt;

    def test_step7_overlapping_annotations_in_search_snippet(self, flask_client):
        """Search in a transcript with overlapping annotations returns valid offsets."""
        import main
        tid = main.STATE["project"]["transcripts"][0]["id"]
        # Search for text that spans the overlap region
        r = flask_client.get("/api/search?q=exempeltext")
        data = r.get_json()
        for result in data["results"]:
            if result["tid"] == tid:
                for m in result["matches"]:
                    assert m["start"] >= 0
                    assert m["snippet_match_start"] >= 0
                    assert m["snippet_match_start"] < len(m["snippet"])


# ===========================================================================
# T2 — Uppdatera-knapp sparar memo/ankar (persistence)
# ===========================================================================

class TestT2_UpdateMemoAnchor:
    """
    PATCH annotation must persist memo and anchor; values survive reload.
    """

    def test_step1_create_annotation_with_memo(self, flask_client):
        text = "Testtext för memo och ankare"
        t = _add_transcript(flask_client, text_content=text)
        c = _add_code(flask_client, "MemoKod")
        a = _add_annotation(flask_client, t["id"], c["id"], 0, 8,
                            text[0:8], memo="initialt memo", anchor=False)
        assert a["memo"] == "initialt memo"
        assert a["anchor"] is False

    def test_step2_update_memo(self, flask_client):
        """PATCH updates memo text."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        anns = flask_client.get(f"/api/transcripts/{tid}/annotations").get_json()["annotations"]
        ann_id = anns[-1]["id"]
        r = flask_client.patch(f"/api/transcripts/{tid}/annotations/{ann_id}",
                               json={"memo": "uppdaterat memo"},
                               content_type="application/json")
        assert r.get_json()["ok"] is True

    def test_step3_update_anchor(self, flask_client):
        """PATCH sets anchor flag to true."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        anns = flask_client.get(f"/api/transcripts/{tid}/annotations").get_json()["annotations"]
        ann_id = anns[-1]["id"]
        r = flask_client.patch(f"/api/transcripts/{tid}/annotations/{ann_id}",
                               json={"anchor": True},
                               content_type="application/json")
        assert r.get_json()["ok"] is True

    def test_step4_values_persisted_after_reload(self, flask_client):
        """Reload annotations from disk and verify memo + anchor survived."""
        import main
        from core.annotation import load_annotations
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        coder = main.STATE["coder"]
        anns = load_annotations(main.STATE["folder"], tid, coder)
        target = anns[-1]
        assert target["memo"] == "uppdaterat memo"
        assert target["anchor"] is True

    def test_step5_update_weight(self, flask_client):
        """PATCH updates weight and persists."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        anns = flask_client.get(f"/api/transcripts/{tid}/annotations").get_json()["annotations"]
        ann_id = anns[-1]["id"]
        r = flask_client.patch(f"/api/transcripts/{tid}/annotations/{ann_id}",
                               json={"weight": 80},
                               content_type="application/json")
        assert r.get_json()["ok"] is True
        from core.annotation import load_annotations
        reloaded = load_annotations(main.STATE["folder"], tid, main.STATE["coder"])
        assert reloaded[-1]["weight"] == 80

    def test_step6_update_code_id(self, flask_client):
        """PATCH changes the code assignment."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        c2 = _add_code(flask_client, "NyKod")
        anns = flask_client.get(f"/api/transcripts/{tid}/annotations").get_json()["annotations"]
        ann_id = anns[-1]["id"]
        r = flask_client.patch(f"/api/transcripts/{tid}/annotations/{ann_id}",
                               json={"code_id": c2["id"]},
                               content_type="application/json")
        assert r.get_json()["ok"] is True
        from core.annotation import load_annotations
        reloaded = load_annotations(main.STATE["folder"], tid, main.STATE["coder"])
        assert reloaded[-1]["code_id"] == c2["id"]


# ===========================================================================
# T3 — Export utan kodval (all export types without tid filter)
# ===========================================================================

class TestT3_ExportWithoutCodeSelection:
    """
    All export endpoints must work when no specific tid is selected.
    """

    @pytest.fixture(autouse=True)
    def setup_data(self, flask_client):
        """Ensure at least one transcript with annotations exists."""
        import main
        if not main.STATE["project"]["transcripts"]:
            text = "Exporttext för test av alla exportformat."
            t = _add_transcript(flask_client, text_content=text)
            c = _add_code(flask_client, "ExportKod")
            _add_annotation(flask_client, t["id"], c["id"], 0, 10, text[0:10])

    def test_step1_csv_export(self, flask_client):
        r = flask_client.get("/api/export/csv")
        assert r.status_code == 200
        assert b"transcript" in r.data  # header row

    def test_step2_csv_tidy_export(self, flask_client):
        r = flask_client.get("/api/export/csv/tidy")
        assert r.status_code == 200
        assert b"project" in r.data

    def test_step3_markdown_codes_export(self, flask_client):
        r = flask_client.get("/api/export/markdown/codes")
        assert r.status_code == 200
        assert len(r.data) > 0

    def test_step4_markdown_codebook_export(self, flask_client):
        r = flask_client.get("/api/export/markdown/codebook")
        assert r.status_code == 200

    def test_step5_codebook_csv_export(self, flask_client):
        r = flask_client.get("/api/export/codebook/csv")
        assert r.status_code == 200
        assert b"name" in r.data

    def test_step6_codetree_docx_export(self, flask_client):
        r = flask_client.get("/api/export/codetree/docx")
        assert r.status_code == 200
        assert len(r.data) > 0  # non-empty docx bytes

    def test_step7_codetree_odt_export(self, flask_client):
        r = flask_client.get("/api/export/codetree/odt")
        assert r.status_code == 200
        assert len(r.data) > 0

    def test_step8_qdpx_export(self, flask_client):
        r = flask_client.get("/api/export/qdpx")
        assert r.status_code == 200
        # QDPX is a zip file — should start with PK
        assert r.data[:2] == b"PK"


# ===========================================================================
# T5 — Popup overlap vid borttagning (delete annotation consistency)
# ===========================================================================

class TestT5_DeleteAnnotationConsistency:
    """
    Deleting an annotation must not corrupt adjacent/overlapping annotations.
    """

    def test_step1_setup_adjacent_annotations(self, flask_client):
        text = "AAAA BBBB CCCC DDDD EEEE"
        t = _add_transcript(flask_client, text_content=text)
        c = _add_code(flask_client, "Kod5")
        _add_annotation(flask_client, t["id"], c["id"], 0, 4, "AAAA")
        _add_annotation(flask_client, t["id"], c["id"], 5, 9, "BBBB")
        _add_annotation(flask_client, t["id"], c["id"], 10, 14, "CCCC")
        _add_annotation(flask_client, t["id"], c["id"], 15, 19, "DDDD")

    def test_step2_delete_middle_annotation(self, flask_client):
        """Deleting the second annotation leaves others intact."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        anns = flask_client.get(f"/api/transcripts/{tid}/annotations").get_json()["annotations"]
        to_delete = anns[1]  # BBBB
        r = flask_client.delete(f"/api/transcripts/{tid}/annotations/{to_delete['id']}")
        assert r.get_json()["ok"] is True

    def test_step3_remaining_annotations_intact(self, flask_client):
        """After deletion, remaining annotations have correct data."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        anns = flask_client.get(f"/api/transcripts/{tid}/annotations").get_json()["annotations"]
        assert len(anns) == 3
        texts = {a["text"] for a in anns}
        assert "BBBB" not in texts
        assert {"AAAA", "CCCC", "DDDD"} == texts

    def test_step4_delete_all_leaves_empty_list(self, flask_client):
        """Deleting all remaining annotations leaves an empty list."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        anns = flask_client.get(f"/api/transcripts/{tid}/annotations").get_json()["annotations"]
        for a in anns:
            r = flask_client.delete(f"/api/transcripts/{tid}/annotations/{a['id']}")
            assert r.get_json()["ok"] is True
        anns = flask_client.get(f"/api/transcripts/{tid}/annotations").get_json()["annotations"]
        assert len(anns) == 0


# ===========================================================================
# T6 — Kodbok antal med bildpins (counts include point annotations)
# ===========================================================================

class TestT6_CodebookCountWithImagePins:
    """
    Code usage stats and codebook CSV export must count point (image pin)
    annotations, not just text annotations.
    """

    def test_step1_add_text_and_point_annotations(self, flask_client):
        text = "Bildtest"
        t = _add_transcript(flask_client, text_content=text)
        c = _add_code(flask_client, "BildKod")
        _add_annotation(flask_client, t["id"], c["id"], 0, 4, "Bild")
        _add_point_annotation(flask_client, t["id"], c["id"], 50.0, 30.0)
        _add_point_annotation(flask_client, t["id"], c["id"], 75.0, 60.0)

    def test_step2_stats_count_includes_points(self, flask_client):
        """Stats API counts both text and point annotations."""
        r = flask_client.get("/api/stats")
        data = r.get_json()
        # Find our code
        bild_row = next((r for r in data["rows"] if r["name"] == "BildKod"), None)
        assert bild_row is not None
        assert bild_row["count"] == 3  # 1 text + 2 points

    def test_step3_codes_stats_count(self, flask_client):
        """/api/codes/stats returns count including point annotations."""
        r = flask_client.get("/api/codes/stats")
        counts = r.get_json()
        import main
        bild_code = next(c for c in main.STATE["project"]["codes"]
                         if c["name"] == "BildKod")
        assert counts[bild_code["id"]] == 3

    def test_step4_codebook_csv_includes_point_counts(self, flask_client):
        """Codebook CSV export includes point annotation counts."""
        r = flask_client.get("/api/export/codebook/csv")
        assert r.status_code == 200
        csv_text = r.data.decode("utf-8-sig")
        # Find the BildKod row and check count. splitlines handles the CRLF
        # terminators that csv.DictWriter emits.
        lines = csv_text.strip().splitlines()
        header = lines[0]
        for line in lines[1:]:
            if "BildKod" in line:
                parts = line.split(",")
                count_idx = header.split(",").index("count")
                assert int(parts[count_idx]) == 3
                break
        else:
            pytest.fail("BildKod not found in codebook CSV")

    def test_step5_point_annotation_fields(self, flask_client):
        """Point annotations have x, y but no start/end."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        anns = flask_client.get(f"/api/transcripts/{tid}/annotations").get_json()["annotations"]
        points = [a for a in anns if a.get("kind") == "point"]
        assert len(points) == 2
        for p in points:
            assert "x" in p and "y" in p
            assert "start" not in p
            assert "end" not in p


# ===========================================================================
# T7 — Slå ihop koder: avbryt + funktion + varning (merge codes)
# ===========================================================================

class TestT7_MergeCodes:
    """
    Test code merging: self-merge rejected, actual merge works,
    overlapping annotations are de-duplicated.
    """

    def test_step1_self_merge_rejected(self, flask_client):
        """Merging a code into itself returns an error."""
        c = _add_code(flask_client, "SelfMerge")
        r = flask_client.post("/api/codes/merge",
                              json={"source_id": c["id"], "target_id": c["id"]},
                              content_type="application/json")
        assert r.status_code == 400
        assert "itself" in r.get_json()["error"].lower()

    def test_step2_missing_ids_rejected(self, flask_client):
        """Missing source_id or target_id returns 400."""
        r = flask_client.post("/api/codes/merge",
                              json={"source_id": "abc"},
                              content_type="application/json")
        assert r.status_code == 400

    def test_step3_nonexistent_code_rejected(self, flask_client):
        """Merging with a non-existent code returns error."""
        c = _add_code(flask_client, "Existent")
        r = flask_client.post("/api/codes/merge",
                              json={"source_id": "nope123", "target_id": c["id"]},
                              content_type="application/json")
        assert r.status_code == 400

    def test_step4_basic_merge_moves_annotations(self, flask_client):
        """Merge moves all annotations from source to target."""
        text = "Mergetest text med tillräckligt innehåll"
        t = _add_transcript(flask_client, text_content=text)
        source = _add_code(flask_client, "KällKod")
        target = _add_code(flask_client, "MålKod")
        _add_annotation(flask_client, t["id"], source["id"], 0, 9, text[0:9])
        _add_annotation(flask_client, t["id"], source["id"], 10, 14, text[10:14])

        r = flask_client.post("/api/codes/merge",
                              json={"source_id": source["id"],
                                    "target_id": target["id"]},
                              content_type="application/json")
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

        # Source code should be gone
        import main
        code_ids = [c["id"] for c in main.STATE["project"]["codes"]]
        assert source["id"] not in code_ids

        # Annotations should now belong to target
        anns = flask_client.get(
            f"/api/transcripts/{t['id']}/annotations"
        ).get_json()["annotations"]
        for a in anns:
            assert a["code_id"] == target["id"]

    def test_step5_merge_deduplicates_overlapping(self, flask_client):
        """When source and target have identical annotations, duplicates are removed."""
        text = "Dedup testtext"
        t = _add_transcript(flask_client, text_content=text)
        src = _add_code(flask_client, "DedupSrc")
        tgt = _add_code(flask_client, "DedupTgt")

        # Same span annotated by both codes
        _add_annotation(flask_client, t["id"], src["id"], 0, 5, "Dedup")
        _add_annotation(flask_client, t["id"], tgt["id"], 0, 5, "Dedup")

        r = flask_client.post("/api/codes/merge",
                              json={"source_id": src["id"],
                                    "target_id": tgt["id"]},
                              content_type="application/json")
        assert r.status_code == 200

        anns = flask_client.get(
            f"/api/transcripts/{t['id']}/annotations"
        ).get_json()["annotations"]
        # Should have only 1 annotation (duplicate removed)
        matching = [a for a in anns if a["start"] == 0 and a["end"] == 5]
        assert len(matching) == 1
        assert matching[0]["code_id"] == tgt["id"]

    def test_step6_merge_reparents_children(self, flask_client):
        """Source code's children are re-parented to target after merge."""
        parent_src = _add_code(flask_client, "ParentSrc")
        child = _add_code(flask_client, "Barn", parent=parent_src["id"])
        target = _add_code(flask_client, "ParentTgt")

        r = flask_client.post("/api/codes/merge",
                              json={"source_id": parent_src["id"],
                                    "target_id": target["id"]},
                              content_type="application/json")
        assert r.status_code == 200

        import main
        child_now = next(c for c in main.STATE["project"]["codes"]
                         if c["id"] == child["id"])
        assert child_now["parent"] == target["id"]

    def test_step7_merge_preserves_unrelated_annotations(self, flask_client):
        """Annotations for other codes are untouched by the merge."""
        text = "Orörd text"
        t = _add_transcript(flask_client, text_content=text)
        unrelated = _add_code(flask_client, "Orörd")
        src = _add_code(flask_client, "MergeSrc2")
        tgt = _add_code(flask_client, "MergeTgt2")

        ann_u = _add_annotation(flask_client, t["id"], unrelated["id"], 0, 5, "Orörd")
        _add_annotation(flask_client, t["id"], src["id"], 6, 10, "text")

        flask_client.post("/api/codes/merge",
                          json={"source_id": src["id"], "target_id": tgt["id"]},
                          content_type="application/json")

        anns = flask_client.get(
            f"/api/transcripts/{t['id']}/annotations"
        ).get_json()["annotations"]
        u_ann = next(a for a in anns if a["id"] == ann_u["id"])
        assert u_ann["code_id"] == unrelated["id"]

    def test_step8_merged_code_not_in_codebook(self, flask_client):
        """After merge, source code is no longer in the codebook."""
        src = _add_code(flask_client, "TaBortKod")
        tgt = _add_code(flask_client, "BehållKod")
        flask_client.post("/api/codes/merge",
                          json={"source_id": src["id"], "target_id": tgt["id"]},
                          content_type="application/json")
        r = flask_client.get("/api/export/markdown/codebook")
        assert "TaBortKod" not in r.data.decode("utf-8")
        assert "BehållKod" in r.data.decode("utf-8")

    def test_step9_merge_with_empty_source_succeeds(self, flask_client):
        """Merging a code with no annotations is a valid operation."""
        src = _add_code(flask_client, "TomKälla")
        tgt = _add_code(flask_client, "TomMål")
        r = flask_client.post("/api/codes/merge",
                              json={"source_id": src["id"], "target_id": tgt["id"]},
                              content_type="application/json")
        assert r.status_code == 200


# ===========================================================================
# T8 — Regressionstest att projektmerge fortfarande fungerar
# ===========================================================================

class TestT8_ProjectMerge:
    """
    /api/merge imports external annotation files correctly.
    """

    def test_step1_import_valid_annotation_file(self, flask_client, tmp_path):
        """Import an external coder's annotation JSON file."""
        text = "Mergetext"
        t = _add_transcript(flask_client, text_content=text)
        import main
        # Ensure annotations dir exists
        ann_dir = os.path.join(main.STATE["folder"], "annotations")
        os.makedirs(ann_dir, exist_ok=True)

        c = _add_code(flask_client, "MergeKod")

        # Create external annotation file
        ext_file = tmp_path / "extern.json"
        ext_file.write_text(json.dumps({
            "transcript_id": t["id"],
            "coder": "extern_kodare",
            "annotations": [{
                "id": "ext001",
                "code_id": c["id"],
                "kind": "text",
                "start": 0,
                "end": 5,
                "text": "Merge",
                "memo": "",
                "weight": 50,
                "anchor": False,
                "created": "2024-01-01T00:00:00",
            }],
        }), encoding="utf-8")

        r = flask_client.post("/api/merge",
                              json={"path": str(ext_file)},
                              content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert data["imported"] == 1
        assert data["coder"] == "extern_kodare"

    def test_step2_imported_annotations_visible(self, flask_client):
        """Imported annotations are visible via the all-coders endpoint."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        r = flask_client.get(f"/api/transcripts/{tid}/annotations/all")
        by_coder = r.get_json()["by_coder"]
        assert "extern_kodare" in by_coder
        assert len(by_coder["extern_kodare"]) == 1

    def test_step3_reimport_skips_duplicates(self, flask_client, tmp_path):
        """Re-importing the same file skips already existing annotations."""
        import main
        tid = main.STATE["project"]["transcripts"][-1]["id"]
        c = next(c for c in main.STATE["project"]["codes"] if c["name"] == "MergeKod")

        ext_file = tmp_path / "extern2.json"
        ext_file.write_text(json.dumps({
            "transcript_id": tid,
            "coder": "extern_kodare",
            "annotations": [{
                "id": "ext001",  # same ID as before
                "code_id": c["id"],
                "kind": "text",
                "start": 0,
                "end": 5,
                "text": "Merge",
                "memo": "",
                "weight": 50,
                "anchor": False,
                "created": "2024-01-01T00:00:00",
            }],
        }), encoding="utf-8")

        r = flask_client.post("/api/merge",
                              json={"path": str(ext_file)},
                              content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data["imported"] == 0
        assert data["skipped"] == 1


# ===========================================================================
# T4 — Avbryt vid projektbyte (state reset) — SIST, ändrar STATE
# ===========================================================================

class TestT4_ProjectSwitchReset:
    """
    Opening a new project must fully reset state; old data must not leak.
    Placed last because it mutates STATE (opens a different project).
    """

    def test_step1_initial_project_has_data(self, flask_client):
        """Set up data in current project."""
        text = "Projektbyte test"
        t = _add_transcript(flask_client, text_content=text)
        c = _add_code(flask_client, "GammalKod")
        _add_annotation(flask_client, t["id"], c["id"], 0, 5, text[0:5])
        r = flask_client.get("/api/project")
        proj = r.get_json()["project"]
        assert len(proj["codes"]) >= 1
        assert len(proj["transcripts"]) >= 1

    def test_step2_open_new_project_resets_state(self, flask_client, tmp_path):
        """Opening a different project resets codes and transcripts."""
        import main
        new_folder = str(tmp_path / "new_project")
        os.makedirs(os.path.join(new_folder, "transcripts"), exist_ok=True)
        os.makedirs(os.path.join(new_folder, "annotations"), exist_ok=True)
        new_proj = {"name": "NyttProjekt", "transcripts": [], "codes": [], "speakers": []}
        with open(os.path.join(new_folder, "project.json"), "w") as f:
            json.dump(new_proj, f)

        r = flask_client.post("/api/project/open",
                              json={"folder": new_folder, "coder": "testare"},
                              content_type="application/json")
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_step3_new_project_has_no_codes(self, flask_client):
        r = flask_client.get("/api/codes")
        data = r.get_json()
        codes = data.get("codes") or data.get("tree", [])
        assert len(codes) == 0 if isinstance(codes, list) else True

    def test_step4_new_project_has_no_transcripts(self, flask_client):
        r = flask_client.get("/api/project")
        proj = r.get_json()["project"]
        assert len(proj["transcripts"]) == 0

    def test_step5_search_returns_empty(self, flask_client):
        r = flask_client.get("/api/search?q=Projektbyte")
        data = r.get_json()
        assert data["total_matches"] == 0
