from __future__ import annotations

import json
import sys
from typing import Any, Callable

_KNOWN_FIELDS = frozenset({
    "entries", "lifecycle", "state", "state_dirs",
    "resources", "interruptible", "guarantee", "dry_run",
    "nondeterministic",
})

_LIFECYCLE_VALUES = frozenset({"one_shot", "persistent"})
_STATE_VALUES = frozenset({"stateless", "stateful_external"})
_STATE_DIR_VALUES = frozenset({"config", "cache", "state", "data"})
_GUARANTEE_VALUES = frozenset({"none", "idempotent", "transactional"})
_INTERRUPTIBLE_STRING_VALUES = frozenset({
    "safe", "unsafe", "resettable", "rollback", "resumable", "graceful",
})

# 全域 metadata 登記表。
# 設計（拒絕 import-time 副作用）：register* 系列只「宣告」，純粹寫入下面三個全域，
# 不讀 sys.argv、不攔截、不 sys.exit。攔截 --metadata 由 intercept() 顯式負責。
# 因此工具可被當 library import 而無副作用；register 應在 __main__ 區塊呼叫
# （見 core_nature/lib_spec.md「register 的 import-time 副作用」一節）。
_top_metadata: dict[str, Any] = {}
_subcommands: dict[str, dict[str, Any]] = {}
_resolver: Callable[[str, str | None], dict[str, Any] | None] | None = None


def register(**kwargs: Any) -> None:
    """宣告程式頂層 metadata（dispatcher 的預設行為）。

    純宣告、無副作用：不讀 sys.argv、不攔截 --metadata、不 sys.exit。
    要讓 --metadata 生效，須在 main / __main__ 顯式呼叫 intercept()。
    可重複呼叫（last-write-wins），但慣例上每個程式只在 __main__ 呼叫一次。
    """
    global _top_metadata
    _top_metadata = _validate(kwargs)


def register_subcommand(name: str, **kwargs: Any) -> None:
    """宣告某個靜態子命令的 scoped metadata（可與頂層不同 lifecycle）。

    解決「單一執行檔含多種 lifecycle 子命令」——頂層描述 dispatcher 的預設行為，
    各子命令各自覆寫。intercept() 會處理 ``prog <name> --metadata``。
    """
    _subcommands[name] = _validate(kwargs)


def register_subcommand_resolver(
    fn: Callable[[str, str | None], dict[str, Any] | None],
) -> None:
    """註冊動態子命令解析器：``fn(name, store_override) -> metadata dict | None``。

    用於子命令名稱來自外部資料（如 SFC 的 tiny function 來自 store）的情形：
    靜態登記查不到時，再交給 resolver 去查。回傳 None 表示查無此子命令。
    """
    global _resolver
    _resolver = fn


def _emit(md: dict[str, Any]) -> None:
    print(json.dumps(md, ensure_ascii=False))
    sys.exit(0)


def intercept(argv: list[str] | None = None) -> None:
    """放寬版 ``--metadata`` 攔截。命中 metadata 查詢則輸出並 ``sys.exit``；否則 return 交還控制權。

    攔截規則（先吃掉可選的前導 ``--store DIR``，使 ``prog --store DIR <sub> --metadata`` 也成立）：

    1. ``argv == ["--metadata"]``          → 印頂層 metadata，exit 0
    2. ``argv == [<name>, "--metadata"]``  → 依序查 靜態子命令 → 動態 resolver；
       命中印該 scoped metadata exit 0；查無 → stderr 報錯 exit 1
    3. 其餘                                 → return（一般 dispatch，交回 caller）
    """
    if argv is None:
        argv = sys.argv[1:]

    work = list(argv)
    store_override: str | None = None
    if len(work) >= 2 and work[0] == "--store":
        store_override = work[1]
        work = work[2:]

    # 規則 1：頂層 metadata
    if work == ["--metadata"]:
        _emit(_top_metadata)

    # 規則 2：subcommand-scoped metadata
    if len(work) == 2 and work[1] == "--metadata":
        name = work[0]
        if name in _subcommands:
            _emit(_subcommands[name])
        if _resolver is not None:
            md = _resolver(name, store_override)
            if md is not None:
                _emit(md)
        print(f"--metadata: unknown subcommand/function {name!r}", file=sys.stderr)
        sys.exit(1)

    # 規則 3：非 metadata 查詢 → 交還控制權
    return


