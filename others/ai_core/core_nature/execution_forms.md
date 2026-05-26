# execution_forms.md

函式執行形式在 terminal 中的對應。這套分類本質上是跨環境的，terminal 只是最純粹的起點。

---

## §0 分類框架：多維描述軸

執行單元的描述空間是**多維的**。§4 的平鋪清單是毛料——把各軸上的概念先攤出來——後續重組時應以下列軸為基礎，而非繼續往清單裡追加。

| 軸 | 描述的問題 | 例子 |
|---|---|---|
| **I/O 型態** | 輸入從哪來、輸出往哪去、是否需要執行途中的互動 | 無輸入、stdin、互動式（中途需 stdin）、streaming push、streaming pull |
| **生命週期** | 執行單元從啟動到結束的持續模式 | one-shot、persistent、lazy/warm、detached |
| **跨呼叫狀態** | 單次執行以外是否保有、影響或累積狀態 | stateless、stateful-external、stateful-internal |
| **資源特性** | 對計算資源的消耗或佔用（含時間） | 執行時間、記憶體、CPU、GPU；對應 `--metadata` 的聲明內容 |
| **可中斷性** | 是否可以被暫停、暫停後可否恢復、恢復後副作用為何 | 不可中斷、可暫停（SIGSTOP）、可恢復（checkpoint/restore） |
| **執行保證** | 對系統狀態的承諾，獨立於執行次數或中途失敗 | idempotent、transactional（ACID）、dry-run |
| **組合模式** | 執行單元如何與其他單元構成更大的結構 | fan-out/fan-in、proxy/wrapper、hook/callback、agentic loop |
| **環境模式** | 執行環境是預先存在還是動態建立與銷毀 | 固定環境、ephemeral/JIT |
| **確定性 / 隨機性** | 同輸入是否同輸出；隨機環節（LLM）的認證狀態 | deterministic（預設）、nondeterministic（未認證 / 帶證書）；見 [`axis_spec.md §9`](axis_spec.md) |

> 「確定性 / 隨機性」是繼前八軸之後**新增的第九軸**。前八軸隱含「函式是確定性的」前提，無一能描述
> LLM 這種天生隨機的函式，且此性質無法由任何既有軸隱含——故獨立成軸。它同時承載治理原則的證書
> （見 `roadmap.md §3.4`）。詳見 `axis_spec.md §9` 與 `lib_spec.md §9`。

同一個執行單元可以在多個軸上各有描述，例如：
- `terraform apply`：one-shot（生命週期）× idempotent + transactional（執行保證）× 固定環境（環境模式）
- `docker run --rm`：one-shot × ephemeral/JIT
- LLM Entry Manager：persistent × singleton × stateful-internal × GPU 資源約束

---

## §4 函式形式在 terminal 中的對應

### 4.1 One-shot

**定義**：執行一次、產生輸出、結束。無狀態，無副作用（除了明確的輸出）。

Terminal 表現：
- stdin → process → stdout / stderr
- exit code 0 = 成功，非 0 = 失敗
- 大多數 Unix 工具屬此類：`grep`、`sed`、`awk`、`jq`...

One-shot 是最基本的形式，也是 pipeline 組合的基礎單元：

```bash
cat file.txt | grep "error" | wc -l
```

每個節點都是獨立的 one-shot process，stdout 自動接到下一個的 stdin。

---

### 4.2 Multi-shot

**定義**：跨多次呼叫保有狀態，本次執行結果影響下次。

Terminal **沒有原生支援**。Multi-shot 在 terminal 中必須拆解為：

> **one-shot + 外部狀態管理**

狀態的持久化策略（由工具自行定義）：

| 策略 | 做法 | 備註 |
|---|---|---|
| 狀態檔 | 每次呼叫讀入 `--state-file path`，執行後寫回 | 最通用，明確可見 |
| 固定路徑慣例 | 工具固定讀寫 `~/.tool/state` 或 `./.tool_state` | 隱式，呼叫者無需指定 |
| 輸出即狀態 | 上次 stdout 直接作為下次 stdin 輸入（無副作用） | 最純粹，但狀態大時不方便 |

