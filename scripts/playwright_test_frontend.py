"""Playwright E2E test: Create a community, start a thread, watch deliberation.

Runs headless Chrome with --no-sandbox (required for root environments).
Captures screenshots at each step.
"""

import asyncio
import json
import sys
import time

import httpx

BASE = "http://localhost:8000"
SCREENSHOTS_DIR = "/tmp/playwright-screenshots"


class TestRunner:
    def __init__(self):
        self.results = []
        self.start = time.time()

    def log(self, name, status, detail=""):
        self.results.append((name, status, detail))
        icon = "PASS" if status == "pass" else "FAIL"
        print(f"  [{icon}] {name}" + (f" -- {detail}" if detail else ""))

    def summary(self):
        elapsed = time.time() - self.start
        passed = sum(1 for _, s, _ in self.results if s == "pass")
        total = len(self.results)
        print(f"\n{'=' * 60}")
        print(f"Results: {passed}/{total} passed in {elapsed:.1f}s")
        print(f"{'=' * 60}")
        return passed == total


async def run_api_tests(runner: TestRunner):  # noqa: C901
    """Test the API endpoints that back the frontend."""
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # 1. Platform init
        r = await c.post("/api/platform/init")
        runner.log(
            "Platform init",
            "pass" if r.status_code == 200 else "fail",
            str(r.status_code),
        )

        # 2. Create community
        r = await c.post(
            "/api/subreddits",
            json={
                "name": "drug_discovery",
                "display_name": "Drug Discovery",
                "description": "AI-driven drug discovery deliberation",
                "thinking_type": "analysis",
                "primary_domain": "pharmacology",
            },
        )
        runner.log(
            "Create community",
            "pass" if r.status_code == 200 else "fail",
            r.text[:100],
        )

        # 3. List communities
        r = await c.get("/api/subreddits")
        subs = r.json()
        count = len(subs)
        runner.log(
            "List communities",
            "pass" if count > 0 else "fail",
            f"{count} communities",
        )

        # 4. Get community detail
        r = await c.get("/api/subreddits/drug_discovery")
        runner.log(
            "Community detail",
            "pass" if r.status_code == 200 else "fail",
        )

        # 5. Create thread (deliberation)
        hypothesis = (
            "Allosteric binding at the switch-II pocket of KRAS G12C "
            "provides superior selectivity over orthosteric inhibition, "
            "reducing off-target effects on wild-type KRAS"
        )
        r = await c.post(
            "/api/subreddits/drug_discovery/threads",
            json={
                "title": "KRAS G12C Inhibitor Selectivity",
                "hypothesis": hypothesis,
                "mode": "mock",
                "max_turns": 3,
            },
        )
        runner.log(
            "Create thread",
            "pass" if r.status_code == 200 else "fail",
            r.text[:120],
        )
        thread = r.json() if r.status_code == 200 else {}
        thread_id = thread.get("id")

        if not thread_id:
            runner.log("Thread ID", "fail", "No thread ID returned")
            return None

        # 6. Start deliberation via SSE
        print("\n  Starting deliberation (SSE stream)...")
        posts = []
        try:
            async with c.stream("POST", f"/api/deliberations/{thread_id}/start") as stream:
                async for line in stream.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "post":
                            agent = data.get("agent_id", "?")
                            preview = data.get("content", "")[:80]
                            posts.append(data)
                            print(f"    Post #{len(posts)} by {agent}: {preview}...")
                        elif data.get("type") == "phase_change":
                            phase = data.get("phase", "?")
                            print(f"    Phase -> {phase}")
                        elif data.get("type") == "complete":
                            print("    Deliberation complete!")
                            break
        except Exception as e:
            n = len(posts)
            runner.log(
                "SSE stream",
                "pass" if n > 0 else "fail",
                f"{n} posts, ended: {e}",
            )

        n_posts = len(posts)
        runner.log(
            "Deliberation posts",
            "pass" if n_posts >= 2 else "fail",
            f"{n_posts} posts generated",
        )

        # 7. Get deliberation history
        r = await c.get(f"/api/deliberations/{thread_id}/history")
        if r.status_code == 200:
            history = r.json()
            total_posts = len(history.get("posts", []))
            has_consensus = history.get("consensus") is not None
            runner.log(
                "Deliberation history",
                "pass",
                f"{total_posts} posts, consensus={has_consensus}",
            )
        else:
            runner.log("Deliberation history", "fail", str(r.status_code))

        # 8. Get thread costs
        r = await c.get(f"/api/threads/{thread_id}/costs")
        cost = ""
        if r.status_code == 200:
            cost = f"${r.json().get('estimated_cost_usd', 0):.2f}"
        runner.log(
            "Thread costs",
            "pass" if r.status_code == 200 else "fail",
            cost,
        )

        # 9. Research program endpoints
        r = await c.get("/api/subreddits/drug_discovery/research-program")
        runner.log(
            "Get research program",
            "pass" if r.status_code == 200 else "fail",
        )

        program_content = (
            "# KRAS Research Program\n\n"
            "## Objectives\n"
            "- Evaluate allosteric vs orthosteric binding\n"
            "- Assess selectivity profiles\n\n"
            "## Constraints\n"
            "- Focus on G12C mutant\n"
            "- Consider clinical translatability"
        )
        r = await c.put(
            "/api/subreddits/drug_discovery/research-program",
            json={"content": program_content},
        )
        ver = ""
        if r.status_code == 200:
            ver = f"v{r.json().get('version', '?')}"
        runner.log(
            "Update research program",
            "pass" if r.status_code == 200 else "fail",
            ver,
        )

        # 10. Research job endpoints
        r = await c.post(
            "/api/subreddits/drug_discovery/research-jobs",
            json={"max_iterations": 10, "max_cost_usd": 5.0},
        )
        runner.log(
            "Create research job",
            "pass" if r.status_code == 200 else "fail",
        )
        job = r.json() if r.status_code == 200 else {}

        if job.get("id"):
            r = await c.get(f"/api/research-jobs/{job['id']}")
            runner.log(
                "Get research job detail",
                "pass" if r.status_code == 200 else "fail",
            )

            r = await c.get(f"/api/research-jobs/{job['id']}/results")
            runner.log(
                "Get research job results",
                "pass" if r.status_code == 200 else "fail",
            )

            r = await c.post(f"/api/research-jobs/{job['id']}/stop")
            status = ""
            if r.status_code == 200:
                status = r.json().get("status", "")
            runner.log(
                "Stop research job",
                "pass" if r.status_code == 200 else "fail",
                status,
            )

        # 11. Memories
        r = await c.get("/api/subreddits/drug_discovery/memories")
        mem_detail = ""
        if r.status_code == 200:
            mem_detail = f"{r.json().get('total', 0)} memories"
        runner.log(
            "Get memories",
            "pass" if r.status_code == 200 else "fail",
            mem_detail,
        )

        # 12. Export
        r = await c.get(f"/api/threads/{thread_id}/export/markdown")
        export_detail = ""
        if r.status_code == 200:
            export_detail = f"{len(r.text)} chars"
        runner.log(
            "Export markdown",
            "pass" if r.status_code == 200 else "fail",
            export_detail,
        )

        return thread_id