def _validate(kwargs: dict[str, Any]) -> dict[str, Any]:
    unknown = set(kwargs) - _KNOWN_FIELDS
    if unknown:
        raise ValueError(f"unknown metadata fields: {sorted(unknown)}")

    result: dict[str, Any] = {}

    if "lifecycle" in kwargs:
        v = kwargs["lifecycle"]
        if v not in _LIFECYCLE_VALUES:
            raise ValueError(f"lifecycle must be one of {sorted(_LIFECYCLE_VALUES)}, got {v!r}")
        result["lifecycle"] = v

    if "state" in kwargs:
        v = kwargs["state"]
        if v not in _STATE_VALUES:
            raise ValueError(f"state must be one of {sorted(_STATE_VALUES)}, got {v!r}")
        result["state"] = v

    if "state_dirs" in kwargs:
        v = kwargs["state_dirs"]
        if not isinstance(v, list):
            raise TypeError(f"state_dirs must be a list, got {type(v).__name__}")
        invalid = set(v) - _STATE_DIR_VALUES
        if invalid:
            raise ValueError(
                f"state_dirs contains invalid values: {sorted(invalid)}; "
                f"allowed: {sorted(_STATE_DIR_VALUES)}"
            )
        result["state_dirs"] = v

    if "entries" in kwargs:
        v = kwargs["entries"]
        if not isinstance(v, dict):
            raise TypeError(f"entries must be a dict, got {type(v).__name__}")
        result["entries"] = _validate_entries(v)

    if "resources" in kwargs:
        v = kwargs["resources"]
        if not isinstance(v, dict):
            raise TypeError(f"resources must be a dict, got {type(v).__name__}")
        result["resources"] = v

    if "interruptible" in kwargs:
        result["interruptible"] = _validate_interruptible(kwargs["interruptible"])

    if "guarantee" in kwargs:
        v = kwargs["guarantee"]
        if v not in _GUARANTEE_VALUES:
            raise ValueError(f"guarantee must be one of {sorted(_GUARANTEE_VALUES)}, got {v!r}")
        result["guarantee"] = v

    if "dry_run" in kwargs:
        result["dry_run"] = _validate_dry_run(kwargs["dry_run"])

    if "nondeterministic" in kwargs:
        result["nondeterministic"] = _validate_nondeterministic(kwargs["nondeterministic"])

    return result


def _validate_entries(entries: dict) -> dict:
    for name, entry in entries.items():
        if not isinstance(entry, dict):
            raise TypeError(f"entries[{name!r}] must be a dict")
        for required in ("able_in", "able_out"):
            if required not in entry:
                raise ValueError(f"entries[{name!r}] missing required field {required!r}")
        if not isinstance(entry["able_in"], bool):
            raise TypeError(f"entries[{name!r}].able_in must be bool")
        if not isinstance(entry["able_out"], bool):
            raise TypeError(f"entries[{name!r}].able_out must be bool")
        if "mode" in entry:
            _validate_entry_mode(name, entry["mode"])
        if "type" in entry:
            _validate_entry_type(name, entry["type"])
        if "channel_constraint" in entry:
            v = entry["channel_constraint"]
            if v != "stable":
                raise ValueError(
                    f"entries[{name!r}].channel_constraint: only 'stable' is defined, got {v!r}"
                )
        if "terminal_binding" in entry:
            v = entry["terminal_binding"]
            if not isinstance(v, dict):
                raise TypeError(f"entries[{name!r}].terminal_binding must be a dict")
    return entries


def _validate_entry_mode(name: str, mode: Any) -> None:
    _ENTRY_MODE_VALUES = frozenset({"batch", "streaming", "interactive"})
    if isinstance(mode, str):
        if mode not in _ENTRY_MODE_VALUES:
            raise ValueError(
                f"entries[{name!r}].mode string must be one of {sorted(_ENTRY_MODE_VALUES)}, got {mode!r}"
            )
    elif isinstance(mode, dict):
        if "type" not in mode:
            raise ValueError(f"entries[{name!r}].mode dict must have 'type' key")
    else:
        raise TypeError(f"entries[{name!r}].mode must be str or dict, got {type(mode).__name__}")


def _validate_entry_type(name: str, t: Any) -> None:
    _ENTRY_TYPE_VALUES = frozenset({"text", "binary"})
    if isinstance(t, str):
        if t not in _ENTRY_TYPE_VALUES:
            raise ValueError(
                f"entries[{name!r}].type string must be one of {sorted(_ENTRY_TYPE_VALUES)}, got {t!r}"
            )
    elif isinstance(t, dict):
        if "base" not in t:
            raise ValueError(f"entries[{name!r}].type dict must have 'base' key")
    else:
        raise TypeError(f"entries[{name!r}].type must be str or dict, got {type(t).__name__}")


def _validate_interruptible(v: Any) -> Any:
    if isinstance(v, str):
        if v not in _INTERRUPTIBLE_STRING_VALUES:
            raise ValueError(
                f"interruptible string must be one of {sorted(_INTERRUPTIBLE_STRING_VALUES)}, got {v!r}"
            )
        return v
    if isinstance(v, dict):
        if "type" not in v:
            raise ValueError("interruptible dict must have 'type' key")
        return v
    raise TypeError(f"interruptible must be str or dict, got {type(v).__name__}")


def _validate_dry_run(v: Any) -> Any:
    if isinstance(v, bool):
        return v
    if isinstance(v, dict):
        return v
    raise TypeError(f"dry_run must be bool or dict, got {type(v).__name__}")


def _validate_nondeterministic(v: Any) -> Any:
    # bool 形式：未認證的 LLM 留白（開機期；僅標記「此環節是隨機的」，馴化框架的觸發根）。
    # dict 形式：證書——已認證的隨機環節。自由 key-value（沿用 §4 resources 的設計），
    #   建議的預定義 key：model（用哪個模型）/ test_set（測試組）/ stability（認證穩定度）。
    #   value 格式不強制、可自由擴充；validation 只確保型別正確（從粗糙到嚴整）。
    if isinstance(v, bool):
        return v
    if isinstance(v, dict):
        return v
    raise TypeError(f"nondeterministic must be bool or dict, got {type(v).__name__}")
