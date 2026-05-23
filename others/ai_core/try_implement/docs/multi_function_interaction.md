# 多函數交互：組合維度（concept draft）

> try_implement 的概念拓展文件。回應「在八軸與複合概念之外，往多函數的合作與交互拓展」。
> 這是提案草稿，非定案規範；對應實作見 `lib/compose.py`、`lib/trace.py`、`lib/call.py`。

---

## 1. 八軸描述「一個函式」，但沒描述「函式怎麼一起動」

現有的八軸（lifecycle / state / interruptible / guarantee / I/O 通道…）回答的都是
**單一函式的執行本性**：它活多久、有沒有副作用、能不能中斷、能不能重試。

但 ai_core 的價值不在單一函式，而在**把很多函式組起來**——一個 LLM 包裝函式的輸出
餵給一個 linter，再餵給一個彙整器；或同一個問題問三次取多數。這個「怎麼組」的問題，
八軸一個字都沒提到。

**主張：組合（composition）是與八軸正交的另一個維度。** 八軸是「名詞的屬性」，
組合是「動詞」。要把它變成一等公民，而不是每次都臨時用 shell pipe 硬接。

---

## 2. 組合的基本形態

`lib/compose.py` 把這些做成了可疊套的組合子（每個都吃 `f(str)->str`、回 `f(str)->str`）：

| 形態 | 組合子 | 語意 | 對應既有概念 |
|---|---|---|---|
| 順序 | `pipe(f, g, h)` | 前一個輸出餵下一個 | 調用鏈 / shell pipeline |
| 並聯 | `fanout` / `fanout_reduce` | 同輸入多分支，可再彙整 | map / map-reduce |
| 條件 | `route(selector, table)` | 依條件分派到不同函式 | **Switch**（thinking_routing） |
| 分治 | `decompose(split, sub, join)` | 拆 → 各自處理 → 合 | 分而治之 |
| 反覆 | `vote` / `best_of` / `retry_until_valid` | 對**同一函式**反覆採樣再選 | 自一致 / 拒絕採樣 |

關鍵性質：因為輸入輸出型別不變（`str->str`），組合子可以**無限疊套**——
`pipe` 裡套 `vote`、`vote` 裡套 `retry_until_valid`。這是「組合維度」能成立的前提。

---

## 3. 組合也有執行本性：軸的「推導規則」（真正的概念拓展）

最有意思的延伸：**組合子產出的新函式，它自己的八軸是什麼？** 這不該由人重新標註，
而應能從「組成它的函式的軸」**推導**出來。提出一組推導規則的雛形：

### guarantee（執行保證）

- `pipe(f, g)`：整體保證 = **各段的最弱保證**。一條鏈裡只要有一段不是 idempotent，
  整條重跑就不安全。（最弱連結原則）
- `fanout(f, g)`：若各分支寫**不同**外部狀態，保證 = 各自保證的交集；若寫**同一**狀態，
  退化為 `none`（並發寫衝突）。
- `retry_until_valid(f)`：要求 `f` 至少 idempotent，否則重試會累積副作用——
  **這是組合對被組合者的「前置條件」**，本身就是一條值得入規範的規則。

### state（跨呼叫狀態）

- 任何組合的 state = 各成員 state 的**聯集**（只要有一個 stateful_external，整體就是）。
- `state_dirs` 同理取聯集——這正好讓 hub 能算出「呼叫這個複合函式，會碰哪些目錄」。

### lifecycle

- 組合通常是 one_shot；但若任一成員是 persistent（server），整體變成「依賴某 server
  在線」的 one_shot——這帶出一個新狀態：**「有外部 server 相依」的 lifecycle 變體**，
  目前八軸沒有，值得補。

### interruptible

- `pipe` 的可中斷性 = 在「段與段之間」最安全；段內中斷則取該段的 interruptible。
  → 提示一個自然的 checkpoint 邊界：**每段之間就是天然的恢復點**（接 `lib/recovery`）。

> 這組推導規則若成立，hub 就能對「臨時組起來的複合函式」自動算出 metadata，
> 不必人工標註——這是把組合維度接回八軸的橋。**建議列為複合規範家族的候選議題。**
>
> **✅ 已做原型**：`lib/compose_meta.py` 把上述規則寫成可跑的 `MetaFn` + `mpipe` / `mfanout_reduce`：
> guarantee 取最弱、state/state_dirs 取聯集、persistent 成員列入 `requires_persistent`、
> fanout 共用 state_dir 時 guarantee 退化 none 並帶 warning。並用 `mretry` 把「retry 要求被包
> 函式至少 idempotent」這個前置契約做成執行期檢查。測試見 `lib_smoke_test.py::test_compose_meta`。
> 簡化處（guarantee 強度序、interruptible 暫不推導）記在該檔檔頭。

---

## 4. 與既有工具的對應

組合維度不是憑空新增，現有工具早已是它的特例：

- **Router** = `route` 的退化（selector 就是「查表名稱」）。
- **Switch** = `route` + 條件 selector。
- **SFC** = 被組合函式的**倉庫**（提供 `f` 們）。
- **trace** = 組合的**可觀測性**（pipe/fanout 在執行期長成一棵調用樹）。
- **call** = 讓組合的成員可以跨邊界（in-process / subprocess / http），組合子不在意成員在哪。

換句話說：`compose` 是把這些散落工具背後的共同骨架，提煉成顯式的概念。

---

## 5. 交互（interaction）≠ 組合（composition）

上面都是**單向**的：資料從輸入流到輸出。但「多函數**交互**」更強——函式之間**來回**：

- actor-critic：生成函式產出 → 批評函式挑錯 → 生成函式據此修改 → 再批評…
- debate / ensemble：多個函式互相反駁，收斂到共識。
- 對話迴圈：函式與環境（或使用者、或另一個函式）多輪往返。

交互比組合難，因為它需要兩樣組合沒有的東西：**共享狀態** 與 **終止條件**。
提出交互的最小模型：

```
driver(participants, state, until):
    while not until(state):
        for p in participants:
            state = p(state)      # 每個參與者讀寫共享 state
    return state
```

- `state` 是黑板（blackboard），參與函式輪流讀寫。
- `until` 是終止謂詞（達成共識、達到輪數上限、通過驗證…）——**沒有它，交互不會停**，
  這正是 LLM 交互最容易出事的地方（無限互踢）。
- 這個模型直接接 `lib/state_dirs`（state 可落地）、`lib/recovery`（多輪可中斷恢復）、
  `lib/singleton`（輪數/成本上限 = consume rate 守門）。

> **✅ 已實作**：`lib/interact.py` 提供這個 blackboard driver（`run`），以及兩個高階模式：
> `actor_critic`（生成↔批評來回修，= LLM-as-judge）與 `debate`（多方論點 → judge 收斂）。
> `max_rounds` 是**強制安全閥**——即使 `until` 永不成立也保證停（直接回應上面「沒有終止
> 條件，交互不會停」的隱患）。測試見 `lib_smoke_test.py::test_interact`。

---

## 6. 開放問題

1. 軸推導規則（§3）要做到多細？只推 guarantee/state，還是全八軸？
2. 交互的「終止條件」要不要標準化成一個 metadata 概念（像 §5 interruptible 那樣）？
3. 組合子本身算不算「函式」——能不能被 SFC 收錄、被 hub 列進 skill 清單？
   （若能，LLM 就能「自己組裝工具鏈」，這很強但也很危險。）
4. 並聯（fanout）目前是順序執行的；真並發要不要進來？並發一進來，§並發 的立場
   （核心規範不處理多實例並發）就會被挑戰。
