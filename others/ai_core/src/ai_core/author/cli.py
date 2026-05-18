"""ai-core-author CLI 入口點（一站式函式製作工具，§8）。"""
from __future__ import annotations


def main() -> None:
    """解析 CLI 旗標，執行 generate → dry-run → register 完整流程（§8.1）。

    必填旗標：
    --spec <file>           JSON spec 檔：{name, description, examples, language?}

    可選旗標：
    --language bash|python  覆蓋 spec 的 language 欄位
    --dry-run-only          只執行 generate + dry-run，不寫入 funcs/（§8.3）
    --target <path>         指定輸出目錄（預設 AI_CORE_FUNCS_DIR 或 user_data_dir/ai_core/funcs/）
    --target sfc            搭配 --sfc 把函式塞進指定 SFC（§8.3）
    --sfc <sfc-name>        指定目標 SFC 名稱（--target sfc 時必填）
    --metadata              印 author 自身的 metadata JSON 後 exit 0
    --json-errors           stderr 改輸出 JSON 格式錯誤
    """
    pass


def register_function(
    func_path,
    target_dir=None,
    sfc_name: str | None = None,
) -> None:
    """把通過 dry-run 的函式寫入 funcs/ 或指定 SFC registry。

    target_dir=None 時用 AI_CORE_FUNCS_DIR env 或 platformdirs 預設路徑（§8.3）。
    sfc_name 有值時呼叫目標 SFC 的 registry 介面（ai-core-sfc register 等），
    而非直接寫檔。

    注冊成功後觸發 ai-core-hub --gen-functions-md 與 --gen-agent-md（§15.4 步驟 2）。
    """
    pass
