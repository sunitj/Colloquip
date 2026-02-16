#!/usr/bin/env python3
"""Seed the Colloquium platform with demo data.

Creates 5 communities with 16 threads of varying topics.
Threads are run using real LLM to produce authentic deliberation content.
After seeding, export the DB + manifest so it can be reloaded instantly
after a database reset.

Usage:
    # Backend must be running first:
    uv run uvicorn colloquip.api:create_app --factory --port 8000

    # Seed with real LLM (authentic content, needs ANTHROPIC_API_KEY):
    uv run python scripts/seed_demo.py

    # Export after seeding (saves DB + manifest for reload):
    uv run python scripts/seed_demo.py --export

    # Reload from fixture (instant, no API keys needed):
    uv run python scripts/seed_demo.py --load-fixture

    # Mock mode for testing the pipeline (fast, shallow content):
    uv run python scripts/seed_demo.py --mock
"""

import argparse
import asyncio
import json
import logging
import shutil
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = PROJECT_ROOT / "demo" / "fixtures"
FIXTURE_DB = FIXTURE_DIR / "seed.db"
FIXTURE_MANIFEST = FIXTURE_DIR / "manifest.json"
# Default SQLite DB location (relative to where the server runs, typically project root)
DEFAULT_DB = PROJECT_ROOT / "colloquip.db"

# ---------------------------------------------------------------------------
# Community definitions
# ---------------------------------------------------------------------------

COMMUNITIES = [
    {
        "name": "neuropharmacology",
        "display_name": "Neuropharmacology",
        "description": (
            "Drug repurposing and novel therapeutic strategies for neurological diseases. "
            "Focus on translational evidence from metabolic pathways to CNS targets."
        ),
        "primary_domain": "drug_discovery",
        "thinking_type": "assessment",
        "required_expertise": ["biology", "chemistry", "admet", "clinical", "regulatory"],
        "max_agents": 8,
    },
    {
        "name": "enzyme_engineering",
        "display_name": "Enzyme Engineering",
        "description": (
            "Computational and directed-evolution approaches to designing novel enzymes "
            "for industrial and environmental applications."
        ),
        "primary_domain": "protein_engineering",
        "thinking_type": "assessment",
        "required_expertise": ["biology", "chemistry", "computational", "synth_bio"],
        "max_agents": 8,
    },
    {
        "name": "immuno_oncology",
        "display_name": "Immuno-Oncology",
        "description": (
            "Evaluating combination immunotherapy strategies, biomarker identification, "
            "and resistance mechanisms in solid tumors."
        ),
        "primary_domain": "drug_discovery",
        "thinking_type": "assessment",
        "required_expertise": ["biology", "clinical", "regulatory"],
        "max_agents": 7,
    },
    {
        "name": "synbio_manufacturing",
        "display_name": "Synthetic Biology & Biomanufacturing",
        "description": (
            "Cell factory design, metabolic pathway engineering, and scale-up challenges "
            "for sustainable chemical production."
        ),
        "primary_domain": "protein_engineering",
        "thinking_type": "assessment",
        "required_expertise": ["biology", "chemistry", "synth_bio", "computational"],
        "max_agents": 7,
    },
    {
        "name": "microbiome_therapeutics",
        "display_name": "Microbiome Therapeutics",
        "description": (
            "Translating microbiome science into clinical interventions. "
            "Covers FMT, engineered probiotics, metabolomics-guided therapy, "
            "and the gut-brain/gut-immune axes."
        ),
        "primary_domain": "drug_discovery",
        "thinking_type": "assessment",
        "required_expertise": ["biology", "chemistry", "clinical", "regulatory", "synth_bio"],
        "max_agents": 8,
    },
]

# ---------------------------------------------------------------------------
# Thread definitions — grouped by community
# ---------------------------------------------------------------------------