**重點**：工具的 `--metadata` 必須聲明它是 multi-shot，並說明狀態的存放位置與格式，否則呼叫者無從得知如何正確使用。

**狀態所有權的兩種子型：**

| 子型 | 說明 | 呼叫者介面 |
|---|---|---|
| Caller-managed | 呼叫者保管狀態，顯式傳入 `--state-file path` | 呼叫者對狀態有完整控制，也需自行處理初始化與清除 |
| Self-managed | 函數自行決定狀態存放路徑（固定路徑慣例） | 呼叫者直接呼叫，無需傳入狀態參數；狀態對呼叫者透明 |

兩者行為語意相同（跨呼叫保有狀態），差別只在**誰持有狀態的所有權**。

---

### 4.3 Persistent

**定義**：長期存活，持續等待呼叫，不主動結束。

Terminal 有兩種子型：

#### 子型 A：互動式（Interactive / REPL）

從 stdin 讀取輸入，處理後輸出到 stdout，循環直到收到結束訊號（EOF 或特定指令）：

```bash
python3        # REPL
sqlite3 db     # 互動式 SQL
```

通訊介面：stdin / stdout（與 one-shot 相同，但 process 不結束）

#### 子型 B：Server / Daemon

在背景持續運行，透過 IPC 機制等待請求：

| IPC 機制 | 說明 |
|---|---|
| Unix socket | 本機 IPC，效能高，路徑即位址 |
| TCP port | 可跨機器，HTTP/JSON-RPC 常用此 |
| Named pipe（FIFO） | 單向，較少用於雙向通訊 |

啟動方式：`&` 置於背景，或由 systemd / init 管理。

**結論**：Persistent 程式建議設計成 server（子型 B），而非互動式。原因：server 可被程式化呼叫，互動式只能給人用。

---

### 4.4 Singleton

**定義**：資源受限，系統中同時只能存在一個（或有限數量的）實例。

Singleton 不是一種「執行形式」，而是一種**資源約束**，可疊加在 persistent 上（最常見）。

Terminal 的實作慣例：

| 機制 | 做法 |
|---|---|
| PID 檔 | 啟動時寫 PID 到 `~/.tool/tool.pid`，啟動前先檢查是否已有 running 實例 |
| Lock 檔 | `flock` 取得獨佔鎖，後來的啟動嘗試直接失敗或等待 |
| OS 服務管理 | 交給 systemd，由 OS 保證單例 |

**典型案例**：LLM Entry Manager——本地 GPU 是有限資源，不允許多個實例同時搶占，因此設計為 singleton persistent server。

---

### 4.5 Streaming

One-shot 的輸出變體：執行期間**邊算邊輸出**，而非等全部完成才輸出。

Terminal 表現：stdout flush 不緩衝（Python 用 `-u` 或 `sys.stdout.flush()`，或 `unbuffer`）。

從 process lifecycle 角度仍是 one-shot（執行完就結束），但輸出是增量的。典型例子：`tail -f`、ping、串流 LLM 回應。

與 persistent 的區別：persistent 等待多個獨立呼叫，streaming 是**單次呼叫**內產生連續輸出。

**變體：Pull-based / Generator 模型**：上述為 push-based（函數主動推送輸出）。Pull-based 反過來——由 caller 主動拉取一個值，函數在兩次拉取之間暫停。Python generator（`yield`）是典型例子。在 terminal 層幾乎不可見（shell 管道預設 push），但在程式內部函數中是獨立的概念。

---

### 4.6 Lazy / Warm

介於 one-shot 與 persistent 之間的中間態：**第一次呼叫才啟動，之後在一段時間內保持活躍等待下一次呼叫。**

| 屬性 | 說明 |
|---|---|
| 啟動方式 | 第一次呼叫時才初始化（非預先常駐） |
| 存活策略 | 呼叫後保持一段 idle 時間（timeout 後自動關閉） |
| 適用場景 | 啟動代價高、但呼叫頻率不固定的工具（如 LLM inference runtime） |

可視為 persistent 的子類（「不預先常駐的 persistent」），或獨立分類——設計上待定。

---

### 4.7 Detached / Fire-and-Forget（分離式 / 射後不理）

