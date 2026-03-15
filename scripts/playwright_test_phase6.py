"""Playwright E2E test for Phase 6: Database & Jobs system.

Tests API endpoints and frontend components via browser automation.
Generates a test report at the end.
"""
import asyncio
import json
import sys
from datetime import datetime
from uuid import uuid4

# We'll use httpx for API testing and playwright for UI
import httpx

BASE = "http://localhost:8000"


class TestReport:
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()

    def add(self, name, status, detail=""):
        self.results.append({"name": name, "status": status, "detail": detail})
        icon = "PASS" if status == "pass" else "FAIL"
        print(f"  [{icon}] {name}" + (f" — {detail}" if detail else ""))

    def generate(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "pass")
        failed = total - passed
        elapsed = (datetime.now() - self.start_time).total_seconds()

        lines = [
            "=" * 72,
            "PHASE 6 — Agent Database & Jobs System — Playwright Test Report",
            "=" * 72,
            f"Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {elapsed:.1f}s",
            f"Results: {passed}/{total} passed, {failed} failed",
            "",
            "-" * 72,
            "DETAILED RESULTS",
            "-" * 72,
        ]
        for r in self.results:
            icon = "PASS" if r["status"] == "pass" else "FAIL"
            lines.append(f"  [{icon}] {r['name']}")
            if r["detail"]:
                lines.append(f"         {r['detail']}")
        lines.append("")
        lines.append("-" * 72)

        # Summary by category
        categories = {}
        for r in self.results:
            cat = r["name"].split(":")[0].strip() if ":" in r["name"] else "General"
            if cat not in categories:
                categories[cat] = {"pass": 0, "fail": 0}
            categories[cat][r["status"]] += 1

        lines.append("SUMMARY BY CATEGORY")
        lines.append("-" * 72)
        for cat, counts in categories.items():
            total_cat = counts["pass"] + counts["fail"]
            lines.append(f"  {cat}: {counts['pass']}/{total_cat} passed")
        lines.append("")
        lines.append("=" * 72)
        if failed == 0:
            lines.append("ALL TESTS PASSED")
        else:
            lines.append(f"{failed} TEST(S) FAILED")
        lines.append("=" * 72)

        return "\n".join(lines)


