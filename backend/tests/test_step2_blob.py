"""
tests/test_step2_blob.py
────────────────────────
Manual verification script for Step 2.
Run AFTER you have filled in real Azure credentials in backend/.env

Run with:
    cd backend
    .venv\\Scripts\\python tests/test_step2_blob.py
"""
import os
import sys
import json
import tempfile

# Add backend/ to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.blob_service import BlobService

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"


def ok(msg):  print(f"{GREEN}  ✅ PASS{RESET} — {msg}")
def fail(msg): print(f"{RED}  ❌ FAIL{RESET} — {msg}"); sys.exit(1)


def run_tests():
    print(f"\n{BOLD}═══ Step 2: Blob Service Tests ═══{RESET}\n")

    blob = BlobService()
    TEST_PATH = "raw/test_step2_verification.txt"
    TEST_CONTENT = "Hello from AI Doc Platform — Step 2 verification!"

    # ── Test 1: Upload text ───────────────────────────────
    try:
        blob.upload_text(TEST_CONTENT, TEST_PATH)
        ok(f"upload_text → {TEST_PATH}")
    except Exception as e:
        fail(f"upload_text failed: {e}")

    # ── Test 2: Exists check ──────────────────────────────
    try:
        assert blob.exists(TEST_PATH), "exists() returned False after upload"
        ok("exists() returns True for uploaded blob")
    except Exception as e:
        fail(f"exists() failed: {e}")

    # ── Test 3: Download text ─────────────────────────────
    try:
        downloaded = blob.download_text(TEST_PATH)
        assert downloaded == TEST_CONTENT, f"Content mismatch: {downloaded!r}"
        ok("download_text — content matches uploaded content")
    except Exception as e:
        fail(f"download_text failed: {e}")

    # ── Test 4: Upload JSON ───────────────────────────────
    try:
        payload = {"document_id": "test-123", "status": "ok", "fields": ["a", "b"]}
        json_path = "extracted/test_step2.json"
        blob.upload_json(payload, json_path)
        result = blob.download_json(json_path)
        assert result["document_id"] == "test-123"
        ok("upload_json / download_json — roundtrip works")
        blob.delete(json_path)
    except Exception as e:
        fail(f"JSON roundtrip failed: {e}")

    # ── Test 5: List blobs ────────────────────────────────
    try:
        blobs = blob.list_blobs(prefix="raw/")
        assert any("test_step2" in b for b in blobs), f"Test blob not in list: {blobs}"
        ok(f"list_blobs('raw/') — found {len(blobs)} blob(s)")
    except Exception as e:
        fail(f"list_blobs failed: {e}")

    # ── Test 6: Download to file ──────────────────────────
    # NOTE: Use mktemp() not NamedTemporaryFile — Windows locks the file
    # when NamedTemporaryFile is open, blocking writes from blob_service.
    try:
        tmp_path = tempfile.mktemp(suffix=".txt")
        blob.download_to_file(TEST_PATH, tmp_path)
        with open(tmp_path, "rb") as f:
            assert f.read() == TEST_CONTENT.encode("utf-8")
        os.unlink(tmp_path)
        ok("download_to_file — file content matches")
    except Exception as e:
        fail(f"download_to_file failed: {e}")

    # ── Test 7: Path builders ─────────────────────────────
    try:
        assert BlobService.raw_path("abc", "pdf")       == "raw/abc.pdf"
        assert BlobService.processed_path("abc")        == "processed/abc.md"
        assert BlobService.extracted_path("abc")        == "extracted/abc.json"
        assert BlobService.log_path("abc", 12345)       == "logs/abc_12345.json"
        assert BlobService.prompt_path("invoice", "v2") == "prompts/invoice/v2.json"
        assert BlobService.prompt_latest_path("invoice") == "prompts/invoice/latest.json"
        ok("All static path builders return correct strings")
    except AssertionError as e:
        fail(f"Path builder assertion failed: {e}")

    # ── Cleanup ───────────────────────────────────────────
    blob.delete(TEST_PATH)
    not_found = not blob.exists(TEST_PATH)
    assert not_found, "Blob still exists after delete!"
    ok("delete() — blob removed, exists() confirms deletion")

    print(f"\n{GREEN}{BOLD}All Step 2 tests passed! ✅{RESET}\n")
    print("Your Azure Blob Storage is correctly configured.\n")


if __name__ == "__main__":
    run_tests()
