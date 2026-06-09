#!/usr/bin/env bash
set -euo pipefail

export UV_INDEX_STRATEGY=unsafe-best-match
export UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

uv sync --no-install-package torch "$@"
uv pip install "torch>=2.6.0" --index-url https://download.pytorch.org/whl/cpu
