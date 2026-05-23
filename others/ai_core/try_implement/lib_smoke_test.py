#!/usr/bin/env python3
"""lib_smoke_test.py — lib/ 各模組的煙霧測試（純 assert，不依賴 pytest）。

涵蓋 state_dirs / recovery / memoize / server / singleton / trace / call /
llm_call / compose。執行：

    python3 lib_smoke_test.py
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from lib import (call, compose, compose_meta, interact, llm_call, memoize, recovery,
                 server, singleton, state_dirs, trace)

_passed = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global _passed
    assert cond, f"[FAIL] {label}\n  {detail}"
    _passed += 1
    print(f"[PASS] {label}")


# --------------------------------------------------------------------------
# state_dirs / recovery / memoize（複合規範三件套）
# --------------------------------------------------------------------------

def test_composite_libs() -> None:
    base = tempfile.mkdtemp()
    sd = state_dirs.StateDirs("demo", base)
    sd.write_json("config", {"k": 1})
    check("state_dirs 單檔 JSON 往返", sd.read_json("config") == {"k": 1})
    check("state_dirs declared() 合規範",
          sd.declared("state", "data") == {"state": "stateful_external",
                                           "state_dirs": ["state", "data"]})

    rm = recovery.RecoveryManager("demo", base, mode="resume")
    rm.begin(payload="recovery/p.json")
    check("recovery 半完成 → detect=resume", rm.detect()[0] == "resume")
    seen = {}
    rm.startup(on_resume=lambda rec: seen.update(rec))
    check("recovery startup 觸發 on_resume", seen.get("payload") == "recovery/p.json")
    rm.complete()
    check("recovery complete → detect=clean", rm.detect()[0] == "clean")

    # rollback / reset 模式：detect 回正確 mode、startup 觸發對應 handler
    rb = recovery.RecoveryManager("demo_rb", base, mode="rollback")
    rb.begin()
    check("recovery rollback 模式 detect=rollback", rb.detect()[0] == "rollback")
    fired = {}
    rb.startup(on_rollback=lambda r: fired.setdefault("rb", True))
    check("recovery rollback 觸發 on_rollback", fired.get("rb") is True)
    rs = recovery.RecoveryManager("demo_rs", base, mode="reset")
    rs.begin()
    fired2 = {}
    rs.startup(on_reset=lambda r: fired2.setdefault("rs", True))
    check("recovery reset 觸發 on_reset", fired2.get("rs") is True)

    mz = memoize.Memoizer("demo", base)
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return "R"
    _, hit1 = mz.cached_call(compute, stdin="x")
    _, hit2 = mz.cached_call(compute, stdin="x")
    check("memoize 第一次 miss、第二次 hit 且不重算",
          hit1 is False and hit2 is True and calls["n"] == 1)


# --------------------------------------------------------------------------
# server（NDJSON persistent server lifecycle）
# --------------------------------------------------------------------------

def test_server() -> None:
    srv = server.NDJSONServer("demo")

    @srv.handler("upper")
    def _upper(req):
        return {"result": req.get("text", "").upper()}

    requests = "\n".join([
        json.dumps({"cmd": "ping"}),
        json.dumps({"cmd": "list"}),
        json.dumps({"cmd": "upper", "text": "hi"}),
        json.dumps({"cmd": "nope"}),
        json.dumps({"cmd": "shutdown"}),
    ]) + "\n"
    out = io.StringIO()
    err = io.StringIO()
    rc = srv.serve(stdin=io.StringIO(requests), stdout=out, stderr=err)
    lines = [json.loads(l) for l in out.getvalue().splitlines() if l.strip()]
    check("server exit 0", rc == 0)
    check("server ping → pong", lines[0].get("pong") is True, str(lines[0]))
    check("server list 含 upper handler", "upper" in lines[1]["handlers"], str(lines[1]))
    check("server 自訂 handler upper(hi)=HI", lines[2].get("result") == "HI", str(lines[2]))
    check("server 未知 cmd → ok=false", lines[3]["ok"] is False, str(lines[3]))
    check("server shutdown 回 shutdown=true", lines[4].get("shutdown") is True, str(lines[4]))
    check("server ready 訊號進 stderr", "ready" in err.getvalue(), err.getvalue())


# --------------------------------------------------------------------------
# singleton（queue + consume rate）
# --------------------------------------------------------------------------

def test_singleton() -> None:
    meter = singleton.RateMeter(limits={"token": 100})
    meter.record(token=30)
    meter.record(token=30)
    check("RateMeter 累計", meter.total("token") == 60)
    check("RateMeter remaining", meter.remaining("token") == 40)
    check("RateMeter would_exceed", meter.would_exceed(token=50) == ["token"])
    check("RateMeter 尚未超限", meter.exceeded() == [])

    q = singleton.RequestQueue()
    a = q.enqueue("A")
    b = q.enqueue("B")
    q.enqueue("C")
    check("queue cancel 中間項", q.cancel(b) is True)
    check("queue pending 扣掉取消", q.pending() == 2)
    check("queue dequeue 跳過取消項", q.dequeue() == (a, "A"))
    check("queue dequeue 下一個是 C", q.dequeue()[1] == "C")

    res = singleton.SingletonResource("llm", limits={"token": 5})
    for word in ["aa", "bb", "cc", "dd"]:
        res.submit(word)
    # worker 把字串轉大寫；每次耗 2 token；上限 5 → 第 3 次後超限應停
    done = res.drain(worker=lambda p: p.upper(),
                     cost_fn=lambda p, r: {"token": 2})
    check("singleton drain 因超限提前停（處理 3 個）", len(done) == 3, f"done={done}")
    check("singleton 已超限", res.meter.exceeded() == ["token"])


# --------------------------------------------------------------------------
# trace（調用鏈）
# --------------------------------------------------------------------------

def test_trace() -> None:
    err = io.StringIO()
    # 清掉可能殘留的 env，確保此 process 是鏈頭
    import os
    os.environ.pop(trace.ENV_TRACE, None)
    os.environ.pop(trace.ENV_SPAN, None)
    with trace.span("outer", stderr=err):
        with trace.span("inner", stderr=err):
            pass
    col = trace.Collector()
    col.add_text(err.getvalue())
    tree = col.tree()
    check("trace 只有一個 root", len(tree) == 1, str(tree))
    check("trace root=outer", tree[0]["name"] == "outer", str(tree))
    check("trace inner 掛在 outer 下", tree[0]["children"][0]["name"] == "inner", str(tree))
    check("trace 兩段都 complete", tree[0]["complete"] and tree[0]["children"][0]["complete"])
    rendered = col.render()
    check("trace render 縮排呈現巢狀", "- outer" in rendered and "  - inner" in rendered, rendered)

    # incomplete span（有 start 無 end，模擬被 kill）→ 應容忍並標 incomplete
    col2 = trace.Collector()
    col2.add_line(json.dumps({"trace": "t", "span": "k1", "parent": None,
                              "name": "killed", "event": "start", "ts": 1}))
    t2 = col2.tree()
    check("trace 容忍 incomplete span（缺 end）",
          len(t2) == 1 and t2[0]["complete"] is False, str(t2))
    check("trace render 標記 incomplete", "incomplete" in col2.render(), col2.render())


# --------------------------------------------------------------------------
# call（跨邊界統一呼叫）
# --------------------------------------------------------------------------

def test_call() -> None:
    # in-process
    ip = call.InProcess(lambda s: s[::-1])
    check("call InProcess 反轉", call.call(ip, "abc") == "cba")

    # subprocess（用 python -c 當 echo-upper）
    sp = call.Subprocess([sys.executable, "-c",
                          "import sys; sys.stdout.write(sys.stdin.read().upper())"])
    check("call Subprocess 轉大寫", call.call(sp, "hi") == "HI")

    # http（起一個 stdlib http server echo body）
    class Echo(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"HTTP:" + body)

        def log_message(self, *a):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Echo)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    ht = call.Http(f"http://127.0.0.1:{port}/")
    check("call Http round-trip", call.call(ht, "ping") == "HTTP:ping")
    httpd.server_close()

    # from_spec
    sp2 = call.from_spec({"kind": "subprocess", "cmd": ["cat"]})
    check("call from_spec 建 Subprocess", call.call(sp2, "x") == "x")


# --------------------------------------------------------------------------
# llm_call（基底 + packing）
# --------------------------------------------------------------------------

def test_llm_call() -> None:
    check("llm_call 預設 EchoBackend", llm_call.llm_call("hi") == "echo: hi")

    coding_q = llm_call.bind(
        system="you are a professor of coding",
        postprocess=lambda o: o + " -- at 20240505",
        backend=llm_call.EchoBackend(),
    )
    out = coding_q("how to sort?")
    check("bind 疊 system 進 prompt", "professor of coding" in out, out)
    check("bind 疊 postprocess 後綴", out.endswith("-- at 20240505"), out)


# --------------------------------------------------------------------------
# compose（多函數組合 + 馴化隨機性）
# --------------------------------------------------------------------------

def test_compose() -> None:
    upper = lambda s: s.upper()
    excl = lambda s: s + "!"
    check("pipe 串接", compose.pipe(upper, excl)("hi") == "HI!")

    check("fanout 多分支", compose.fanout(upper, excl)("hi") == ["HI", "hi!"])
    longest = compose.fanout_reduce([upper, excl, lambda s: s * 3],
                                    reducer=lambda outs: max(outs, key=len))
    check("fanout_reduce 取最長", longest("hi") == "hihihi", longest("hi"))

    r = compose.route(selector=lambda s: "num" if s.isdigit() else "txt",
                      table={"num": lambda s: f"N({s})", "txt": lambda s: f"T({s})"})
    check("route 走 num 分支", r("123") == "N(123)")
    check("route 走 txt 分支", r("abc") == "T(abc)")

    fb = compose.with_fallback(primary=lambda s: 1 / 0,  # 故意拋
                               fallback=lambda s: "safe")
    check("with_fallback 主拋例外走備援", fb("x") == "safe")

    dec = compose.decompose(split=lambda s: list(s),
                            sub=lambda c: c.upper(),
                            join=lambda parts: "-".join(parts))
    check("decompose 拆-處理-合", dec("abc") == "A-B-C")

    # --- 馴化隨機性：用 ScriptedBackend 模擬「同輸入不同輸出」---
    # retry_until_valid：壞、壞、好 → 第三次過
    flaky = llm_call.bind(backend=llm_call.ScriptedBackend(["bad", "bad", "good"]))
    safe = compose.retry_until_valid(flaky, validate=lambda o: o == "good", retries=3)
    check("retry_until_valid 抽到合格才回", safe("q") == "good")

    # retry 用盡仍不過 → 拋
    always_bad = llm_call.bind(backend=llm_call.ScriptedBackend(["bad"]))
    g = compose.retry_until_valid(always_bad, validate=lambda o: False, retries=2)
    raised = False
    try:
        g("q")
    except compose.ValidationError:
        raised = True
    check("retry_until_valid 用盡拋 ValidationError", raised)

    # vote：答案 4,4,5,4,3 → 多數 4
    ans = llm_call.bind(backend=llm_call.ScriptedBackend(["4", "4", "5", "4", "3"]))
    voted = compose.vote(ans, n=5)
    check("vote 自一致取多數=4", voted("2+2?") == "4")

    # best_of：取最長者
    cand = llm_call.bind(backend=llm_call.ScriptedBackend(["a", "aaa", "aa"]))
    bo = compose.best_of(cand, n=3, score=len)
    check("best_of 取最高分（最長）", bo("q") == "aaa")

    # guard：壞輸出交給 repair 修
    bad = llm_call.bind(backend=llm_call.ScriptedBackend(["WRONG"]))
    guarded = compose.guard(bad, validate=lambda o: o == "OK", repair=lambda o: "OK")
    check("guard 驗證失敗走 repair", guarded("q") == "OK")


# --------------------------------------------------------------------------
# interact（多函數交互：黑板 driver / actor-critic / debate）
# --------------------------------------------------------------------------

def test_interact() -> None:
    # 黑板 driver：每輪 n+1，until n>=3
    inc = lambda s: {**s, "n": s.get("n", 0) + 1}
    final = interact.run([inc], {"n": 0}, until=lambda s: s.get("n", 0) >= 3, max_rounds=10)
    check("interact run 收斂到 until", final["n"] >= 3 and final["_stopped"] == "until", str(final))

    # max_rounds 安全閥：until 永不成立也不會 hang
    capped = interact.run([inc], {"n": 0}, until=lambda s: False, max_rounds=2)
    check("interact max_rounds 安全閥生效", capped["_stopped"] == "max_rounds" and capped["n"] == 2,
          str(capped))

    # actor-critic：actor 把 feedback 加一個 'a'，critic 在長度>=3 時驗收
    actor = lambda task, fb: (fb + "a") if fb else "a"
    critic = lambda task, draft: (len(draft) >= 3, draft)
    res = interact.actor_critic("grow", actor, critic, max_rounds=5)
    check("actor_critic 修到驗收", res["accepted"] and res["draft"] == "aaa", str(res))
    check("actor_critic 第 3 輪收斂", res["rounds"] == 3, str(res))

    # actor-critic 永不驗收 → 用盡 max_rounds 但不 hang
    never = lambda task, draft: (False, draft)
    res2 = interact.actor_critic("x", actor, never, max_rounds=2)
    check("actor_critic 永不驗收則用盡輪數", res2["accepted"] is False and res2["rounds"] == 2,
          str(res2))

    # debate：三方 A/B/A，judge 取多數 → A
    from collections import Counter
    debaters = [lambda c: "A", lambda c: "B", lambda c: "A"]
    judge = lambda task, args: Counter(args).most_common(1)[0][0]
    d = interact.debate("誰對", debaters, judge)
    check("debate judge 取多數=A", d["verdict"] == "A", str(d))


# --------------------------------------------------------------------------
# compose_meta（組合的軸推導規則）
# --------------------------------------------------------------------------

def test_compose_meta() -> None:
    MF = compose_meta.MetaFn
    f1 = MF(fn=lambda s: s.upper(), name="upper",
            meta={"guarantee": "idempotent", "state": "stateful_external",
                  "state_dirs": ["data"]})
    f2 = MF(fn=lambda s: s + "!", name="bang",
            meta={"guarantee": "none", "state": "stateless"})

    p = compose_meta.mpipe(f1, f2)
    check("mpipe 行為正確", p("hi") == "HI!", p("hi"))
    check("mpipe guarantee=最弱(none)", p.meta["guarantee"] == "none", str(p.meta))
    check("mpipe state=聯集(stateful_external)", p.meta["state"] == "stateful_external", str(p.meta))
    check("mpipe state_dirs=聯集([data])", p.meta["state_dirs"] == ["data"], str(p.meta))

    # persistent 成員 → requires_persistent（八軸無此值，示範缺口）
    srv = MF(fn=lambda s: s, name="srv", meta={"lifecycle": "persistent", "state": "stateless"})
    p2 = compose_meta.mpipe(f1, srv)
    check("mpipe 列出 persistent 相依", p2.meta.get("requires_persistent") == ["srv"], str(p2.meta))

    # fanout 共用 state_dir → 並發衝突 → guarantee 退化 none + warning
    a = MF(fn=lambda s: s, name="a", meta={"guarantee": "idempotent", "state": "stateful_external",
                                           "state_dirs": ["data"]})
    b = MF(fn=lambda s: s, name="b", meta={"guarantee": "idempotent", "state": "stateful_external",
                                           "state_dirs": ["data"]})
    fo = compose_meta.mfanout_reduce([a, b], reducer=lambda outs: outs[0])
    check("fanout 共用 dir → guarantee 退化 none", fo.meta["guarantee"] == "none", str(fo.meta))
    check("fanout 共用 dir → 帶 warning", "_warning" in fo.meta, str(fo.meta))

    # fanout 不同 dir → guarantee 取最弱（都 idempotent → idempotent）
    c = MF(fn=lambda s: s, name="c", meta={"guarantee": "idempotent", "state_dirs": ["data"]})
    d = MF(fn=lambda s: s, name="d", meta={"guarantee": "idempotent", "state_dirs": ["cache"]})
    fo2 = compose_meta.mfanout_reduce([c, d], reducer=lambda outs: outs[0])
    check("fanout 不同 dir → guarantee=idempotent", fo2.meta["guarantee"] == "idempotent", str(fo2.meta))

    # mretry 前置契約：guarantee=none 的函式不准被 retry 包
    raised = False
    try:
        compose_meta.mretry(f2, validate=lambda o: True)
    except ValueError:
        raised = True
    check("mretry 拒絕包 guarantee=none 的函式（前置契約）", raised)

    # idempotent 的可以包，且行為正確
    r = compose_meta.mretry(f1, validate=lambda o: True)
    check("mretry 包 idempotent 函式 OK", r("hi") == "HI", r("hi"))


def main() -> int:
    print("=== lib 煙霧測試開始 ===\n")
    test_composite_libs()
    test_server()
    test_singleton()
    test_trace()
    test_call()
    test_llm_call()
    test_compose()
    test_interact()
    test_compose_meta()
    print(f"\n=== 全部通過：{_passed} 項斷言 ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