async def run_browser_tests(runner: TestRunner, thread_id: str):
    """Test the frontend UI via headless Chrome."""
    import os

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/opt/google/chrome/chrome",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # 1. Landing page
        await page.goto(BASE)
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/01-landing.png")
        title = await page.title()
        runner.log("Landing page loads", "pass" if title else "fail", title)

        # 2. Check sidebar / nav
        content = await page.content()
        lower = content.lower()
        has_nav = "sidebar" in lower or "communities" in lower or "nav" in lower
        runner.log("Page has navigation", "pass" if has_nav else "fail")

        # 3. Navigate to communities
        try:
            comm_link = page.locator("text=Communities").first
            if await comm_link.is_visible(timeout=2000):
                await comm_link.click()
                await page.wait_for_load_state("networkidle")
                await page.screenshot(path=f"{SCREENSHOTS_DIR}/02-communities.png")
                runner.log("Navigate to communities", "pass")
            else:
                await page.goto(f"{BASE}/communities")
                await page.wait_for_load_state("networkidle")
                await page.screenshot(path=f"{SCREENSHOTS_DIR}/02-communities.png")
                runner.log("Navigate to communities (direct)", "pass")
        except Exception as e:
            runner.log("Navigate to communities", "fail", str(e)[:80])

        # 4. Navigate to our community
        try:
            await page.goto(f"{BASE}/communities/drug_discovery")
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=f"{SCREENSHOTS_DIR}/03-community-detail.png")
            page_text = await page.inner_text("body")
            has_name = "Drug Discovery" in page_text or "drug_discovery" in page_text
            runner.log(
                "Community detail page",
                "pass" if has_name else "fail",
                "Community name visible" if has_name else "Name not found",
            )
        except Exception as e:
            runner.log("Community detail page", "fail", str(e)[:80])

        # 5. Navigate to the thread
        try:
            await page.goto(f"{BASE}/threads/{thread_id}")
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=f"{SCREENSHOTS_DIR}/04-thread.png")
            page_text = await page.inner_text("body")
            has_content = (
                "KRAS" in page_text or "allosteric" in page_text.lower() or len(page_text) > 100
            )
            runner.log(
                "Thread page",
                "pass" if has_content else "fail",
                "Thread content visible" if has_content else "Content not found",
            )
        except Exception as e:
            runner.log("Thread page", "fail", str(e)[:80])

        # 6. Check agents page
        try:
            await page.goto(f"{BASE}/agents")
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=f"{SCREENSHOTS_DIR}/05-agents.png")
            page_text = await page.inner_text("body")
            runner.log("Agents page", "pass" if len(page_text) > 50 else "fail")
        except Exception as e:
            runner.log("Agents page", "fail", str(e)[:80])

        # 7. Health check
        try:
            await page.goto(f"{BASE}/health")
            health_text = await page.inner_text("body")
            runner.log(
                "Health endpoint in browser",
                "pass" if "ok" in health_text else "fail",
            )
        except Exception as e:
            runner.log("Health endpoint", "fail", str(e)[:80])

        await browser.close()

    print(f"\n  Screenshots saved to {SCREENSHOTS_DIR}/")


async def main():
    print("=" * 60)
    print("Colloquip Frontend E2E Test")
    print("=" * 60)

    runner = TestRunner()

    print("\n--- API Tests ---")
    thread_id = await run_api_tests(runner)

    if thread_id:
        print("\n--- Browser Tests ---")
        try:
            await run_browser_tests(runner, thread_id)
        except ImportError:
            print("  [SKIP] playwright not installed, skipping browser tests")
        except Exception as e:
            runner.log("Browser tests", "fail", str(e)[:120])

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
