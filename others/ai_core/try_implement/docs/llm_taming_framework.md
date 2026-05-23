# LLM 隨機性馴化框架（concept draft）

> try_implement 的概念框架文件。回應「如何用現有概念做個框架，規範 LLM 的隨機性，
> 或者說，更好地利用 LLM」。對應實作見 `lib/llm_call.py`、`lib/compose.py`、
> `lib/memoize.py`、`tools/hub.py`、`tools/router.py`、`tools/switch.py`。

---

## 0. 一句話

**整個 ai_core 可以重新讀成一台機器：把「LLM 這個唯一的非確定性函式」，
轉成「可靠、可組合、可重現的複合函式」。** 八軸、複合規範、組合維度，
全都是這台機器的零件。

---

## 1. 問題：LLM 是唯一的非確定性函式

ai_core 把一切都當函式 `f(str)->str`。絕大多數函式是確定的（同輸入同輸出）。
**只有 LLM 不是**：`llm(prompt)` 每次可能不同。隨機性有兩面——

- **壞處**：不可靠、不可重現、難驗證、難除錯。
- **好處**：多樣性、創造力、能跳出固定套路。

所以目標**不是消滅隨機性**，而是：**在需要確定的地方確定，在需要多樣的地方多樣。**
「馴化」是給隨機性裝上閥門，不是拔掉它。

---

## 2. 框架：五個層次

由內而外，每層把上一層的隨機性再收一點。每層都對應 try_implement 已實作的零件。

### L0 契約層 — 收窄介面，讓隨機性無處可藏

隨機性的傷害與**輸出空間大小**成正比。自由作文有無限種寫法；「回 yes 或 no」只有兩種。

- `--metadata` + typed I/O 通道（八軸 §1）把函式介面固定下來。
- 要求 LLM 輸出**結構化格式**（JSON / 固定枚舉 / 受限語法），把作文題變成填空題。
- 對應實作：`llm_call.bind(suffix="只回 JSON，schema 為…")` 把格式要求綁進 prompt。

> 原則：**能用枚舉就不要用自由文字。** 輸出空間越小，後面幾層越省力。

### L1 確定化層 — 在該確定的地方強制確定

- **memoize**（`lib/memoize.py`）：同輸入直接回快取 → 對重複輸入，LLM 變成確定函式。
  快取即是「凍結的隨機性」。這也是省錢/省算力的主力。
- temperature=0 / 固定 seed（透過 `llm_call(..., temperature=0)` 傳給 backend）：降方差。
- 與 §6 `guarantee: idempotent` 呼應：memoized 的函式天然冪等（重跑不再呼叫 LLM）。

### L2 驗證層 — 抽到不合格就重抽或修

把「LLM 偶爾給出對的答案」變成「保證對，否則明確失敗」。

- `compose.retry_until_valid(f, validate, retries)`：**拒絕採樣**——重抽到通過驗證為止。
- `compose.guard(f, validate, repair)`：**驗證→修復**——壞輸出交給 repair（可以是
  另一次 LLM 呼叫：「你上次的輸出不合格，原因是…，請修正」）。
- 驗證器 `validate` 可以是確定的（regex、JSON parse、語法檢查），
  也可以是另一個 LLM（LLM-as-judge，見 §4）。

> 前置條件（接 §多函數交互 §3）：`retry_until_valid` 要求被包的函式無累積副作用，
> 否則重試會出事。這是「組合對被組合者的契約」的具體案例。

### L3 聚合層 — 多次抽樣 + 統計，把方差換成穩定

單次抽樣有方差；抽很多次再統計，方差會被平均掉。

- `compose.vote(f, n)`：**自一致（self-consistency）**——同問題抽 N 次取多數。
- `compose.best_of(f, n, score)`：抽 N 次取最高分（用 scorer 把「好壞」可計算化）。
- `compose.fanout_reduce(fns, reducer)`：用**不同角度的函式**（不同 prompt/模型）跑同輸入，
  再彙整——多視角降偏誤。

> L3 反而**善用**隨機性：沒有隨機性，抽 N 次都一樣，投票毫無意義。
> 這是「在需要多樣的地方多樣」的正面用法。

### L4 編排層 — 約束「能做什麼」，而非只看「說了什麼」

最外層：不在輸出端救火，而在**動作空間**就設限。

- **hub**（`tools/hub.py`）：給 LLM 一份有界、有描述、大小受控的 skill 清單。
  LLM 只能從清單裡挑工具 → 動作空間從「無限文字」收成「有限工具集」。
- **router / switch**：把「LLM 自由發揮」換成「LLM 在固定分支裡選一個」。
- **decompose**（`compose.decompose`）：大模糊任務拆成小而受限的子任務，
  每個子任務輸出空間更小、更易驗證（回到 L0）。

