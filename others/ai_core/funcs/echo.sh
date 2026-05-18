#!/usr/bin/env bash
# echo.sh — 把 --input 指定的檔案原樣寫入 --output
# 用途：測試 pipeline 是否正確傳遞檔案；也是最簡單的 --metadata 協議範例
#
# 用法：
#   echo.sh --input src.txt --output dst.txt
#   echo.sh --input src.txt                  # 未指定 --output 時寫到 stdout
#   echo.sh --metadata                       # 印 metadata JSON 後 exit 0

set -euo pipefail

INPUT=""
OUTPUT=""

# --- 解析旗標 ---
# 逐一處理 $@ 中的旗標，支援 --input <path>、--output <path>、--metadata

# --- --metadata 模式 ---
# 印出符合 §4.5 規範的 JSON 後 exit 0
# 內容對應 docs/ 中的 echo.sh metadata 範例

# --- 一般執行模式 ---
# 驗 --input 存在，不存在時 stderr 報錯 + exit 1
# 若有 --output：把 input 內容寫到 output
# 若無 --output：把 input 內容寫到 stdout
