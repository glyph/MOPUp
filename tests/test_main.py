"""Test cases for the __main__ module."""

import pytest
from click.testing import CliRunner

from mopup import __main__


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for invoking command-line interfaces."""
    return CliRunner()


def test_main_succeeds(runner: CliRunner) -> None:
    """It exits with a status code of zero."""
    result = runner.invoke(__main__.main, ["update", "--dry-run=true"])
    assert result.exit_code == 0


def test_uninstall_dry_run(runner: CliRunner) -> None:
    """Test uninstall with dry-run mode."""
    # Get the current Python version
    import sys

    version = f"{sys.version_info.major}.{sys.version_info.minor}"

    result = runner.invoke(__main__.main, ["uninstall", version, "--dry-run=true"])
    assert result.exit_code == 0

    # Check that it found packages
    assert "Found Python" in result.output or "No Python" in result.output


def test_uninstall_invalid_version(runner: CliRunner) -> None:
    """Test uninstall with invalid version format."""
    result = runner.invoke(__main__.main, ["uninstall", "3", "--dry-run=true"])
    assert result.exit_code == 0
    assert "Invalid version format" in result.output


def test_uninstall_nonexistent_version(runner: CliRunner) -> None:
    """Test uninstall with non-existent Python version."""
    result = runner.invoke(__main__.main, ["uninstall", "2.7", "--dry-run=true"])
    assert result.exit_code == 0
    assert "No Python 2.7 installation found" in result.output


def test_uninstall_with_force(runner: CliRunner) -> None:
    """Test uninstall with force option in dry-run mode."""
    import sys

    version = f"{sys.version_info.major}.{sys.version_info.minor}"

    result = runner.invoke(
        __main__.main, ["uninstall", version, "--dry-run=true", "--force=true"]
    )
    assert result.exit_code == 0

    # Should complete without errors about extra files
    assert "Found Python" in result.output or "No Python" in result.output


@pytest.mark.destructive
def test_main_update_real(runner: CliRunner) -> None:
    """Test real update (downloads but doesn't install due to being up-to-date)."""
    result = runner.invoke(__main__.main, ["update"])
    assert result.exit_code == 0
    # Should find that we're already up-to-date or need an update
    assert "update" in result.output.lower()


@pytest.mark.destructive
def test_uninstall_interactive(runner: CliRunner) -> None:
    """Test uninstall with interactive mode (won't actually uninstall)."""
    import sys

    version = f"{sys.version_info.major}.{sys.version_info.minor}"

    # With interactive=true and no actual user input, this should exit cleanly
    result = runner.invoke(
        __main__.main, ["uninstall", version, "--interactive=true"], input="no\n"
    )
    assert result.exit_code == 0
    assert "Found Python" in result.output or "No Python" in result.output