**定義**：被呼叫後，立即啟動一個背景任務（或將任務交接給系統守護行程），主行程瞬間結束並回傳狀態，不等待實際任務運算完成。

Terminal 表現：`nohup command &`、`disown`，或不帶 `--wait` 的 `systemctl start <service>`。

與 One-shot 的差異：One-shot 會阻塞呼叫者直到任務完成並輸出結果；Detached 立刻釋放控制權，實際任務的輸出通常導向 log 檔、`/dev/null`，或透過 webhook 異步回傳。

適用場景：觸發耗時極長的非同步任務（大規模資料遷移、觸發 CI/CD pipeline）。

**變體——Async with Result Retrieval（非同步帶回傳）**：主行程立即結束並回傳 job ID，呼叫者之後透過輪詢（polling）或回調（callback）取回結果。純 Fire-and-Forget 是呼叫者不關心結果；此變體是呼叫者**延遲取回**結果。

---

### 4.8 Fan-out / Fan-in（散佈與收集）

**定義**：複合型執行形式。主行程作為協調者（Coordinator），將任務拆解並同時啟動多個子任務（Fan-out），等待所有子任務完成後，將結果聚合（Fan-in）再統一輸出。

Terminal 表現：`GNU parallel`、`xargs -P`、`make -j`。

與 One-shot pipeline 的差異：標準 pipeline（`A | B | C`）是線性串流；Fan-out / Fan-in 是樹狀的平行展開與收斂，本質是為了最大化利用多核資源。

---

### 4.9 Idempotent（冪等式）

**定義**：無論執行一次還是連續執行一百次，對系統狀態造成的改變和最終結果都完全相同。可視為「目標狀態導向」的特殊 One-shot：若系統已達目標狀態，則不產生任何副作用操作。

Terminal 表現：`mkdir -p /path`、`rm -f file`、`rsync`，以及幾乎所有 IaC 工具（Terraform、Ansible）。

與 Multi-shot 的差異：Multi-shot 的狀態通常是「累加」或「推進」的（如對話歷史）；Idempotent 是確保狀態**收斂**到預期的絕對基準線上。

---

### 4.10 Suspendable / Resumable（可中斷與恢復）

**定義**：執行到一半可以被掛起（暫停），釋放當下的運算或網路資源，並在未來某個時間點從中斷處繼續執行，而不是從頭開始。

Terminal 表現：
- OS 層級：`Ctrl+Z` 觸發 `SIGSTOP`，後續以 `fg` / `bg` 恢復
- 應用層級：支援斷點續傳的工具（`wget -c`、`rsync --partial`），或使用 CRIU 保存行程記憶體狀態

與 Lazy / Warm 的差異：Lazy 是在等待「下一次新的呼叫」；Resumable 是暫停「當前尚未完成的長期任務」。

---

### 4.11 Interactive Wizard（步進互動式）

**定義**：以收集參數為目的的短期互動。按順序詢問一系列問題，收集完畢後執行一次性任務，然後結束。

Terminal 表現：`npm init`、`ssh-keygen`、`apt-get install`（遇到需配置選項時）。

與 Persistent 子型 A（REPL）的差異：REPL 的生命週期是無窮迴圈（Read-Eval-Print Loop）；Wizard 是有限狀態機，走完特定設定流程後，轉化為 One-shot 執行並結束。

---

### 4.12 Transactional（事務式）

**定義**：一系列步驟要麼全部成功（commit），要麼全部回滾到初始狀態（rollback），不留中間殘局。

Terminal 表現：`git commit`（all-or-nothing）、資料庫 transaction、`rsync` 的原子替換（先寫 temp 再 rename）。

與 Idempotent 的差異：Idempotent 保證「重複執行安全」；Transactional 保證「中途失敗不留殘局」。兩者正交，常一起出現（如 Terraform apply：idempotent + transactional）。

---

### 4.13 Memoized / Cached（快取式）

**定義**：同樣的輸入若已計算過，直接回傳快取結果而不重新執行，計算只發生一次（或快取失效前只發生一次）。

Terminal 表現：`ccache`（C/C++ 編譯快取）、`pip` 的 wheel cache、`make` 的 target 時間戳依賴判斷。