THREADS = {
    "neuropharmacology": [
        {
            "title": "GLP-1 Agonists for Alzheimer's Disease",
            "hypothesis": (
                "Repurposing GLP-1 receptor agonists (semaglutide) for Alzheimer's "
                "disease is a viable therapeutic strategy, given emerging evidence of "
                "neuroinflammatory pathway modulation and improved cognitive outcomes "
                "in diabetic cohorts."
            ),
            "max_turns": 15,
        },
        {
            "title": "Psychedelic-Assisted Therapy for Treatment-Resistant Depression",
            "hypothesis": (
                "Psilocybin-assisted therapy produces durable antidepressant effects "
                "through 5-HT2A-mediated neuroplasticity and default mode network "
                "reorganization, and can be safely integrated into clinical practice "
                "at scale."
            ),
            "max_turns": 12,
        },
        {
            "title": "CRISPR Base Editing for Huntington's Disease",
            "hypothesis": (
                "Adenine base editors delivered via AAV9 can selectively silence mutant "
                "HTT alleles in striatal neurons with sufficient efficiency and specificity "
                "to halt disease progression in early-stage Huntington's patients."
            ),
            "max_turns": 12,
        },
    ],
    "enzyme_engineering": [
        {
            "title": "Engineered PETases for Industrial Plastic Degradation",
            "hypothesis": (
                "Engineered PETase variants can achieve sufficient catalytic efficiency "
                "and thermostability for commercially viable industrial PET plastic "
                "degradation within 5 years."
            ),
            "max_turns": 15,
        },
        {
            "title": "De Novo Enzyme Design via Diffusion Models",
            "hypothesis": (
                "Protein diffusion models (RFdiffusion, Chroma) can generate functional "
                "enzymes with novel folds and catalytic activities not found in nature, "
                "surpassing directed evolution in efficiency for de novo design."
            ),
            "max_turns": 12,
        },
        {
            "title": "Thermostable Cellulases for Lignocellulose Conversion",
            "hypothesis": (
                "Consensus-designed cellulase chimeras with thermostability above 80°C "
                "can reduce enzyme loading requirements by 5x in second-generation "
                "bioethanol production, making cellulosic ethanol cost-competitive."
            ),
            "max_turns": 10,
        },
    ],
    "immuno_oncology": [
        {
            "title": "Bispecific Antibodies vs CAR-T in Solid Tumors",
            "hypothesis": (
                "Bispecific T-cell engagers targeting HER2×CD3 will demonstrate "
                "superior tumor penetration and safety profiles compared to HER2-directed "
                "CAR-T cells in HER2-low breast cancer, due to their smaller molecular "
                "size and lack of cytokine storm risk."
            ),
            "max_turns": 12,
        },
        {
            "title": "Neoantigens and Personalized Cancer Vaccines",
            "hypothesis": (
                "mRNA-based personalized neoantigen vaccines combined with anti-PD1 "
                "checkpoint blockade can achieve durable complete responses in >30% of "
                "microsatellite-stable colorectal cancer patients, a population that "
                "currently does not respond to immunotherapy alone."
            ),
            "max_turns": 12,
        },
        {
            "title": "Tumor Microenvironment Reprogramming via Oncolytic Viruses",
            "hypothesis": (
                "Engineered oncolytic HSV-1 armed with IL-12 and anti-PD-L1 nanobodies "
                "can convert immunologically 'cold' pancreatic tumors into 'hot' tumors "
                "amenable to checkpoint inhibitor therapy."
            ),
            "max_turns": 10,
        },
    ],
    "synbio_manufacturing": [
        {
            "title": "Cell-Free Systems for Pharmaceutical Manufacturing",
            "hypothesis": (
                "Cell-free protein synthesis systems can produce complex biologics "
                "(glycosylated antibodies) at manufacturing scale with comparable quality "
                "attributes to CHO-based systems, while reducing production timelines "
                "from months to days."
            ),
            "max_turns": 12,
        },
        {
            "title": "Engineered Yeast for Cannabinoid Production",
            "hypothesis": (
                "Metabolically engineered S. cerevisiae expressing a complete cannabinoid "
                "pathway can produce pharmaceutical-grade CBD at >1 g/L titer, offering "
                "a sustainable alternative to agricultural extraction."
            ),
            "max_turns": 10,
        },
        {
            "title": "CRISPR Interference for Dynamic Metabolic Control",
            "hypothesis": (
                "CRISPRi-based genetic circuits with biosensor-coupled feedback loops "
                "can dynamically balance metabolic flux in E. coli, improving production "
                "yields of non-native terpenes by >10x compared to static pathway engineering."
            ),
            "max_turns": 10,
        },
    ],
    "microbiome_therapeutics": [
        {
            "title": "FMT vs Defined Consortia for Recurrent C. difficile",
            "hypothesis": (
                "Rationally designed bacterial consortia (e.g., SER-109-like defined "
                "communities of 8-12 Firmicutes strains) will match or exceed fecal "
                "microbiota transplantation efficacy for recurrent C. difficile infection "
                "while eliminating donor-screening risks and enabling standardized "
                "manufacturing."
            ),
            "max_turns": 12,
        },
        {
            "title": "Engineered Probiotics as Living Therapeutics for IBD",
            "hypothesis": (
                "Engineered E. coli Nissle 1917 strains expressing IL-10 and "
                "anti-TNF-alpha nanobodies under inflammation-responsive promoters "
                "can achieve localized immunosuppression in the gut sufficient to "
                "maintain remission in ulcerative colitis, outperforming systemic "
                "biologics in safety profile."
            ),
            "max_turns": 12,
        },
        {
            "title": "Gut Microbiome Signatures as Predictors of Immunotherapy Response",
            "hypothesis": (
                "Pre-treatment gut microbiome composition — specifically the ratio of "
                "Akkermansia muciniphila to Bacteroides fragilis and the abundance of "
                "butyrate-producing Faecalibacterium — can predict anti-PD-1 checkpoint "
                "inhibitor response in melanoma patients with >80% accuracy, and "
                "microbiome-targeted interventions can convert non-responders."
            ),
            "max_turns": 12,
            # Cross-links with immuno_oncology — the hypothesis deliberately
            # spans both communities to test cross-reference detection.
        },
    ],
}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


