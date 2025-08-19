"""Pytest configuration and fixtures."""

from __future__ import annotations

import pytest
from pytest import Config, Item, Parser


def pytest_addoption(parser: Parser) -> None:
    """Add custom command line options."""
    parser.addoption(
        "--destructive",
        action="store_true",
        default=False,
        help="run destructive tests that may modify the system",
    )


def pytest_configure(config: Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "destructive: mark test as making actual changes to the system"
    )


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:
    """Skip destructive tests unless --destructive flag is passed."""
    if config.getoption("--destructive"):
        # --destructive given in cli: do not skip destructive tests
        return
    skip_destructive = pytest.mark.skip(reason="need --destructive option to run")
    for item in items:
        if "destructive" in item.keywords:
            item.add_marker(skip_destructive)
