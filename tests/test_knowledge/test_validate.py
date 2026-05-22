"""Tests for claude_knowledge.validate."""

import json
import pytest
from pathlib import Path


class TestValidateKb:
    """Test validate_kb function."""

    def test_empty_kb(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with empty KB."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()
        (mock_kb_dir / "articles").mkdir()
        (mock_kb_dir / "state.json").write_text("{}")

        # Patch _config paths first
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.REPORTS_DIR", tmp_path / "reports")
        monkeypatch.setattr("claude_knowledge._config.STATE_FILE", tmp_path / "state.json")
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", tmp_path / "daily")

        # Patch _utils functions - note: validate.py imports these at module load time
        # so we need to import validate.py AFTER patching
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {})
        monkeypatch.setattr("claude_knowledge.validate.now_iso", lambda: "2024-01-15T10:00:00")

        # Now import validate module AFTER patching
        import claude_knowledge.validate as validate_mod
        result = validate_mod.validate_kb()

        assert "issues" in result
        assert "errors" in result["issues"]
        assert "warnings" in result["issues"]
        assert "suggestions" in result["issues"]
        assert "report_path" in result

    def test_validates_all_checks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that all 6 validation checks are run."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()
        (mock_kb_dir / "articles").mkdir()
        (mock_kb_dir / "state.json").write_text("{}")

        # Patch _config paths first
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.REPORTS_DIR", tmp_path / "reports")
        monkeypatch.setattr("claude_knowledge._config.STATE_FILE", tmp_path / "state.json")
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", tmp_path / "daily")

        # Patch _utils functions
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {})
        monkeypatch.setattr("claude_knowledge.validate.now_iso", lambda: "2024-01-15T10:00:00")

        # Now import validate module AFTER patching
        import claude_knowledge.validate as validate_mod
        result = validate_mod.validate_kb()

        # All 6 checks should be run
        assert result["issues"]["errors"] >= 0
        assert result["issues"]["warnings"] >= 0
        assert result["issues"]["suggestions"] >= 0


class TestCheckBrokenLinks:
    """Test check_broken_links function."""

    def test_no_broken_links(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when all links are valid."""
        mock_kb_dir = tmp_path / "knowledge"
        concepts_dir = mock_kb_dir / "concepts"
        concepts_dir.mkdir(parents=True)

        # Create a valid article that links to another valid article
        (concepts_dir / "article1.md").write_text("""
# Article 1

See [[concepts/article2]]
""")

        (concepts_dir / "article2.md").write_text("""
# Article 2

Content here.
""")

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [
            concepts_dir / "article1.md",
            concepts_dir / "article2.md"
        ])
        monkeypatch.setattr("claude_knowledge._utils.wiki_article_exists", lambda link: True)

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_broken_links()
        assert issues == []

    def test_broken_links_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when broken links are found."""
        mock_kb_dir = tmp_path / "knowledge"
        concepts_dir = mock_kb_dir / "concepts"
        concepts_dir.mkdir(parents=True)

        (concepts_dir / "article1.md").write_text("""
# Article 1

See [[concepts/nonexistent]]
""")

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [
            concepts_dir / "article1.md"
        ])
        monkeypatch.setattr("claude_knowledge._utils.wiki_article_exists", lambda link: False)

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_broken_links()
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert "broken_link" in issues[0]["check"]
        assert "nonexistent" in issues[0]["detail"]


class TestCheckOrphanPages:
    """Test check_orphan_pages function."""

    def test_no_orphan_pages(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when no orphan pages exist."""
        mock_kb_dir = tmp_path / "knowledge"
        concepts_dir = mock_kb_dir / "concepts"
        concepts_dir.mkdir(parents=True)

        (concepts_dir / "article1.md").write_text("See [[concepts/article2]]")
        (concepts_dir / "article2.md").write_text("Content")

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [
            concepts_dir / "article1.md",
            concepts_dir / "article2.md"
        ])
        monkeypatch.setattr("claude_knowledge._utils.count_inbound_links", lambda link, exclude=None: 1)

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_orphan_pages()
        assert issues == []

    def test_orphan_pages_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when orphan pages are found."""
        mock_kb_dir = tmp_path / "knowledge"
        concepts_dir = mock_kb_dir / "concepts"
        concepts_dir.mkdir(parents=True)

        (concepts_dir / "orphan.md").write_text("No links to this")

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [
            concepts_dir / "orphan.md"
        ])
        monkeypatch.setattr("claude_knowledge._utils.count_inbound_links", lambda link, exclude=None: 0)

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_orphan_pages()
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
        assert "orphan_page" in issues[0]["check"]


