import json
import sys

import pytest

import ai_core
import ai_core._core as _core


@pytest.fixture(autouse=True)
def reset():
    _core._top_metadata = {}
    _core._subcommands = {}
    _core._resolver = None
    yield
    _core._top_metadata = {}
    _core._subcommands = {}
    _core._resolver = None


# --- register() 基本行為（拆分模型：純宣告、無副作用） ---

def test_register_stores_metadata():
    ai_core.register(lifecycle="one_shot")
    assert _core._top_metadata == {"lifecycle": "one_shot"}


def test_register_returns_none():
    assert ai_core.register(lifecycle="one_shot") is None


def test_register_is_side_effect_free(monkeypatch):
    # 拆分模型核心保證：即使 argv 帶 --metadata，register 本身不讀 argv、不攔截、不 exit。
    monkeypatch.setattr(sys, "argv", ["prog", "--metadata"])
    ai_core.register(lifecycle="one_shot")  # 不應 SystemExit
    assert _core._top_metadata == {"lifecycle": "one_shot"}


def test_register_twice_last_write_wins():
    # 舊契約是「二次呼叫 raise」；拆分後 register 純宣告，採 last-write-wins。
    ai_core.register(lifecycle="one_shot")
    ai_core.register(lifecycle="persistent")
    assert _core._top_metadata == {"lifecycle": "persistent"}


def test_register_no_args():
    ai_core.register()
    assert _core._top_metadata == {}


def test_unknown_field_raises():
    with pytest.raises(ValueError, match="unknown metadata fields"):
        ai_core.register(foo="bar")


# --- intercept() 攔截（放寬版） ---

def test_intercept_top_metadata_exits_0(capsys):
    ai_core.register(lifecycle="one_shot", state="stateful_external")
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept(["--metadata"])
    assert exc.value.code == 0
    data = json.loads(capsys.readouterr().out)
    assert data == {"lifecycle": "one_shot", "state": "stateful_external"}


def test_intercept_defaults_to_sys_argv(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--metadata"])
    ai_core.register(lifecycle="one_shot")
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept()
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out) == {"lifecycle": "one_shot"}


def test_intercept_non_metadata_returns_control(capsys):
    # 一般 dispatch：intercept 應 return（不 exit、無輸出），把控制權交回 caller。
    ai_core.register(lifecycle="one_shot")
    assert ai_core.intercept(["run", "--foo"]) is None
    assert capsys.readouterr().out == ""


def test_intercept_empty_metadata(capsys):
    ai_core.register()
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept(["--metadata"])
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out) == {}


# --- subcommand-scoped metadata（A1 + A2） ---

def test_intercept_static_subcommand_metadata(capsys):
    # A2：單一執行檔，頂層 one_shot，子命令 forge 為 persistent。
    ai_core.register(lifecycle="one_shot")
    ai_core.register_subcommand("forge", lifecycle="persistent")
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept(["forge", "--metadata"])
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out) == {"lifecycle": "persistent"}


def test_intercept_unknown_subcommand_exits_1():
    ai_core.register(lifecycle="one_shot")
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept(["nope", "--metadata"])
    assert exc.value.code == 1


def test_intercept_dynamic_resolver(capsys):
    # A1：子命令名稱來自外部資料（如 SFC store），靜態查不到時交給 resolver。
    ai_core.register(lifecycle="one_shot")

    def resolver(name, store_override):
        if name == "shout":
            return {"lifecycle": "one_shot", "state": "stateless"}
        return None

    ai_core.register_subcommand_resolver(resolver)
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept(["shout", "--metadata"])
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out)["state"] == "stateless"


def test_intercept_resolver_miss_exits_1():
    ai_core.register(lifecycle="one_shot")
    ai_core.register_subcommand_resolver(lambda name, store: None)
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept(["ghost", "--metadata"])
    assert exc.value.code == 1


def test_intercept_static_takes_precedence_over_resolver(capsys):
    ai_core.register_subcommand("forge", lifecycle="persistent")
    ai_core.register_subcommand_resolver(lambda n, s: {"lifecycle": "one_shot"})
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept(["forge", "--metadata"])
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out) == {"lifecycle": "persistent"}


def test_intercept_strips_store_prefix(capsys):
    # --store DIR 前綴應被吃掉，使 `prog --store DIR <sub> --metadata` 仍命中 scoped metadata。
    ai_core.register(lifecycle="one_shot")
    ai_core.register_subcommand("forge", lifecycle="persistent")
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept(["--store", "/tmp/x", "forge", "--metadata"])
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out) == {"lifecycle": "persistent"}


def test_intercept_resolver_receives_store_override():
    seen = {}
    ai_core.register_subcommand_resolver(lambda name, store: seen.update(name=name, store=store) or None)
    with pytest.raises(SystemExit):
        ai_core.intercept(["--store", "/tmp/s", "fn", "--metadata"])
    assert seen == {"name": "fn", "store": "/tmp/s"}


