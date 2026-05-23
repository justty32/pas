#!/usr/bin/env bash
# py_linter.sh — switch demo 用的假 Python linter。讀 stdin，回報「以 Python 規則檢查」。

set -euo pipefail

if [[ "${1:-}" == "--metadata" ]]; then
  printf '{"lifecycle": "one_shot", "state": "stateless"}\n'
  exit 0
fi

echo "[py_linter] 以 Python 語言規則檢查輸入："
cat -