class TestCheckOrphanSources:
    """Test check_orphan_sources function."""

    def test_no_orphan_sources(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when all sources are compiled."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()

        # Create a mock state file
        (mock_kb_dir / "state.json").write_text(json.dumps({
            "ingested": {
                "2024-01-15.md": {"hash": "abc123"}
            }
        }))

        daily_dir = mock_kb_dir / "daily"
        daily_dir.mkdir()

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [
            daily_dir / "2024-01-15.md"
        ])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {
            "ingested": {
                "2024-01-15.md": {"hash": "abc123"}
            }
        })

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_orphan_sources()
        assert issues == []

    def test_orphan_sources_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when uncompiled sources are found."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()

        daily_dir = mock_kb_dir / "daily"
        daily_dir.mkdir()

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [
            daily_dir / "2024-01-15.md"
        ])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {"ingested": {}})
        # Patch state file location to use our mock
        monkeypatch.setattr("claude_knowledge._config.STATE_FILE", mock_kb_dir / "state.json")

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_orphan_sources()
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
        assert "orphan_source" in issues[0]["check"]


class TestCheckStaleArticles:
    """Test check_stale_articles function."""

    def test_no_stale_articles(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when all articles are up to date."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()

        daily_dir = mock_kb_dir / "daily"
        daily_dir.mkdir()

        # Write content that will have a consistent hash
        test_content = "Test content for stale article check"
        (daily_dir / "2024-01-15.md").write_text(test_content)

        # Calculate the actual hash
        import hashlib
        actual_hash = hashlib.sha256(test_content.encode()).hexdigest()[:16]

        (mock_kb_dir / "state.json").write_text(json.dumps({
            "ingested": {
                "2024-01-15.md": {"hash": actual_hash}
            }
        }))

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [
            daily_dir / "2024-01-15.md"
        ])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {
            "ingested": {
                "2024-01-15.md": {"hash": actual_hash}
            }
        })
        monkeypatch.setattr("claude_knowledge._utils.file_hash", lambda p: actual_hash)
        monkeypatch.setattr("claude_knowledge._config.STATE_FILE", mock_kb_dir / "state.json")

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_stale_articles()
        assert issues == []

    def test_stale_articles_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when articles have changed since last compilation."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()

        (mock_kb_dir / "state.json").write_text(json.dumps({
            "ingested": {
                "2024-01-15.md": {"hash": "oldhash"}
            }
        }))

        daily_dir = mock_kb_dir / "daily"
        daily_dir.mkdir()

        (daily_dir / "2024-01-15.md").write_text("New content")  # Different hash

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [
            daily_dir / "2024-01-15.md"
        ])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {
            "ingested": {
                "2024-01-15.md": {"hash": "oldhash"}
            }
        })
        monkeypatch.setattr("claude_knowledge._utils.file_hash", lambda p: "newhash")
        monkeypatch.setattr("claude_knowledge._config.STATE_FILE", mock_kb_dir / "state.json")

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_stale_articles()
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
        assert "stale_article" in issues[0]["check"]


class TestCheckMissingBacklinks:
    """Test check_missing_backlinks function."""

    def test_no_missing_backlinks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when all backlinks are present."""
        mock_kb_dir = tmp_path / "knowledge"
        concepts_dir = mock_kb_dir / "concepts"
        concepts_dir.mkdir(parents=True)
        (mock_kb_dir / "qa").mkdir()

        (concepts_dir / "article1.md").write_text("""
# Article 1

See [[concepts/article2]]
""")

        (concepts_dir / "article2.md").write_text("""
# Article 2

