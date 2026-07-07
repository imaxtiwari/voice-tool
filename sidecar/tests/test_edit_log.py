import os
# Set mock environment variables before import to pass validation
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint.azure.com"
os.environ["AZURE_OPENAI_KEY"] = "mock-key-value"

import pytest
import sqlite3
from sidecar import edit_log

@pytest.fixture(autouse=True)
def setup_in_memory_db():
    """Fixture to force edit_log to use an isolated in-memory DB and reset connections."""
    edit_log.DB_PATH = ":memory:"
    edit_log.close_connection()
    yield
    edit_log.close_connection()

def test_init_db_creates_table():
    """Verifies init_db() creates the edit_log table."""
    edit_log.init_db()
    conn = edit_log.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='edit_log';")
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "edit_log"

def test_log_edit_inserts_correctly():
    """Verifies that log_edit() inserts rows with correct parameters and maps accepted=True to 1."""
    edit_log.init_db()
    edit_log.log_edit(
        original_seg="Original text content",
        proposed_seg="Proposed text content",
        accepted=True,
        de_ai_level=70,
        voice_level=90,
        mode="my_voice",
        model_used="stub"
    )
    
    conn = edit_log.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ts, original_seg, proposed_seg, accepted, de_ai_level, voice_level, mode, model_used FROM edit_log;")
    row = cursor.fetchone()
    assert row is not None
    assert row[1] == "Original text content"
    assert row[2] == "Proposed text content"
    assert row[3] == 1  # stored as integer 1
    assert row[4] == 70
    assert row[5] == 90
    assert row[6] == "my_voice"
    assert row[7] == "stub"

def test_log_edit_accepted_false():
    """Verifies that log_edit() stores accepted=False as 0."""
    edit_log.init_db()
    edit_log.log_edit(
        original_seg="Some other segment",
        proposed_seg="Some rewrite",
        accepted=False,
        de_ai_level=10,
        voice_level=20,
        mode="ceo_archetype",
        model_used="base_fallback"
    )
    
    conn = edit_log.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT accepted, mode, model_used FROM edit_log WHERE original_seg='Some other segment';")
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == 0  # stored as integer 0
    assert row[1] == "ceo_archetype"
    assert row[2] == "base_fallback"
