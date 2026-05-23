#!/usr/bin/env bash
# c_linter.sh — switch demo 用的假 C linter。讀 stdin，回報「以 C 規則檢查」。
# 遵守 --metadata 契約（手寫 JSON，因為這是 shell 函式）。

set -euo pipefail

if [[ "${1:-}" == "--metadata" ]]; then
  # one_shot / stateless 的 shell 工具
  printf '{"lifecycle": "one_shot", "state": "stateless"}\n'
  exit 0
fi

echo "[c_linter] 以 C 語言規則檢查輸入："
cat -
