import time

import sqlbot.core.docblocks as docblocks
from sqlbot.core.docblocks import (
    DocBlock,
    DocBlockCache,
    build_doc_block_digest,
    load_doc_blocks,
)


def _set_project_root(monkeypatch, tmp_path):
    monkeypatch.setattr(docblocks, "get_project_root", lambda: tmp_path)


def test_load_doc_blocks_from_profile(monkeypatch, tmp_path):
    profile_name = "demo"
    docs_dir = tmp_path / ".sqlbot" / "profiles" / profile_name / "docs"
    docs_dir.mkdir(parents=True)
    docs_dir.joinpath("overview.md").write_text(
        "{% docs customer_overview %}\nCustomers include both retail and wholesale buyers.\n{% enddocs %}\n",
        encoding="utf-8",
    )

    _set_project_root(monkeypatch, tmp_path)
    DocBlockCache.invalidate()

    blocks = load_doc_blocks(profile_name)

    assert "customer_overview" in blocks
    assert "retail" in blocks["customer_overview"].content
    assert str(blocks["customer_overview"].file_path).endswith("overview.md")


def test_docblock_cache_detects_file_changes(monkeypatch, tmp_path):
    profile_name = "demo"
    docs_dir = tmp_path / "profiles" / profile_name / "docs"
    docs_dir.mkdir(parents=True)
    doc_file = docs_dir / "metrics.md"
    doc_file.write_text(
        "{% docs revenue_doc %}\nInitial revenue description.\n{% enddocs %}\n",
        encoding="utf-8",
    )

    _set_project_root(monkeypatch, tmp_path)
    DocBlockCache.invalidate()

    blocks_initial = DocBlockCache.get_or_load(profile_name)
    assert blocks_initial["revenue_doc"].content.startswith("Initial")

    time.sleep(1.1)  # ensure filesystem mtime precision is exceeded
    doc_file.write_text(
        "{% docs revenue_doc %}\nUpdated revenue documentation with new details.\n{% enddocs %}\n",
        encoding="utf-8",
    )

    blocks_updated = DocBlockCache.get_or_load(profile_name)
    assert "Updated" in blocks_updated["revenue_doc"].content


def test_docblock_cache_tracks_mtimes_for_all_files(monkeypatch, tmp_path):
    """Test that mtimes are tracked for ALL files, even those with no blocks or duplicates."""
    profile_name = "demo"
    docs_dir = tmp_path / "profiles" / profile_name / "docs"
    docs_dir.mkdir(parents=True)
    
    # Create a file with a doc block
    file1 = docs_dir / "file1.md"
    file1.write_text(
        "{% docs test_doc %}\nTest content.\n{% enddocs %}\n",
        encoding="utf-8",
    )
    
    # Create a file with NO doc blocks
    file2 = docs_dir / "file2.md"
    file2.write_text("Just some regular markdown content.\n", encoding="utf-8")
    
    # Create a file with a duplicate doc block name
    file3 = docs_dir / "file3.md"
    file3.write_text(
        "{% docs test_doc %}\nDuplicate content.\n{% enddocs %}\n",
        encoding="utf-8",
    )

    _set_project_root(monkeypatch, tmp_path)
    DocBlockCache.invalidate()

    # Load blocks and verify all files are tracked
    from sqlbot.core.docblocks import discover_doc_blocks
    blocks, file_mtimes = discover_doc_blocks(profile_name)
    
    # Verify we found at least one doc block
    assert "test_doc" in blocks
    
    # Verify ALL files have their mtimes tracked, not just those with new blocks
    file1_str = str(file1)
    file2_str = str(file2)
    file3_str = str(file3)
    
    assert file1_str in file_mtimes, "file1 should have mtime tracked"
    assert file2_str in file_mtimes, "file2 (no blocks) should have mtime tracked"
    assert file3_str in file_mtimes, "file3 (duplicate block) should have mtime tracked"
    
    # Now modify file2 (which has no blocks) and verify cache detects it
    time.sleep(1.1)
    file2.write_text("Modified content.\n", encoding="utf-8")
    
    # Get cache entry and verify it detects staleness
    from sqlbot.core.docblocks import DocBlockCacheEntry
    entry = DocBlockCacheEntry(
        blocks=blocks,
        file_mtimes=file_mtimes,
        timestamp=time.time(),
    )
    
    assert entry.is_stale(), "Cache should detect file2 modification even though it has no blocks"


def test_build_doc_block_digest_includes_context():
    schema_text = (
        "\n"
        "version: 2\n"
        "sources:\n"
        "  - name: analytics\n"
        "    tables:\n"
        "      - name: customers\n"
        "        description: \"{{ doc('customer_table') }}\"\n"
        "        columns:\n"
        "          - name: lifetime_value\n"
        "            description: \"{{ doc('ltv_column') }}\"\n"
        "          - name: missing_column\n"
        "            description: \"{{ doc('missing_doc') }}\"\n"
    )

    doc_blocks = {
        "customer_table": DocBlock(
            name="customer_table",
            content="Customers cover all active accounts.",
            file_path="/tmp/docs.md",
            hash="abc",
        ),
        "ltv_column": DocBlock(
            name="ltv_column",
            content="Lifetime value calculated from gross margin over 12 months.",
            file_path="/tmp/docs.md",
            hash="def",
        ),
    }

    digest = build_doc_block_digest(schema_text, doc_blocks)

    assert "analytics.customers" in digest
    assert "doc 'customer_table'" in digest
    assert "Lifetime value" in digest
    assert "missing_doc" in digest  # missing doc referenced should be flagged
