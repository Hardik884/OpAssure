"""Shared pytest fixtures: generate the synthetic dataset once per test session."""

import pytest

from src.common.synthetic import generate_all


@pytest.fixture(scope="session")
def tables():
    """In-memory generated tables (does not touch disk)."""
    return generate_all()