async def init_platform(client: httpx.AsyncClient) -> dict:
    """Initialize the platform (loads agent personas)."""
    resp = await client.post(f"{BASE_URL}/api/platform/init")
    resp.raise_for_status()
    data = resp.json()
    logger.info("Platform initialized: %d agents loaded", data.get("agents_loaded", 0))
    return data


async def create_community(client: httpx.AsyncClient, config: dict) -> dict:
    """Create a community, or skip if it already exists."""
    resp = await client.post(f"{BASE_URL}/api/subreddits", json=config)
    if resp.status_code == 409:
        logger.info("Community '%s' already exists, skipping", config["name"])
        resp2 = await client.get(f"{BASE_URL}/api/subreddits/{config['name']}")
        resp2.raise_for_status()
        return resp2.json()
    resp.raise_for_status()
    data = resp.json()
    logger.info(
        "Created community '%s' with %d members",
        data["name"],
        data["member_count"],
    )
    return data


async def create_thread(
    client: httpx.AsyncClient,
    community_name: str,
    thread_config: dict,
    mode: str = "real",
    thread_id: str | None = None,
) -> dict:
    """Create a thread in a community."""
    payload = {
        "title": thread_config["title"],
        "hypothesis": thread_config["hypothesis"],
        "mode": mode,
        "max_turns": thread_config.get("max_turns", 15),
    }
    if thread_id:
        payload["thread_id"] = thread_id
    resp = await client.post(
        f"{BASE_URL}/api/subreddits/{community_name}/threads",
        json=payload,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info("Created thread '%s' in c/%s (id=%s)", data["title"], community_name, data["id"])
    return data


async def launch_deliberation(
    client: httpx.AsyncClient,
    session_id: str,
    community_name: str,
    hypothesis: str,
    mode: str = "real",
    max_turns: int = 15,
) -> None:
    """Launch a deliberation via the create + SSE start pattern."""
    create_resp = await client.post(
        f"{BASE_URL}/api/deliberations",
        json={
            "hypothesis": hypothesis,
            "mode": mode,
            "max_turns": max_turns,
            "community_name": community_name,
            "session_id": session_id,
        },
    )
    if create_resp.status_code == 400:
        logger.warning("Session %s may already exist, trying to start anyway", session_id)
    else:
        create_resp.raise_for_status()

    logger.info("Starting deliberation %s...", session_id)
    async with client.stream(
        "POST",
        f"{BASE_URL}/api/deliberations/{session_id}/start",
        timeout=300.0,
    ) as stream:
        post_count = 0
        async for line in stream.aiter_lines():
            if line.startswith("event: post"):
                post_count += 1
                if post_count % 3 == 0:
                    logger.info("  ...%d posts generated", post_count)
            elif line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if isinstance(data, dict) and "current_phase" in data:
                        logger.info("  Phase: %s", data["current_phase"])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif line.startswith("event: session_complete"):
                logger.info("  Deliberation complete! (%d posts)", post_count)
            elif line.startswith("event: done"):
                break
            elif line.startswith("event: error"):
                logger.error("  Error during deliberation: %s", line)
                break


# ---------------------------------------------------------------------------
# Core seeding
# ---------------------------------------------------------------------------


async def run_seed(mode: str = "real", communities_only: bool = False, concurrency: int = 2):
    """Main seeding routine. Returns manifest data for export."""
    timeout = httpx.Timeout(10.0, read=300.0)
    manifest = {"communities": [], "threads": []}

    async with httpx.AsyncClient(timeout=timeout) as client:
        # 1) Initialize platform
        await init_platform(client)

        # 2) Create all communities
        for community_config in COMMUNITIES:
            await create_community(client, community_config)
            manifest["communities"].append({
                "name": community_config["name"],
                "display_name": community_config["display_name"],
                "description": community_config["description"],
                "primary_domain": community_config["primary_domain"],
                "thinking_type": community_config["thinking_type"],
                "required_expertise": community_config["required_expertise"],
                "max_agents": community_config["max_agents"],
            })

        if communities_only:
            logger.info("Communities created. Skipping deliberations (--communities-only).")
            return manifest

        # 3) Create all threads and collect launch tasks
        launch_tasks = []
        for community_name, threads in THREADS.items():
            for thread_config in threads:
                thread_data = await create_thread(client, community_name, thread_config, mode)
                thread_id = thread_data["id"]

                manifest["threads"].append({
                    "thread_id": thread_id,
                    "community_name": community_name,
                    "title": thread_config["title"],
                    "hypothesis": thread_config["hypothesis"],
                    "max_turns": thread_config.get("max_turns", 15),
                })

                launch_tasks.append({
                    "session_id": thread_id,
                    "community_name": community_name,
                    "hypothesis": thread_config["hypothesis"],
                    "max_turns": thread_config.get("max_turns", 15),
                })

        logger.info(
            "Created %d threads across %d communities. Launching deliberations...",
            len(launch_tasks),
            len(COMMUNITIES),
        )

        # 4) Launch deliberations with controlled concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def _launch_one(task: dict):
            async with semaphore:
                t0 = time.monotonic()
                try:
                    await launch_deliberation(
                        client,
                        session_id=task["session_id"],
                        community_name=task["community_name"],
                        hypothesis=task["hypothesis"],
                        mode=mode,
                        max_turns=task["max_turns"],
                    )
                    elapsed = time.monotonic() - t0
                    logger.info(
                        "Finished '%s' in %.1fs",
                        task["community_name"],
                        elapsed,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to run deliberation %s: %s",
                        task["session_id"],
                        e,
                    )

        await asyncio.gather(*[_launch_one(task) for task in launch_tasks])

    logger.info("Seeding complete!")
    return manifest


# ---------------------------------------------------------------------------
# Export / Import fixtures
# ---------------------------------------------------------------------------


def export_fixture(manifest: dict, db_path: Path = DEFAULT_DB):
    """Copy the SQLite DB and save the manifest for later reload."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        logger.error("Database file not found at %s — cannot export.", db_path)
        sys.exit(1)

    shutil.copy2(db_path, FIXTURE_DB)
    logger.info("Exported DB -> %s (%.1f MB)", FIXTURE_DB, FIXTURE_DB.stat().st_size / 1e6)

    with open(FIXTURE_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Exported manifest -> %s (%d threads)", FIXTURE_MANIFEST, len(manifest["threads"]))


async def load_fixture(db_path: Path = DEFAULT_DB):
    """Restore the DB from fixture and recreate platform state."""
    if not FIXTURE_DB.exists():
        logger.error(
            "Fixture DB not found at %s. Run with --export first after seeding.", FIXTURE_DB
        )
        sys.exit(1)
    if not FIXTURE_MANIFEST.exists():
        logger.error("Fixture manifest not found at %s.", FIXTURE_MANIFEST)
        sys.exit(1)

    with open(FIXTURE_MANIFEST) as f:
        manifest = json.load(f)

    # 1) Restore DB file (server must be stopped or will pick up changes on next query)
    shutil.copy2(FIXTURE_DB, db_path)
    logger.info(
        "Restored DB <- %s (%.1f MB)", FIXTURE_DB, FIXTURE_DB.stat().st_size / 1e6
    )

    # 2) Wait for server to be ready
    timeout = httpx.Timeout(10.0, read=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(10):
            try:
                resp = await client.get(f"{BASE_URL}/health")
                if resp.status_code == 200:
                    break
            except httpx.ConnectError:
                pass
            logger.info("Waiting for server... (attempt %d)", attempt + 1)
            await asyncio.sleep(1)
        else:
            logger.error("Server not reachable at %s", BASE_URL)
            sys.exit(1)

        # 3) Initialize platform (loads agent personas)
        await init_platform(client)

        # 4) Recreate communities
        for community in manifest["communities"]:
            await create_community(client, community)

        # 5) Recreate thread entries with original IDs (data already in DB)
        for thread in manifest["threads"]:
            await create_thread(
                client,
                community_name=thread["community_name"],
                thread_config={
                    "title": thread["title"],
                    "hypothesis": thread["hypothesis"],
                    "max_turns": thread["max_turns"],
                },
                mode="mock",
                thread_id=thread["thread_id"],
            )
            logger.info(
                "Linked thread '%s' (%s...) in c/%s",
                thread["title"],
                thread["thread_id"][:8],
                thread["community_name"],
            )

    logger.info(
        "Fixture loaded! %d communities, %d threads restored.",
        len(manifest["communities"]),
        len(manifest["threads"]),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Seed Colloquium with demo data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First-time seed with real LLM + export:
  uv run python scripts/seed_demo.py
  uv run python scripts/seed_demo.py --export

  # Reload after DB reset (instant, no API keys):
  uv run python scripts/seed_demo.py --load-fixture

  # Dry run with mock LLM:
  uv run python scripts/seed_demo.py --mock
        """,
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM mode (no API keys needed, fast but shallow content)",
    )
    parser.add_argument(
        "--communities-only",
        action="store_true",
        help="Only create communities and threads, don't run deliberations",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Number of concurrent deliberations (default: 2, increase for mock mode)",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export current DB + manifest to demo/fixtures/ for later reload",
    )
    parser.add_argument(
        "--load-fixture",
        action="store_true",
        help="Restore DB from fixture and recreate platform state (no LLM needed)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB,
        help=f"Path to SQLite DB file (default: {DEFAULT_DB})",
    )
    args = parser.parse_args()

    # --load-fixture is a standalone operation
    if args.load_fixture:
        asyncio.run(load_fixture(db_path=args.db_path))
        return

    # --export just copies the DB and saves the manifest
    if args.export:
        if FIXTURE_MANIFEST.exists():
            with open(FIXTURE_MANIFEST) as f:
                manifest = json.load(f)
            export_fixture(manifest, db_path=args.db_path)
        else:
            logger.error(
                "No manifest found. Run seed first (without --export), then --export."
            )
            sys.exit(1)
        return

    mode = "mock" if args.mock else "real"
    concurrency = args.concurrency if not args.mock else max(args.concurrency, 4)

    logger.info("Seeding in %s mode (concurrency=%d)...", mode, concurrency)
    manifest = asyncio.run(
        run_seed(mode=mode, communities_only=args.communities_only, concurrency=concurrency)
    )

    # Auto-save manifest after seeding so --export can pick it up
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    with open(FIXTURE_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Manifest saved to %s", FIXTURE_MANIFEST)

    if not args.communities_only:
        logger.info(
            "To export for reload later: uv run python scripts/seed_demo.py --export"
        )


if __name__ == "__main__":
    main()
