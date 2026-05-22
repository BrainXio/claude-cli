"""Tests for claude_quality.modes."""

from claude_quality.modes import Mode, get_mode, get_mode_thresholds, set_mode


def test_get_mode_default() -> None:
    assert get_mode() == Mode.DEVELOPER


def test_set_and_get_mode() -> None:
    set_mode(Mode.RESEARCH)
    assert get_mode() == Mode.RESEARCH
    # restore
    set_mode(Mode.DEVELOPER)


def test_get_mode_thresholds() -> None:
    thresholds = get_mode_thresholds(Mode.REVIEW)
    assert thresholds["quality_gate_strict"] is True
    assert thresholds["allow_auto_format"] is False


def test_mode_enum_values() -> None:
    """Test that all Mode enum values are defined correctly."""
    assert Mode.DEVELOPER.value == "developer"
    assert Mode.RESEARCH.value == "research"
    assert Mode.REVIEW.value == "review"
    assert Mode.OPS.value == "ops"
    assert Mode.PERSONAL.value == "personal"


def test_get_mode_thresholds_for_all_modes() -> None:
    """Test thresholds for all mode types."""
    for mode in Mode:
        thresholds = get_mode_thresholds(mode)
        assert "description" in thresholds
        assert "quality_gate_strict" in thresholds
        assert "allow_auto_format" in thresholds
        assert "max_complexity" in thresholds


def test_mode_thresholds_specific_values() -> None:
    """Test specific threshold values for each mode."""
    # Developer: strict gates, auto-format allowed, max complexity 10
    dev = get_mode_thresholds(Mode.DEVELOPER)
    assert dev["quality_gate_strict"] is True
    assert dev["allow_auto_format"] is True
    assert dev["max_complexity"] == 10

    # Research: lenient gates, auto-format allowed, max complexity 20
    research = get_mode_thresholds(Mode.RESEARCH)
    assert research["quality_gate_strict"] is False
    assert research["allow_auto_format"] is True
    assert research["max_complexity"] == 20

    # Review: strict gates, no auto-format, max complexity 8
    review = get_mode_thresholds(Mode.REVIEW)
    assert review["quality_gate_strict"] is True
    assert review["allow_auto_format"] is False
    assert review["max_complexity"] == 8

    # Ops: focused on operations
    ops = get_mode_thresholds(Mode.OPS)
    assert ops["quality_gate_strict"] is True
    assert ops["allow_auto_format"] is True
    assert ops["max_complexity"] == 12

    # Personal: permissive, max complexity 30
    personal = get_mode_thresholds(Mode.PERSONAL)
    assert personal["quality_gate_strict"] is False
    assert personal["allow_auto_format"] is True
    assert personal["max_complexity"] == 30


def test_get_mode_thresholds_default_to_current_mode(monkeypatch) -> None:
    """Test that get_mode_thresholds without argument uses current mode."""
    # Set mode to RESEARCH
    set_mode(Mode.RESEARCH)

    # Mock get_mode to return RESEARCH
    from claude_quality import modes

    def mock_get_mode():
        return Mode.REVIEW

    monkeypatch.setattr(modes, "get_mode", mock_get_mode)

    thresholds = get_mode_thresholds(None)
    assert thresholds["quality_gate_strict"] is True  # REVIEW mode
    assert thresholds["allow_auto_format"] is False  # REVIEW mode
    assert thresholds["max_complexity"] == 8  # REVIEW mode

    # Restore
    set_mode(Mode.DEVELOPER)


def test_get_mode_with_invalid_json(monkeypatch, tmp_path) -> None:
    """Test that get_mode falls back to DEVELOPER when JSON is invalid."""
    state_file = tmp_path / ".claude" / "mode_state.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("invalid json {")

    from claude_quality import modes as modes_module
    monkeypatch.setattr(modes_module, "_STATE_FILE", state_file)

    result = get_mode()
    assert result == Mode.DEVELOPER


def test_get_mode_with_invalid_mode_value(monkeypatch, tmp_path) -> None:
    """Test that get_mode falls back to DEVELOPER when mode value is invalid."""
    state_file = tmp_path / ".claude" / "mode_state.json"
    state_file.parent.mkdir(parents=True)
    import json
    state_file.write_text(json.dumps({"mode": "invalid_mode"}))

    from claude_quality import modes as modes_module
    monkeypatch.setattr(modes_module, "_STATE_FILE", state_file)

    result = get_mode()
    assert result == Mode.DEVELOPER


def test_get_mode_with_os_error(monkeypatch, tmp_path) -> None:
    """Test that get_mode falls back to DEVELOPER when file read fails."""
    import json
    state_file = tmp_path / ".claude" / "mode_state.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps({"mode": "developer"}))

    from claude_quality import modes as modes_module
    monkeypatch.setattr(modes_module, "_STATE_FILE", state_file)

    # Monkeypatch the json.loads call to raise OSError
    import json as json_module
    original_loads = json_module.loads

    def mock_loads(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(json_module, "loads", mock_loads)

    result = get_mode()
    assert result == Mode.DEVELOPER


def test_get_mode_thresholds_custom_mode() -> None:
    """Test get_mode_thresholds with a specific mode argument."""
    thresholds = get_mode_thresholds(Mode.PERSONAL)
    assert thresholds["max_complexity"] == 30
    assert thresholds["quality_gate_strict"] is False


def test_set_mode_creates_file(tmp_path, monkeypatch) -> None:
    """Test that set_mode creates the state file."""
    import json
    state_file = tmp_path / ".claude" / "mode_state.json"
    monkeypatch.setattr("claude_quality.modes._STATE_FILE", state_file)

    set_mode(Mode.OPS)

    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["mode"] == "ops"
    assert "thresholds" in data


def test_set_mode_overwrites_existing(tmp_path, monkeypatch) -> None:
    """Test that set_mode overwrites an existing state file."""
    import json
    state_file = tmp_path / ".claude" / "mode_state.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps({"mode": "developer"}))
    monkeypatch.setattr("claude_quality.modes._STATE_FILE", state_file)

    set_mode(Mode.REVIEW)

    data = json.loads(state_file.read_text())
    assert data["mode"] == "review"
