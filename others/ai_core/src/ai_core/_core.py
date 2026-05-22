from __future__ import annotations

import json
import sys
from typing import Any

_KNOWN_FIELDS = frozenset({
    "entries", "lifecycle", "state", "state_dirs",
    "resources", "interruptible", "guarantee", "dry_run",
})

_LIFECYCLE_VALUES = frozenset({"one_shot", "persistent"})
_STATE_VALUES = frozenset({"stateless", "stateful_external"})
_STATE_DIR_VALUES = frozenset({"config", "cache", "state", "data"})
_GUARANTEE_VALUES = frozenset({"none", "idempotent", "transactional"})
_INTERRUPTIBLE_STRING_VALUES = frozenset({
    "safe", "unsafe", "resettable", "rollback", "resumable", "graceful",
})

_registered = False
_metadata: dict[str, Any] = {}


def register(**kwargs: Any) -> None:
    global _registered, _metadata

    if _registered:
        raise RuntimeError("ai_core.register() called twice; it must be called exactly once")

    _registered = True
    _metadata = _validate(kwargs)
    _intercept()


def _intercept() -> None:
    argv = sys.argv[1:]
    if "--metadata" not in argv:
        return
    if len(argv) == 1:
        print(json.dumps(_metadata))
        sys.exit(0)
    print("--metadata must be used alone with no other arguments", file=sys.stderr)
    sys.exit(1)


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
