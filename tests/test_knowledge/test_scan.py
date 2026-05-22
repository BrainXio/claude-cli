"""Tests for claude_knowledge.scan."""

from pathlib import Path
import json

from claude_knowledge.scan import scan_prototypes, _detect_language


class TestDetectLanguage:
    """Test _detect_language function."""

    def test_python_pyproject(self) -> None:
        """Test detection of Python project via pyproject.toml."""
        assert _detect_language("pyproject.toml") == "python"

    def test_python_setup_py(self) -> None:
        """Test detection of Python project via setup.py."""
        assert _detect_language("setup.py") == "python"

    def test_python_requirements(self) -> None:
        """Test detection of Python project via requirements.txt."""
        assert _detect_language("requirements.txt") == "python"

    def test_javascript(self) -> None:
        """Test detection of JavaScript project."""
        assert _detect_language("package.json") == "javascript"

    def test_rust(self) -> None:
        """Test detection of Rust project."""
        assert _detect_language("Cargo.toml") == "rust"

    def test_go(self) -> None:
        """Test detection of Go project."""
        assert _detect_language("go.mod") == "go"

    def test_java(self) -> None:
        """Test detection of Java project."""
        assert _detect_language("pom.xml") == "java"
        assert _detect_language("build.gradle") == "java"

    def test_cpp(self) -> None:
        """Test detection of C++ project."""
        assert _detect_language("CMakeLists.txt") == "cpp"

    def test_unknown(self) -> None:
        """Test unknown sentinel returns 'unknown'."""
        assert _detect_language("unknown.toml") == "unknown"


class TestScanPrototypes:
    """Test scan_prototypes function."""

    def test_no_prototypes(self, tmp_path: Path) -> None:
        """Test scanning directory with no projects."""
        result = scan_prototypes(tmp_path)
        assert result == []

    def test_single_python_project(self, tmp_path: Path) -> None:
        """Test detection of single Python project."""
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("[project]\nname = 'myproject'")

        result = scan_prototypes(tmp_path)

        assert len(result) == 1
        assert result[0]["path"] == str(project_dir)
        assert result[0]["name"] == "myproject"
        assert result[0]["language"] == "python"
        assert result[0]["sentinel"] == "pyproject.toml"

    def test_single_rust_project(self, tmp_path: Path) -> None:
        """Test detection of single Rust project."""
        project_dir = tmp_path / "rustproject"
        project_dir.mkdir()
        (project_dir / "Cargo.toml").write_text("[package]\nname = 'rustproject'")

        result = scan_prototypes(tmp_path)

        assert len(result) == 1
        assert result[0]["language"] == "rust"

    def test_single_javascript_project(self, tmp_path: Path) -> None:
        """Test detection of single JavaScript project."""
        project_dir = tmp_path / "jsproject"
        project_dir.mkdir()
        (project_dir / "package.json").write_text('{"name": "jsproject"}')

        result = scan_prototypes(tmp_path)

        assert len(result) == 1
        assert result[0]["language"] == "javascript"

    def test_nested_projects_ignored(self, tmp_path: Path) -> None:
        """Test that nested projects in same tree are not double-counted."""
        # Create a structure like: root/project1/src/project2
        project1 = tmp_path / "project1"
        project2 = project1 / "src" / "project2"
        project2.mkdir(parents=True)

        (project1 / "pyproject.toml").write_text("[project]")
        (project2 / "pyproject.toml").write_text("[project]")

        result = scan_prototypes(tmp_path)

        # Only project1 should be counted
        assert len(result) == 1
        assert result[0]["path"] == str(project1)

    def test_multiple_projects(self, tmp_path: Path) -> None:
        """Test detection of multiple different projects."""
        python_dir = tmp_path / "pythonproj"
        python_dir.mkdir()
        (python_dir / "pyproject.toml").write_text("[project]")

        rust_dir = tmp_path / "rustproj"
        rust_dir.mkdir()
        (rust_dir / "Cargo.toml").write_text("[package]")

        js_dir = tmp_path / "jsproj"
        js_dir.mkdir()
        (js_dir / "package.json").write_text('{"name": "jsproj"}')

        result = scan_prototypes(tmp_path)

        assert len(result) == 3

    def test_output_file_write(self, tmp_path: Path) -> None:
        """Test writing shortlist to output file."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("[project]")

        output_file = tmp_path / "output" / "shortlist.json"

        result = scan_prototypes(tmp_path, output_file=output_file)

        assert len(result) == 1
        assert output_file.parent.exists()
        assert output_file.exists()

        content = json.loads(output_file.read_text())
        assert len(content) == 1
        assert content[0]["language"] == "python"

    def test_empty_directory_handling(self, tmp_path: Path) -> None:
        """Test scanning an empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = scan_prototypes(empty_dir)

        assert result == []

    def test_sentinel_file_detection(self, tmp_path: Path) -> None:
        """Test all sentinel files are detected."""
        for sentinel, expected_lang in [
            ("pyproject.toml", "python"),
            ("setup.py", "python"),
            ("requirements.txt", "python"),
            ("package.json", "javascript"),
            ("Cargo.toml", "rust"),
            ("go.mod", "go"),
            ("pom.xml", "java"),
            ("build.gradle", "java"),
            ("CMakeLists.txt", "cpp"),
        ]:
            project_dir = tmp_path / f"proj_{sentinel}"
            project_dir.mkdir()
            (project_dir / sentinel).write_text("dummy content")

            result = scan_prototypes(tmp_path)
            langs = [r["language"] for r in result if r["path"] == str(project_dir)]
            assert expected_lang in langs, f"Failed to detect {sentinel}"

    def test_directory_resolution(self, tmp_path: Path) -> None:
        """Test that paths are resolved correctly."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("[project]")

        result = scan_prototypes(project_dir)

        assert len(result) == 1
        assert Path(result[0]["path"]).resolve() == project_dir.resolve()
