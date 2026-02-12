"""Load and validate agent personas from YAML files."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Default personas directory (alongside this module)
_PERSONAS_DIR = Path(__file__).parent / "personas"


def load_persona_file(path: Path) -> dict:
    """Load a single persona YAML file and validate its structure."""
    with open(path) as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Empty persona file: {path}")

    required_fields = [
        "agent_type",
        "display_name",
        "expertise_tags",
        "knowledge_scope",
        "persona_prompt",
        "evaluation_criteria",
        "phase_mandates",
        "domain_keywords",
        "is_red_team",
    ]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Persona {path.name} missing fields: {missing}")

    # Validate evaluation_criteria sum to ~1.0
    criteria = data["evaluation_criteria"]
    total = sum(criteria.values())
    if not (0.95 <= total <= 1.05):
        raise ValueError(f"Persona {path.name}: evaluation_criteria sum to {total}, expected ~1.0")

    # Validate phase mandates
    expected_phases = {"explore", "debate", "deepen", "converge"}
    actual_phases = set(data["phase_mandates"].keys())
    if not expected_phases.issubset(actual_phases):
        missing_phases = expected_phases - actual_phases
        raise ValueError(f"Persona {path.name} missing phase mandates: {missing_phases}")

    # Validate non-empty list fields (critical for registry matching)
    for list_field in ("expertise_tags", "domain_keywords"):
        if not data.get(list_field):
            raise ValueError(f"Persona {path.name}: '{list_field}' must be a non-empty list")

    # Validate persona_prompt is non-trivial
    if not data.get("persona_prompt", "").strip():
        raise ValueError(f"Persona {path.name}: 'persona_prompt' must not be empty")

    return data


def load_all_personas(
    personas_dir: Optional[Path] = None,
) -> Dict[str, dict]:
    """Load all persona YAML files from a directory.

    Returns dict mapping agent_type -> persona data.
    """
    directory = personas_dir or _PERSONAS_DIR
    if not directory.exists():
        logger.warning("Personas directory not found: %s", directory)
        return {}

    personas: Dict[str, dict] = {}
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = load_persona_file(path)
            agent_type = data["agent_type"]
            if agent_type in personas:
                logger.warning(
                    "Duplicate agent_type '%s' in %s (overwriting previous)",
                    agent_type,
                    path.name,
                )
            personas[agent_type] = data
            logger.debug("Loaded persona: %s from %s", agent_type, path.name)
        except Exception as e:
            logger.error("Failed to load persona %s: %s", path.name, e)

    logger.info("Loaded %d personas from %s", len(personas), directory)
    return personas


def persona_to_agent_identity(persona: dict) -> "BaseAgentIdentity":
    """Convert a raw persona dict to a BaseAgentIdentity model.

    Lazy import to avoid circular dependency with models.py.
    """
    from colloquip.models import BaseAgentIdentity

    agent_type = persona.get("agent_type", "<unknown>")
    try:
        return BaseAgentIdentity(
            agent_type=persona["agent_type"],
            display_name=persona["display_name"],
            expertise_tags=persona["expertise_tags"],
            persona_prompt=persona["persona_prompt"],
            phase_mandates=persona["phase_mandates"],
            domain_keywords=persona["domain_keywords"],
            knowledge_scope=persona["knowledge_scope"],
            evaluation_criteria=persona["evaluation_criteria"],
            is_red_team=persona["is_red_team"],
        )
    except KeyError as e:
        raise ValueError(f"Persona '{agent_type}' missing required field: {e}") from e


def load_agent_identities(
    personas_dir: Optional[Path] = None,
) -> List["BaseAgentIdentity"]:
    """Load all personas and convert to BaseAgentIdentity models."""
    personas = load_all_personas(personas_dir)
    return [persona_to_agent_identity(p) for p in personas.values()]


def get_persona_by_type(
    agent_type: str,
    personas_dir: Optional[Path] = None,
) -> Optional[dict]:
    """Load a specific persona by agent_type."""
    personas = load_all_personas(personas_dir)
    return personas.get(agent_type)