與 Idempotent 的差異：Idempotent 關注「副作用安全性」（重複執行不造成多餘改變）；Memoized 關注「計算的跳過」（輸入相同則完全略過執行）。前者是 correctness 保證，後者是 performance 最佳化。

---

### 4.14 Dry-Run / Simulation（模擬執行 / 試運行）

**定義**：執行完整的邏輯運算與狀態比對，但攔截所有對系統的實際修改（副作用），僅向 stdout 輸出「如果真的執行，將會發生什麼事」。

Terminal 表現：`terraform plan`、`rsync -n`（或 `--dry-run`）、`apt-get install -s`。

與 One-shot 的差異：這是對「有副作用任務」的唯讀鏡像。它回傳的是執行計畫或意圖（Intent），讓呼叫者在實際改變狀態前進行確認，是基礎設施與高風險操作的必備形式。

---

### 4.15 Hook / Callback（掛鉤 / 生命週期回呼）

**定義**：不預期由人類使用者直接呼叫。被「註冊」到另一個宿主（Host）應用程式的生命週期中，在特定事件發生時被系統性地觸發。

Terminal 表現：Git hooks（`.git/hooks/pre-commit`）、Linux 套件管理器 hooks（pacman hooks）、systemd 服務的 `ExecStartPre` / `ExecStopPost`。

執行約束：I/O 與環境變數完全由宿主提供。Exit code 直接決定宿主行程是否能繼續推進（hook 回傳非 0，git commit 即被強制中斷）。

---

### 4.16 Ephemeral / JIT Execution（臨時 / 用後即棄執行）

**定義**：執行前動態拉取依賴、建構環境，執行一次性任務後立刻銷毀整個運行環境，不留任何痕跡。

Terminal 表現：`npx <package>`、`docker run --rm <image>`、`nix run`。

與 One-shot 的差異：One-shot（如 `grep`）假設執行環境與依賴已固定存在；Ephemeral 將「環境的建構與銷毀」封裝進單次呼叫中，保證極致的環境隔離與無狀態性。

---

### 4.17 Proxy / Wrapper（代理 / 包裝器）

**定義**：包裝在目標指令外層，攔截、監控或修改其環境變數、I/O 串流或系統呼叫，然後將控制權透傳（Pass-through）給內部實際運作的行程。

Terminal 表現：`time <command>`（測量耗時）、`strace <command>`（追蹤系統呼叫）、`sudo <command>`（提權）、`env VAR=1 <command>`。

與 Pipeline 中介點的差異：Pipeline 節點只處理純資料；Proxy / Wrapper 處理的是「執行環境的殼」。其生命週期與被包裝的子行程（Child Process）完全綁定。

---

### 4.18 Agentic / Autonomous Loop（自主代理迴圈）

**定義**：高度動態的 Multi-shot 變體。行程啟動後，根據自身的輸出或外部環境的反饋，自主決定下一步的執行路徑，直到滿足某個終止條件。

Terminal 表現：AutoGPT 終端介面、具備 Tool-use / Function Calling 的本地端 LLM 代理腳本。

執行特徵：傳統 Shell Script 或 Pipeline 是預先寫死的有向無環圖（DAG）；Agentic 形式的執行流程是**執行期動態生成**的，具備「觀察 → 思考 → 行動」的非確定性迴圈。

---

## §5 觸發機制（正交軸）

§4 的執行狀態描述「執行後的行為」；**觸發方式**是另一個正交軸，描述「由什麼啟動執行」。

| 觸發機制 | 說明 |
|---|---|
| 直接呼叫 | §4 各節隱含的預設，caller 主動發起 |
| Event-driven | 被外部事件推送觸發（message queue、webhook、filesystem watch） |
| Scheduled | 由時間觸發（cron、systemd timer） |

兩個軸可自由組合：

| 組合範例 | 說明 |
|---|---|
| scheduled + one-shot | 定時跑的批次任務 |
| event-driven + persistent | 收到事件才喚醒的常駐服務 |
| scheduled + multi-shot | 定時累積狀態的定期任務 |

Terminal 實作：

| 觸發機制 | 常見工具 |
|---|---|
| Scheduled | `cron`、`systemd timer` |
| Event-driven | `inotifywait`（filesystem）、消費 message queue 的 consumer process |
