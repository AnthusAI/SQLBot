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
