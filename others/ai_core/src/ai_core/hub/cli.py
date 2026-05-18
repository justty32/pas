"""ai-core-hub one-shot CLI 入口點（§7.1）。"""
from __future__ import annotations


def main() -> None:
    """掃描指定函式目錄，把結果輸出到 stdout 或指定路徑。

    支援旗標：
    --build-list <dir>                      掃描後印 list.txt 格式到 stdout
      [--ext .sh,.py]                       改用副檔名過濾（§7.5）
      [--recursive]                         遞迴子目錄（預設只掃頂層）

    --export <format> <dir>                 格式轉換後輸出到 stdout
      format 可為 mcp | openai-tools | anthropic-tools | claude-skill | agent-md | functions-md
      [--out <dir>]                         搭配 claude-skill，指定各 skill 的輸出目錄

    --gen-agent-md <dir>                    產生 AGENTS.md 到 stdout（§15.2）
    --gen-functions-md <dir>               產生 auto/FUNCTIONS.md 到 stdout

    --metadata                              印 hub 自身 metadata 後 exit
    --json-errors                           stderr 改輸出 JSON 格式錯誤
    """
    pass