# --- §2 lifecycle ---

def test_lifecycle_one_shot():
    ai_core.register(lifecycle="one_shot")
    assert _core._top_metadata["lifecycle"] == "one_shot"


def test_lifecycle_persistent():
    ai_core.register(lifecycle="persistent")
    assert _core._top_metadata["lifecycle"] == "persistent"


def test_lifecycle_invalid():
    with pytest.raises(ValueError, match="lifecycle"):
        ai_core.register(lifecycle="always_on")


# --- §3 state + state_dirs ---

def test_state_stateless():
    ai_core.register(state="stateless")
    assert _core._top_metadata["state"] == "stateless"


def test_state_stateful_external():
    ai_core.register(state="stateful_external")
    assert _core._top_metadata["state"] == "stateful_external"


def test_state_invalid():
    with pytest.raises(ValueError, match="state"):
        ai_core.register(state="stateful_internal")


def test_state_dirs_valid():
    ai_core.register(state="stateful_external", state_dirs=["state", "data"])
    assert _core._top_metadata["state_dirs"] == ["state", "data"]


def test_state_dirs_all_values():
    ai_core.register(state_dirs=["config", "cache", "state", "data"])
    assert len(_core._top_metadata["state_dirs"]) == 4


def test_state_dirs_empty_list():
    ai_core.register(state_dirs=[])
    assert _core._top_metadata["state_dirs"] == []


def test_state_dirs_invalid_value():
    with pytest.raises(ValueError, match="state_dirs"):
        ai_core.register(state_dirs=["logs"])


def test_state_dirs_not_list():
    with pytest.raises(TypeError, match="state_dirs"):
        ai_core.register(state_dirs="state")


# --- §1 entries ---

def test_entries_valid_minimal():
    ai_core.register(entries={"stdin": {"able_in": True, "able_out": False}})
    assert "entries" in _core._top_metadata


def test_entries_full():
    ai_core.register(entries={
        "input": {
            "able_in": True,
            "able_out": False,
            "mode": "batch",
            "type": "text",
            "channel_constraint": "stable",
            "terminal_binding": {"argflag": "--input", "default": "stdin"},
        }
    })
    assert _core._top_metadata["entries"]["input"]["mode"] == "batch"


def test_entries_streaming_dict_mode():
    ai_core.register(entries={
        "out": {
            "able_in": False,
            "able_out": True,
            "mode": {"type": "streaming", "rate": "20b/s"},
        }
    })
    assert _core._top_metadata["entries"]["out"]["mode"]["type"] == "streaming"


def test_entries_binary_type():
    ai_core.register(entries={
        "blob": {"able_in": True, "able_out": False, "type": "binary"}
    })
    assert _core._top_metadata["entries"]["blob"]["type"] == "binary"


def test_entries_type_dict_with_mime():
    ai_core.register(entries={
        "img": {
            "able_in": True,
            "able_out": False,
            "type": {"base": "binary", "mime": "image/png"},
        }
    })
    assert _core._top_metadata["entries"]["img"]["type"]["mime"] == "image/png"


def test_entries_missing_able_in():
    with pytest.raises(ValueError, match="able_in"):
        ai_core.register(entries={"x": {"able_out": True}})


def test_entries_missing_able_out():
    with pytest.raises(ValueError, match="able_out"):
        ai_core.register(entries={"x": {"able_in": True}})


def test_entries_able_in_not_bool():
    with pytest.raises(TypeError, match="able_in"):
        ai_core.register(entries={"x": {"able_in": "yes", "able_out": False}})


def test_entries_mode_invalid_string():
    with pytest.raises(ValueError, match="mode"):
        ai_core.register(entries={"x": {"able_in": True, "able_out": False, "mode": "once"}})


def test_entries_mode_dict_missing_type():
    with pytest.raises(ValueError, match="mode"):
        ai_core.register(entries={"x": {"able_in": True, "able_out": False, "mode": {"rate": "1kb/s"}}})


def test_entries_type_invalid_string():
    with pytest.raises(ValueError, match="type"):
        ai_core.register(entries={"x": {"able_in": True, "able_out": False, "type": "json"}})


def test_entries_type_dict_missing_base():
    with pytest.raises(ValueError, match="base"):
        ai_core.register(entries={"x": {"able_in": True, "able_out": False, "type": {"encoding": "utf-8"}}})


def test_entries_channel_constraint_invalid():
    with pytest.raises(ValueError, match="channel_constraint"):
        ai_core.register(entries={"x": {"able_in": True, "able_out": False, "channel_constraint": "fast"}})


def test_entries_not_dict():
    with pytest.raises(TypeError, match="entries"):
        ai_core.register(entries=["stdin"])