> L4 的精神：**與其要 LLM 直接產出最終結果，不如讓它選擇/編排確定的工具來產出結果。**
> LLM 負責「決策」，確定函式負責「執行」。

---

## 3. 層次總表

| 層 | 手段 | 把「？」變成「！」 | 實作零件 |
|---|---|---|---|
| L0 契約 | 結構化輸出、typed I/O | 縮小輸出空間 | `llm_call.bind`、八軸 §1 |
| L1 確定化 | memoize、temp=0 | 重複輸入→確定 | `lib/memoize`、§6 idempotent |
| L2 驗證 | retry / guard | 偶爾對→保證對或明確失敗 | `compose.retry_until_valid` / `guard` |
| L3 聚合 | vote / best_of | 單次方差→多次穩定 | `compose.vote` / `best_of` / `fanout_reduce` |
| L4 編排 | hub / route / decompose | 自由發揮→有界選擇 | `tools/hub`、`router`、`switch`、`compose.decompose` |

---

## 4. 不只是防呆：更好地「利用」LLM

馴化框架反過來看，也是榨取 LLM 價值的框架：

1. **LLM-as-judge / critic**：L2 的 `validate`、L3 的 `score` 本身可以是 LLM 函式。
   生成函式（actor）+ 評審函式（critic）形成交互（見 `multi_function_interaction.md` §5）。
   一個 LLM 生成、另一個 LLM（或同一個換 prompt）挑錯，比單次生成可靠得多。

2. **冷熱分工**：把任務拆成兩種 LLM 函式——
   - **熱函式**（高 temperature、求多樣）：負責發想、生成候選。
   - **冷函式**（低 temperature、嚴格）：負責篩選、驗證、收斂。
   用 `best_of(熱函式, n, score=冷函式)` 一行接起來：熱的多生幾個，冷的選最好。

3. **便宜→貴的升級路徑**：`memoize`（命中就免費）→ 不命中才呼叫 LLM（貴）→
   `guard` 驗證 → 存回 cache。下次同問題免費且確定。成本與可靠性一起改善。

---

## 5. 端到端範例：一個「可靠的程式碼問答函式」

把五層串起來（全部用已實作的零件）：

```python
from lib import llm_call, compose, memoize

ask = llm_call.bind(                                  # L0：綁定角色 + 要求帶程式碼區塊
    system="你是資深工程師，回答務必包含一段 ```python 程式碼區塊",
    backend=...,                                       # 真接 API 時換成 Http backend
)
ask = compose.retry_until_valid(                       # L2：沒有程式碼區塊就重抽
    ask, validate=lambda o: "```python" in o, retries=3,
)
ask = compose.guard(                                   # L2：語法錯就請它修
    ask,
    validate=lambda o: _py_syntax_ok(o),
    repair=llm_call.bind(prefix="以下程式碼有語法錯，請只回修正後的版本：\n"),
)
# L1：同一個問題不重算（memoize 包在最外，命中就完全不碰 LLM）
mz = memoize.Memoizer("code_qa")
def code_qa(question: str) -> str:
    out, _hit = mz.cached_call(lambda: ask(question), stdin=question)
    return out
```

`lib_smoke_test.py` 的 `test_compose` / `test_llm_call` 已用 ScriptedBackend 驗證了
其中每個零件（retry/vote/best_of/guard/bind）的行為——上面只是把它們串成一條。

> **✅ 已做可跑 demo**：`demos/reliable_code_qa.py` 把上面五層完整串起來並自我測試。
> 跑 `python3 demos/reliable_code_qa.py` 會看到：retry 抽 2 次（第 1 次無程式碼被拒）、
> guard 觸發 1 次修復（語法錯被修）、memoize 第二次命中完全不碰 backend——
> 每一層都被斷言驗證確實生效。這是整套馴化框架「真的能組起來動」的端到端證據。

---

## 6. 與規範的關係 / 開放問題

1. 這套五層框架，是否該成為複合規範家族的一支「LLM 馴化慣例」？
2. 哪些該進 metadata 軸？候選：
   - `nondeterministic: true`（標記這函式是隨機的——目前八軸無此概念，但它是
     **觸發整套馴化框架的根**；類似 memoized 缺對應軸值的處境，見 `lib/memoize` 決策 3）。
   - 是否暴露 temperature / sampling 參數為標準 metadata。
3. L2 的「重試前置條件＝被包函式須無累積副作用」要不要寫成正式契約（接組合維度 §3）。
4. LLM-as-judge 形成的 actor-critic 交互，需要 `multi_function_interaction.md` §5 的
   blackboard driver 才能乾淨表達——兩份文件在此交會。
