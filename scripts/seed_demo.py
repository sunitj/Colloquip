#!/usr/bin/env python3
"""Seed the Colloquium platform with demo data.

Creates 4 communities with 10-15 threads of varying topics.
Threads are run using real LLM to produce authentic deliberation content.

Usage:
    # Backend must be running first:
    uv run uvicorn colloquip.api:create_app --factory --port 8000

    # Then seed:
    uv run python scripts/seed_demo.py

    # Use --mock flag for fast seeding without API keys:
    uv run python scripts/seed_demo.py --mock

    # Seed only communities (no deliberations):
    uv run python scripts/seed_demo.py --communities-only
"""

import argparse
import asyncio
import json
import logging
import time

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

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
        {
            "title": "Gut-Brain Axis in Parkinson's Disease",
            "hypothesis": (
                "Alpha-synuclein aggregation initiates in the enteric nervous system "
                "and propagates to the CNS via the vagus nerve, suggesting that early "
                "intervention targeting gut microbiome composition could delay PD onset."
            ),
            "max_turns": 10,
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
) -> dict:
    """Create a thread in a community."""
    payload = {
        "title": thread_config["title"],
        "hypothesis": thread_config["hypothesis"],
        "mode": mode,
        "max_turns": thread_config.get("max_turns", 15),
    }
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
    # Create the deliberation session
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
        # Session may already exist
        logger.warning("Session %s may already exist, trying to start anyway", session_id)
    else:
        create_resp.raise_for_status()

    # Start the deliberation via SSE and consume events
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
            elif line.startswith("event: phase_change"):
                pass  # Phase changes logged via data
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


async def run_seed(mode: str = "real", communities_only: bool = False, concurrency: int = 2):
    """Main seeding routine."""
    timeout = httpx.Timeout(10.0, read=300.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # 1) Initialize platform
        await init_platform(client)

        # 2) Create all communities
        for community_config in COMMUNITIES:
            await create_community(client, community_config)

        if communities_only:
            logger.info("Communities created. Skipping deliberations (--communities-only).")
            return

        # 3) Create all threads and collect launch tasks
        launch_tasks = []
        for community_name, threads in THREADS.items():
            for thread_config in threads:
                thread_data = await create_thread(client, community_name, thread_config, mode)
                launch_tasks.append({
                    "session_id": thread_data["id"],
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


def main():
    parser = argparse.ArgumentParser(description="Seed Colloquium with demo data")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM mode (no API keys needed, fast but less realistic)",
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
    args = parser.parse_args()

    mode = "mock" if args.mock else "real"
    concurrency = args.concurrency if not args.mock else max(args.concurrency, 4)

    logger.info("Seeding in %s mode (concurrency=%d)...", mode, concurrency)
    asyncio.run(
        run_seed(mode=mode, communities_only=args.communities_only, concurrency=concurrency)
    )


if __name__ == "__main__":
    main()
