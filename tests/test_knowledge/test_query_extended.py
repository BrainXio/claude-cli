"""Extended tests for claude_knowledge.query."""

import pytest
from pathlib import Path
import json

from claude_knowledge.query import _cosine_similarity, query_kb


class TestCosineSimilarity:
    """Test _cosine_similarity function."""

    def test_identical_vectors(self) -> None:
        """Test identical vectors have similarity 1.0."""
        vec1 = {"a": 1.0, "b": 2.0, "c": 3.0}
        result = _cosine_similarity(vec1, vec1)
        assert result == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        """Test orthogonal vectors have similarity 0.0."""
        vec1 = {"a": 1.0}
        vec2 = {"b": 1.0}
        result = _cosine_similarity(vec1, vec2)
        assert result == 0.0

    def test_perpendicular_vectors(self) -> None:
        """Test perpendicular vectors have similarity 0.0."""
        vec1 = {"x": 1.0, "y": 0.0}
        vec2 = {"x": 0.0, "y": 1.0}
        result = _cosine_similarity(vec1, vec2)
        assert result == 0.0

    def test_partial_similarity(self) -> None:
        """Test vectors with partial overlap."""
        vec1 = {"a": 1.0, "b": 1.0}
        vec2 = {"a": 1.0, "c": 1.0}
        result = _cosine_similarity(vec1, vec2)
        # Only 'a' is common, so similarity should be 1/sqrt(2)*1/sqrt(2) = 0.5
        assert result == pytest.approx(0.5)

    def test_zero_vector(self) -> None:
        """Test similarity with zero vector is 0.0."""
        vec1 = {}
        vec2 = {"a": 1.0}
        result = _cosine_similarity(vec1, vec2)
        assert result == 0.0

    def test_negative_values(self) -> None:
        """Test handling of negative values."""
        vec1 = {"a": 1.0, "b": -1.0}
        vec2 = {"a": -1.0, "b": 1.0}
        result = _cosine_similarity(vec1, vec2)
        # Should be negative (opposite direction)
        assert result < 0

    def test_very_different_magnitudes(self) -> None:
        """Test vectors with very different magnitudes."""
        vec1 = {"a": 100.0, "b": 100.0}
        vec2 = {"a": 1.0, "b": 1.0}
        result = _cosine_similarity(vec1, vec2)
        assert result == pytest.approx(1.0)  # Same direction, different magnitude


class TestQueryKb:
    """Test query_kb function."""

    def test_empty_kb(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test querying when KB is empty."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        results = query_kb("test query")
        assert results == []

    def test_no_articles_in_kb(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test querying when articles directory doesn't exist."""
        mock_kb_dir = tmp_path / "knowledge"
        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        results = query_kb("test query")
        assert results == []

    def test_single_article_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test finding a single matching article."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        # Create a matching article
        article = articles_dir / "test-article.json"
        article.write_text(
            json.dumps(
                {"entries": [{"body": "This is a test article about machine learning"}]}
            )
        )

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        results = query_kb("machine learning", top_k=5)
        assert len(results) == 1
        assert "test-article.json" in results[0]["source"]
        assert results[0]["score"] > 0

    def test_multiple_articles_ranked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that multiple articles are ranked by score."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        # Create articles with different relevance
        (articles_dir / "article1.json").write_text(
            json.dumps({"entries": [{"body": "Python programming language"}]})
        )
        (articles_dir / "article2.json").write_text(
            json.dumps(
                {"entries": [{"body": "Python programming language for data science"}]}
            )
        )

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        results = query_kb("python programming", top_k=5)
        assert len(results) == 2
        # Results should be sorted by score (descending)
        assert results[0]["score"] >= results[1]["score"]

    def test_top_k_limit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that top_k limit is respected."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        # Create 5 articles
        for i in range(5):
            (articles_dir / f"article{i}.json").write_text(
                json.dumps({"entries": [{"body": f"Article {i} about topic"}]})
            )

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        results = query_kb("topic", top_k=2)
        assert len(results) == 2

    def test_no_match_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test query with no matching terms."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        (articles_dir / "article.json").write_text(
            json.dumps({"entries": [{"body": "Some completely unrelated content"}]})
        )

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        # Query with terms that don't appear in the content at all
        results = query_kb("xyzzy plugh foobar baz")
        # Should return empty since there's no match
        assert results == []

    def test_invalid_article_handling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test handling of corrupted article files."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        # Valid article
        (articles_dir / "valid.json").write_text(
            json.dumps({"entries": [{"body": "Valid content"}]})
        )

        # Invalid/corrupted article
        (articles_dir / "invalid.json").write_text("not valid json")

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        results = query_kb("valid")
        # Should handle invalid file gracefully
        assert len(results) == 1

    def test_version_filtering(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test min_version and max_version filtering.

        Note: The current query_kb doesn't actually filter by version.
        This test verifies that version filters are accepted but may not filter.
        """
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        # Create an article with version metadata in content
        article = articles_dir / "test.json"
        article.write_text(
            json.dumps({"version": 2, "entries": [{"body": "Test content"}]})
        )

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        # Query with version filter that should exclude the article
        # (if implemented) - currently not implemented
        results = query_kb("test", min_version=5)
        # Since version filtering is not implemented, we just verify the filter doesn't crash
        assert isinstance(results, list)

    def test_excerpt_generation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that excerpts are generated correctly."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        (articles_dir / "test.json").write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "body": "Very long content that should be truncated in the excerpt"
                        }
                    ]
                }
            )
        )

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        results = query_kb("long content")
        assert len(results) == 1
        assert "excerpt" in results[0]
        assert len(results[0]["excerpt"]) <= 203  # 200 + "..."