# --- §4 resources ---

def test_resources_simple():
    ai_core.register(resources={"memory": "4gb", "gpu": True})
    assert _core._top_metadata["resources"]["memory"] == "4gb"


def test_resources_memory_object():
    ai_core.register(resources={"memory": {"startup": "2gb", "peak": "8gb", "idle": "500mb"}})
    assert _core._top_metadata["resources"]["memory"]["startup"] == "2gb"


def test_resources_custom_key():
    ai_core.register(resources={"llm_entry": True, "db": {"type": "postgres"}})
    assert _core._top_metadata["resources"]["db"]["type"] == "postgres"


def test_resources_not_dict():
    with pytest.raises(TypeError, match="resources"):
        ai_core.register(resources="4gb")


# --- §5 interruptible ---

def test_interruptible_safe():
    ai_core.register(interruptible="safe")
    assert _core._top_metadata["interruptible"] == "safe"


def test_interruptible_all_string_values():
    for v in ("safe", "unsafe", "resettable", "rollback", "resumable", "graceful"):
        ai_core.register(interruptible=v)  # last-write-wins，無須重置
        assert _core._top_metadata["interruptible"] == v


def test_interruptible_invalid_string():
    with pytest.raises(ValueError, match="interruptible"):
        ai_core.register(interruptible="maybe")


def test_interruptible_dict():
    ai_core.register(interruptible={"type": "resettable", "reset_hint": "--reset"})
    assert _core._top_metadata["interruptible"]["reset_hint"] == "--reset"


def test_interruptible_dict_missing_type():
    with pytest.raises(ValueError, match="type"):
        ai_core.register(interruptible={"hint": "run --reset"})


def test_interruptible_dict_conditional():
    ai_core.register(interruptible={"type": "conditional", "condition": "only when idle"})
    assert _core._top_metadata["interruptible"]["type"] == "conditional"


def test_interruptible_wrong_type():
    with pytest.raises(TypeError, match="interruptible"):
        ai_core.register(interruptible=42)


# --- §6 guarantee + dry_run ---

def test_guarantee_none():
    ai_core.register(guarantee="none")
    assert _core._top_metadata["guarantee"] == "none"


def test_guarantee_idempotent():
    ai_core.register(guarantee="idempotent")
    assert _core._top_metadata["guarantee"] == "idempotent"


def test_guarantee_transactional():
    ai_core.register(guarantee="transactional")
    assert _core._top_metadata["guarantee"] == "transactional"


def test_guarantee_invalid():
    with pytest.raises(ValueError, match="guarantee"):
        ai_core.register(guarantee="atomic")


def test_dry_run_bool_true():
    ai_core.register(dry_run=True)
    assert _core._top_metadata["dry_run"] is True


def test_dry_run_bool_false():
    ai_core.register(dry_run=False)
    assert _core._top_metadata["dry_run"] is False


def test_dry_run_dict():
    ai_core.register(dry_run={"flag": "--dry-run", "state_entry": "stdout"})
    assert _core._top_metadata["dry_run"]["flag"] == "--dry-run"


def test_dry_run_wrong_type():
    with pytest.raises(TypeError, match="dry_run"):
        ai_core.register(dry_run="yes")


# --- nondeterministic（LLM 馴化框架 / 憑證准入入口；roadmap §3.4） ---

def test_nondeterministic_bool_uncertified():
    # bool 形式：未認證的 LLM 留白（開機期；僅標記隨機）。
    ai_core.register(nondeterministic=True)
    assert _core._top_metadata["nondeterministic"] is True


def test_nondeterministic_certificate_dict():
    # dict 形式：證書——用哪個模型、哪個測試組、認證穩定度。
    ai_core.register(nondeterministic={
        "model": "local-8b",
        "test_set": "code_qa_v1",
        "stability": "92%",
    })
    cert = _core._top_metadata["nondeterministic"]
    assert cert["model"] == "local-8b"
    assert cert["stability"] == "92%"


def test_nondeterministic_wrong_type():
    with pytest.raises(TypeError, match="nondeterministic"):
        ai_core.register(nondeterministic="yes")


# --- 複合範例（對應 lib_spec.md 完整範例） ---

def test_composite_full_example(capsys):
    ai_core.register(
        lifecycle="one_shot",
        state="stateful_external",
        state_dirs=["state", "data"],
        interruptible="unsafe",
        guarantee="idempotent",
    )
    with pytest.raises(SystemExit) as exc:
        ai_core.intercept(["--metadata"])
    assert exc.value.code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["lifecycle"] == "one_shot"
    assert data["state"] == "stateful_external"
    assert data["state_dirs"] == ["state", "data"]
    assert data["interruptible"] == "unsafe"
    assert data["guarantee"] == "idempotent"
