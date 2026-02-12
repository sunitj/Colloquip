"""Tests for deployment infrastructure: settings, logging, metrics."""

import json
import os
from unittest.mock import patch

# --- Settings ---


class TestSettings:
    def test_default_settings(self):
        from colloquip.settings import load_settings

        settings = load_settings()
        assert settings.deployment.environment == "development"
        assert settings.embedding.provider == "mock"
        assert settings.memory.store == "in_memory"

    def test_settings_from_env(self):
        from colloquip.settings import load_settings

        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
                "EMBEDDING_PROVIDER": "openai",
                "MEMORY_STORE": "pgvector",
                "LOG_LEVEL": "WARNING",
                "WATCHER_POLL_INTERVAL": "600",
                "MAX_COST_PER_THREAD_USD": "10.0",
            },
        ):
            settings = load_settings()
            assert settings.deployment.environment == "production"
            assert settings.embedding.provider == "openai"
            assert settings.memory.store == "pgvector"
            assert settings.deployment.log_level == "WARNING"
            assert settings.watchers.poll_interval == 600
            assert settings.deployment.max_cost_per_thread_usd == 10.0

    def test_cors_origins_parsing(self):
        from colloquip.settings import load_settings

        with patch.dict(
            os.environ,
            {
                "CORS_ORIGINS": "https://app.example.com,https://admin.example.com",
            },
        ):
            settings = load_settings()
            assert len(settings.deployment.cors_origins) == 2
            assert "https://app.example.com" in settings.deployment.cors_origins

    def test_database_settings_default(self):
        from colloquip.settings import load_settings

        settings = load_settings()
        assert "sqlite" in settings.database.url


# --- Logging ---


class TestLogging:
    def test_configure_text_logging(self):
        from colloquip.logging_config import configure_logging

        configure_logging(level="DEBUG", fmt="text")

    def test_configure_json_logging(self):
        from colloquip.logging_config import configure_logging

        configure_logging(level="INFO", fmt="json")

    def test_request_id_filter(self):
        from colloquip.logging_config import RequestIdFilter, request_id_var

        filt = RequestIdFilter()
        import logging

        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        result = filt.filter(record)
        assert result is True
        assert record.request_id == "-"

        token = request_id_var.set("abc123")
        filt.filter(record)
        assert record.request_id == "abc123"
        request_id_var.reset(token)

    def test_json_formatter(self):
        import logging

        from colloquip.logging_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "test message", (), None)
        record.request_id = "test-id"
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "test message"
        assert data["level"] == "INFO"
        assert data["request_id"] == "test-id"

    def test_generate_request_id(self):
        from colloquip.logging_config import generate_request_id

        rid = generate_request_id()
        assert len(rid) == 12
        assert rid.isalnum()


# --- Metrics ---


class TestMetrics:
    def test_metrics_counters(self):
        from colloquip.metrics import (
            deliberations_total,
            memory_retrievals_total,
            notifications_total,
            watcher_events_total,
        )

        # These should be callable without error (NoOp or real)
        deliberations_total.inc()
        memory_retrievals_total.inc()
        watcher_events_total.labels(watcher_type="literature").inc()
        notifications_total.inc()

    def test_metrics_histograms(self):
        from colloquip.metrics import (
            deliberation_cost_usd,
            deliberation_duration_seconds,
            memory_retrieval_latency_seconds,
        )

        deliberation_duration_seconds.observe(5.0)
        deliberation_cost_usd.observe(0.5)
        memory_retrieval_latency_seconds.observe(0.01)

    def test_metrics_gauge(self):
        from colloquip.metrics import memory_store_size

        memory_store_size.set(42)

    def test_track_duration(self):
        from colloquip.metrics import (
            memory_retrieval_latency_seconds,
            track_duration,
        )

        with track_duration(memory_retrieval_latency_seconds):
            pass  # Simulate fast operation

    def test_get_metrics_text(self):
        from colloquip.metrics import get_metrics_text

        output = get_metrics_text()
        assert isinstance(output, bytes)


# --- Docker/Config file existence ---


class TestFileExistence:
    def test_dockerfile_exists(self):
        assert os.path.exists("/home/user/Colloquip/Dockerfile")

    def test_dockerfile_dev_exists(self):
        assert os.path.exists("/home/user/Colloquip/Dockerfile.dev")

    def test_docker_compose_exists(self):
        assert os.path.exists("/home/user/Colloquip/docker-compose.yml")

    def test_dockerignore_exists(self):
        assert os.path.exists("/home/user/Colloquip/.dockerignore")

    def test_env_example_exists(self):
        assert os.path.exists("/home/user/Colloquip/.env.example")

    def test_ci_workflow_exists(self):
        assert os.path.exists("/home/user/Colloquip/.github/workflows/ci.yml")

    def test_deploy_workflow_exists(self):
        assert os.path.exists("/home/user/Colloquip/.github/workflows/deploy.yml")

    def test_alembic_ini_exists(self):
        assert os.path.exists("/home/user/Colloquip/alembic.ini")

    def test_alembic_env_exists(self):
        assert os.path.exists("/home/user/Colloquip/alembic/env.py")

    def test_migration_files_exist(self):
        versions_dir = "/home/user/Colloquip/alembic/versions"
        assert os.path.exists(f"{versions_dir}/001_baseline_schema.py")
        assert os.path.exists(f"{versions_dir}/002_phase3_memory_tables.py")
        assert os.path.exists(f"{versions_dir}/003_phase4_watcher_tables.py")
        assert os.path.exists(f"{versions_dir}/004_phase5_crossref_outcome_tables.py")

    def test_production_config_exists(self):
        assert os.path.exists("/home/user/Colloquip/config/production.yaml")

    def test_staging_config_exists(self):
        assert os.path.exists("/home/user/Colloquip/config/staging.yaml")
