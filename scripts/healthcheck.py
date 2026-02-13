#!/usr/bin/env python3
"""Standalone health check script for Docker/k8s probes."""

import sys
import urllib.request


def main() -> int:
    url = "http://localhost:8000/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            if resp.status == 200:
                return 0
    except Exception:
        pass
    return 1


if __name__ == "__main__":
    sys.exit(main())
