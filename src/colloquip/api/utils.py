"""Shared utilities for API route handlers."""

from uuid import UUID

from fastapi import HTTPException


def parse_uuid(value: str, label: str = "ID") -> UUID:
    """Parse a UUID string, raising 400 if invalid."""
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid {label}: {value!r}")