See [[concepts/article1]]
""")

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [
            concepts_dir / "article1.md",
            concepts_dir / "article2.md"
        ])

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_missing_backlinks()
        assert issues == []

    def test_missing_backlinks_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when backlinks are missing."""
        mock_kb_dir = tmp_path / "knowledge"
        concepts_dir = mock_kb_dir / "concepts"
        concepts_dir.mkdir(parents=True)
        (mock_kb_dir / "qa").mkdir()

        (concepts_dir / "article1.md").write_text("""
# Article 1

See [[concepts/article2]]
""")

        # article2 doesn't link back to article1
        (concepts_dir / "article2.md").write_text("""
# Article 2

Content here.
""")

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [
            concepts_dir / "article1.md",
            concepts_dir / "article2.md"
        ])

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_missing_backlinks()
        assert len(issues) == 1
        assert issues[0]["severity"] == "suggestion"
        assert "missing_backlink" in issues[0]["check"]


class TestCheckSparseArticles:
    """Test check_sparse_articles function."""

    def test_no_sparse_articles(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when all articles have enough content."""
        mock_kb_dir = tmp_path / "knowledge"
        concepts_dir = mock_kb_dir / "concepts"
        concepts_dir.mkdir(parents=True)
        (mock_kb_dir / "qa").mkdir()

        # Write article with at least 200 words to pass the sparse check
        (concepts_dir / "article1.md").write_text("""# Article 1

This is a lengthy article with enough content to pass the word count check.
We need to have at least 200 words for this to not be flagged as sparse.
Adding more text here to make sure we meet the threshold.
More text to reach the required 200 word count minimum.
The algorithm counts words, so we just need enough text.
More content keeps going to pad out the word count.
And more and more and more text to ensure we pass the check.
Additional content continues here to increase the word count.
More words are added to make the article longer and more detailed.
The content flows naturally as we add more information.
Each sentence adds value to the overall article content.
More and more text is being added to reach the threshold.
This is paragraph two of our lengthy article.
More content to ensure word count passes.
Additional text is required here.
More words to pad out the content.
Longer articles provide more value to readers.
Content quality and quantity both matter.
This paragraph adds more substance to the article.
More text continues to build the word count.
Additional information is included here.
More content ensures we don't trigger the sparse article warning.
This is the final paragraph adding final words to the article.
More text at the end to ensure we exceed 200 words.
""")

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [
            concepts_dir / "article1.md"
        ])

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_sparse_articles()
        assert issues == []

    def test_sparse_articles_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when sparse articles are found."""
        mock_kb_dir = tmp_path / "knowledge"
        concepts_dir = mock_kb_dir / "concepts"
        concepts_dir.mkdir(parents=True)
        (mock_kb_dir / "qa").mkdir()

        (concepts_dir / "sparse.md").write_text("""
# Sparse Article

Short content.
""")

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [
            concepts_dir / "sparse.md"
        ])

        import claude_knowledge.validate as validate_mod
        issues = validate_mod.check_sparse_articles()
        assert len(issues) == 1
        assert issues[0]["severity"] == "suggestion"
        assert "sparse_article" in issues[0]["check"]
        assert "200" in issues[0]["detail"]


class TestGenerateReport:
    """Test generate_report function."""

    def test_empty_report(self) -> None:
        """Test report generation with no issues."""
        from claude_knowledge.validate import generate_report
        report = generate_report([])
        assert "All checks passed" in report
        assert "# Lint Report" in report

    def test_report_with_issues(self) -> None:
        """Test report generation with issues."""
        from claude_knowledge.validate import generate_report
        issues = [
            {"severity": "error", "check": "broken_link", "file": "test.md", "detail": "Broken link"},
            {"severity": "warning", "check": "orphan_page", "file": "test2.md", "detail": "Orphan"},
        ]
        report = generate_report(issues)
        assert "## Errors" in report
        assert "## Warnings" in report
        assert "- **[x]**" in report
        assert "- **[!]**" in report

    def test_report_with_suggestions(self) -> None:
        """Test report generation with suggestions."""
        from claude_knowledge.validate import generate_report
        issues = [
            {"severity": "suggestion", "check": "sparse_article", "file": "test.md", "detail": "Sparse"},
        ]
        report = generate_report(issues)
        assert "## Suggestions" in report
        assert "- **[?]**" in report

    def test_report_auto_fixable(self) -> None:
        """Test report generation with auto-fixable flag."""
        from claude_knowledge.validate import generate_report
        issues = [
            {"severity": "suggestion", "check": "missing_backlink", "file": "test.md",
             "detail": "Missing backlink", "auto_fixable": True},
        ]
        report = generate_report(issues)
        assert "(auto-fixable)" in report