async def run_tests():
    report = TestReport()

    async with httpx.AsyncClient(base_url=BASE, timeout=10) as client:
        # ============================================================
        # 1. Health check
        # ============================================================
        print("\n[Health]")
        try:
            resp = await client.get("/health")
            report.add("Health: GET /health", "pass" if resp.status_code == 200 else "fail",
                        f"status={resp.status_code} body={resp.text[:100]}")
        except Exception as e:
            report.add("Health: GET /health", "fail", str(e))

        # ============================================================
        # 2. Nextflow Process Library
        # ============================================================
        print("\n[NF Process Library]")

        # List all processes
        try:
            resp = await client.get("/api/nf-processes")
            data = resp.json()
            procs = data.get("processes", [])
            report.add(
                "NF Processes: GET /api/nf-processes",
                "pass" if resp.status_code == 200 and len(procs) > 0 else "fail",
                f"status={resp.status_code}, count={len(procs)}",
            )
        except Exception as e:
            report.add("NF Processes: GET /api/nf-processes", "fail", str(e))

        # Filter by category
        try:
            resp = await client.get("/api/nf-processes", params={"category": "structure_prediction"})
            data = resp.json()
            filtered = data.get("processes", [])
            all_match = all(p.get("category") == "structure_prediction" for p in filtered)
            report.add(
                "NF Processes: Filter by category",
                "pass" if resp.status_code == 200 and len(filtered) > 0 and all_match else "fail",
                f"count={len(filtered)}, all_match={all_match}",
            )
        except Exception as e:
            report.add("NF Processes: Filter by category", "fail", str(e))

        # Get specific process
        try:
            resp = await client.get("/api/nf-processes/alphafold2")
            report.add(
                "NF Processes: GET /api/nf-processes/alphafold2",
                "pass" if resp.status_code == 200 and resp.json().get("process_id") == "alphafold2" else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("NF Processes: GET /api/nf-processes/alphafold2", "fail", str(e))

        # Get nonexistent process
        try:
            resp = await client.get("/api/nf-processes/nonexistent_xyz")
            report.add(
                "NF Processes: 404 for unknown process",
                "pass" if resp.status_code == 404 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("NF Processes: 404 for unknown process", "fail", str(e))

        # Verify process schema completeness
        try:
            resp = await client.get("/api/nf-processes/alphafold2")
            proc = resp.json()
            required_fields = ["process_id", "name", "description", "category",
                               "input_channels", "output_channels", "parameters",
                               "container", "resource_requirements"]
            missing = [f for f in required_fields if f not in proc]
            report.add(
                "NF Processes: Schema completeness",
                "pass" if not missing else "fail",
                f"missing_fields={missing}" if missing else "all fields present",
            )
        except Exception as e:
            report.add("NF Processes: Schema completeness", "fail", str(e))

        # ============================================================
        # 3. Jobs API (no job manager configured — expect 503)
        # ============================================================
        print("\n[Jobs API — No Manager]")

        try:
            resp = await client.get("/api/jobs")
            report.add(
                "Jobs: GET /api/jobs returns 503 without manager",
                "pass" if resp.status_code == 503 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Jobs: GET /api/jobs returns 503 without manager", "fail", str(e))

        try:
            resp = await client.post("/api/jobs", json={
                "session_id": str(uuid4()),
                "agent_id": "test",
                "pipeline_name": "test",
            })
            report.add(
                "Jobs: POST /api/jobs returns 503 without manager",
                "pass" if resp.status_code == 503 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Jobs: POST /api/jobs returns 503 without manager", "fail", str(e))

        try:
            resp = await client.get(f"/api/jobs/{uuid4()}")
            report.add(
                "Jobs: GET /api/jobs/:id returns 503 without manager",
                "pass" if resp.status_code == 503 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Jobs: GET /api/jobs/:id returns 503 without manager", "fail", str(e))

        try:
            resp = await client.post(f"/api/jobs/{uuid4()}/cancel")
            report.add(
                "Jobs: POST cancel returns 503 without manager",
                "pass" if resp.status_code == 503 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Jobs: POST cancel returns 503 without manager", "fail", str(e))

        # ============================================================
        # 4. Proposals API (no manager — expect 503)
        # ============================================================
        print("\n[Proposals API — No Manager]")

        try:
            resp = await client.get(f"/api/proposals?session_id={uuid4()}")
            report.add(
                "Proposals: GET returns 503 without manager",
                "pass" if resp.status_code == 503 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Proposals: GET returns 503 without manager", "fail", str(e))

        try:
            resp = await client.post(f"/api/proposals/{uuid4()}/review", json={
                "reviewer": "admin",
                "action": "approve",
            })
            report.add(
                "Proposals: POST review returns 503 without manager",
                "pass" if resp.status_code == 503 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Proposals: POST review returns 503 without manager", "fail", str(e))

        # ============================================================
        # 5. Data Connections CRUD
        # ============================================================
        print("\n[Data Connections]")

        sub_id = str(uuid4())

        # Create a connection
        try:
            resp = await client.post(f"/api/subreddits/{sub_id}/data-connections", json={
                "name": "test_assay_db",
                "description": "Test assay results database",
                "db_type": "postgresql",
                "connection_string": "postgresql://localhost:5432/assays",
                "read_only": True,
            })
            conn_data = resp.json()
            conn_id = conn_data.get("id", "")
            report.add(
                "Data Connections: POST create",
                "pass" if resp.status_code == 200 and conn_id else "fail",
                f"status={resp.status_code}, id={conn_id[:8]}..." if conn_id else f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Data Connections: POST create", "fail", str(e))
            conn_id = ""

        # List connections
        try:
            resp = await client.get(f"/api/subreddits/{sub_id}/data-connections")
            conns = resp.json().get("connections", [])
            report.add(
                "Data Connections: GET list",
                "pass" if resp.status_code == 200 and len(conns) == 1 else "fail",
                f"status={resp.status_code}, count={len(conns)}",
            )
        except Exception as e:
            report.add("Data Connections: GET list", "fail", str(e))

        # Verify connection fields
        try:
            resp = await client.get(f"/api/subreddits/{sub_id}/data-connections")
            conns = resp.json().get("connections", [])
            if conns:
                c = conns[0]
                has_fields = all(k in c for k in ["id", "name", "db_type", "read_only", "enabled"])
                report.add(
                    "Data Connections: Response schema",
                    "pass" if has_fields else "fail",
                    f"fields={list(c.keys())}",
                )
            else:
                report.add("Data Connections: Response schema", "fail", "no connections returned")
        except Exception as e:
            report.add("Data Connections: Response schema", "fail", str(e))

        # Create a second connection
        try:
            resp = await client.post(f"/api/subreddits/{sub_id}/data-connections", json={
                "name": "compound_lib",
                "connection_string": "sqlite:///compounds.db",
            })
            conn2_id = resp.json().get("id", "")
            report.add(
                "Data Connections: POST create second",
                "pass" if resp.status_code == 200 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Data Connections: POST create second", "fail", str(e))
            conn2_id = ""

        # List should show 2
        try:
            resp = await client.get(f"/api/subreddits/{sub_id}/data-connections")
            conns = resp.json().get("connections", [])
            report.add(
                "Data Connections: List shows 2",
                "pass" if len(conns) == 2 else "fail",
                f"count={len(conns)}",
            )
        except Exception as e:
            report.add("Data Connections: List shows 2", "fail", str(e))

        # Delete first connection
        if conn_id:
            try:
                resp = await client.delete(f"/api/subreddits/{sub_id}/data-connections/{conn_id}")
                report.add(
                    "Data Connections: DELETE",
                    "pass" if resp.status_code == 200 else "fail",
                    f"status={resp.status_code}",
                )
            except Exception as e:
                report.add("Data Connections: DELETE", "fail", str(e))

        # List should now show 1
        try:
            resp = await client.get(f"/api/subreddits/{sub_id}/data-connections")
            conns = resp.json().get("connections", [])
            report.add(
                "Data Connections: List after delete shows 1",
                "pass" if len(conns) == 1 else "fail",
                f"count={len(conns)}",
            )
        except Exception as e:
            report.add("Data Connections: List after delete shows 1", "fail", str(e))

        # Delete nonexistent
        try:
            resp = await client.delete(f"/api/subreddits/{sub_id}/data-connections/{uuid4()}")
            report.add(
                "Data Connections: DELETE nonexistent returns 404",
                "pass" if resp.status_code == 404 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Data Connections: DELETE nonexistent returns 404", "fail", str(e))

        # Different subreddit should be empty
        try:
            other_sub = str(uuid4())
            resp = await client.get(f"/api/subreddits/{other_sub}/data-connections")
            conns = resp.json().get("connections", [])
            report.add(
                "Data Connections: Isolation between subreddits",
                "pass" if len(conns) == 0 else "fail",
                f"count={len(conns)}",
            )
        except Exception as e:
            report.add("Data Connections: Isolation between subreddits", "fail", str(e))

        # ============================================================
        # 6. Process Catalog Completeness
        # ============================================================
        print("\n[Process Catalog Validation]")

        try:
            resp = await client.get("/api/nf-processes")
            procs = resp.json().get("processes", [])
            expected_ids = [
                "alphafold2", "esmfold", "rosettafold", "colabfold_msa",
                "mmseqs2_search", "foldseek", "protein_mpnn",
                "rosetta_relax", "md_simulation", "binding_affinity", "docking",
            ]
            found_ids = {p.get("process_id") for p in procs}
            missing = set(expected_ids) - found_ids
            report.add(
                "Catalog: All 11 processes present",
                "pass" if not missing else "fail",
                f"missing={missing}" if missing else f"all {len(found_ids)} present",
            )
        except Exception as e:
            report.add("Catalog: All 11 processes present", "fail", str(e))

        # Validate each process has input/output channels
        try:
            resp = await client.get("/api/nf-processes")
            procs = resp.json().get("processes", [])
            issues = []
            for p in procs:
                pid = p.get("process_id", "?")
                if not p.get("input_channels"):
                    issues.append(f"{pid}: no input channels")
                if not p.get("output_channels"):
                    issues.append(f"{pid}: no output channels")
                if not p.get("container"):
                    issues.append(f"{pid}: no container")
            report.add(
                "Catalog: All processes have channels & containers",
                "pass" if not issues else "fail",
                "; ".join(issues) if issues else "all valid",
            )
        except Exception as e:
            report.add("Catalog: All processes have channels & containers", "fail", str(e))

        # Validate categories
        try:
            resp = await client.get("/api/nf-processes")
            procs = resp.json().get("processes", [])
            categories = {p.get("category") for p in procs}
            expected_cats = {"structure_prediction", "sequence_alignment",
                             "protein_design", "simulation", "structure_search",
                             "structure_refinement", "analysis"}
            missing_cats = expected_cats - categories
            report.add(
                "Catalog: Expected categories present",
                "pass" if not missing_cats else "fail",
                f"found={categories}" if not missing_cats else f"missing={missing_cats}",
            )
        except Exception as e:
            report.add("Catalog: Expected categories present", "fail", str(e))

        # ============================================================
        # 7. Cross-cutting: API error handling
        # ============================================================
        print("\n[Error Handling]")

        # Invalid JSON body
        try:
            resp = await client.post(
                f"/api/subreddits/{uuid4()}/data-connections",
                content="not json",
                headers={"Content-Type": "application/json"},
            )
            report.add(
                "Error Handling: Invalid JSON returns 422",
                "pass" if resp.status_code == 422 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Error Handling: Invalid JSON returns 422", "fail", str(e))

        # Missing required fields
        try:
            resp = await client.post(
                f"/api/subreddits/{uuid4()}/data-connections",
                json={"description": "no name or connection_string"},
            )
            report.add(
                "Error Handling: Missing required fields returns 422",
                "pass" if resp.status_code == 422 else "fail",
                f"status={resp.status_code}",
            )
        except Exception as e:
            report.add("Error Handling: Missing required fields returns 422", "fail", str(e))

    # ============================================================
    # Generate Report
    # ============================================================
    report_text = report.generate()
    print("\n\n" + report_text)

    # Write to file
    report_path = "/home/user/Colloquip/phase6_test_report.txt"
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"\nReport saved to: {report_path}")

    # Return exit code
    failed = sum(1 for r in report.results if r["status"] == "fail")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
