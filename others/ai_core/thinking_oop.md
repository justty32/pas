# thinking_oop.md

新想法紀錄（2026-05-20）

---

## 貫穿始終的兩個理念

**metadata**（程式對自身的描述）、**index**（程式/函數的位址）、**hub**（聚集索引）是貫穿整個系統的三個核心理念。理念本身不變，但在不同邊界上以不同的形式出現：

| 邊界 | metadata 的形式 | index 的形式 | hub 的形式 |
|---|---|---|---|
| 命令行（單檔程式） | `--metadata` flag → JSON | OS 檔案系統路徑（`./code_senior.sh`） | hub scanner 掃描可執行檔 |
| 程式內部（函數） | `ip.register()` 的描述參數 | 原始碼位置（`file.py:44`）或 runtime registry | `FunctionManager` / registry |
| Python library（class） | base class 的類別屬性 + `metadata()` | module 路徑（`mymodule.Professor`） | hub scanner 掃描 subclass |

形式不同，理念相同。設計新機制時，先問：「這裡的 index 長什麼樣？metadata 長什麼樣？hub 長什麼樣？」

---

## 核心洞見：metadata 與 hub 的本質

- **metadata** 的本質：程式對自身的描述
- **hub** 的本質：對程式的**聚集**索引

### 索引的三個層次

| 層次 | 索引誰 | 天然索引 | 聚集器 |
|---|---|---|---|
| 跨程式 | 獨立可執行檔 | 作業系統檔案系統路徑（`/bin/program`） | hub |
| 程式內部 | 程式內的函數 | 原始碼位置（`file.py:44`） | `FunctionManager` / `function_indexes` 全局 class |

兩層的結構完全對稱：環境本身都已提供天然索引，聚集器的工作只是把這些分散的天然索引**收攏成一份清單**。

**邊緣案例**：執行期間動態生成的函數沒有靜態行號可用作天然索引，只能由程式自行維護額外的索引結構（dict、registry 等）。此情況暫不設計。

Hub 做的是**跨程式的聚集**，`FunctionManager` 做的是**程式內的聚集**，兩者是同一概念在不同邊界上的顯示形象。

`--metadata` flag 與 hub scanner 是這兩個概念在**命令行世界**的顯示形象。

在**Python library 世界**，同樣的概念自然對應到 OOP：**繼承於提供這兩個功能的 base class**。

---

## CLI 與 OOP 的統一

CLI 世界的 `--metadata` 是 base class metadata 的**跨行程序列化格式**。
Base class 本身就是 metadata；`--metadata` 只是把它印成 JSON 讓另一個行程能讀到。
兩者是同一個概念在不同邊界上的顯示形象。

```
Python class  ──(同一個行程)──→  MetadataView 物件
CLI 執行檔    ──(行程邊界)────→  --metadata → JSON → MetadataView 物件
```

Hub 不需要知道來源是哪種，終點都是 `MetadataView`。

---

## Base Class 設計

```python
class Function(ABC):
    # 類別層級宣告 metadata（子類別 override）
    name: str = ""
    description: str = ""
    execution_model: str = "one-shot"   # pipe-and-script / one-shot / persistent / server
    retry_safe: bool = True
    reversible: bool = False
    undo_method: str = "none"
    memory_hints: list[str] = []
    complexity: str = "low"
    semantic_coupling: list[str] = []
    # ... 其他 MetadataView 欄位

    @classmethod
    def metadata(cls) -> MetadataView:
        """從類別屬性組出標準 MetadataView。"""
        ...

    @abstractmethod
    def run(self, input: str) -> str:
        """子類別實作實際邏輯。"""
        ...
```

**設計原則**：base class 只負責**宣告介面**（metadata 欄位 + 抽象 `run()`）。
Auto CLI 生成、hub 自動註冊等功能作為獨立的 opt-in 工具，不內建於 base class——
否則違反 KISS，base class 會變成 framework。

---

## 推論一：Auto CLI 生成

有了 base class，CLI wrapper 是純樣板程式碼，可以自動產生。
`--input`、`--output`、`--metadata`、`--json-errors` 全部從 base class 來。

**寫 Python class 就同時得到 CLI 介面，不用手寫兩份。**

---

## 推論二：Hub 統一掃描兩個世界

| 來源 | 掃描方式 | 終點 |
|---|---|---|
| 可執行檔 | 呼叫 `--metadata`（CLI 協定） | `MetadataView` |
| Python module | import 後找繼承 `Function` 的 subclass | `MetadataView` |

---

## 推論三：`execution_model` 驅動不同 lifecycle

Base class 可依宣告的 `execution_model` 提供不同的方法簽名（opt-in subclass）：

| execution_model | 方法簽名 |
|---|---|
| `one-shot` | `run(input) -> output` |
| `persistent` | `start()` / `on_message()` / `stop()` |
| `server` | 產生 FastAPI app |

---

## 統一呼叫介面（Unified Call Interface）

索引解決「找到在哪」，呼叫介面解決「如何使用」。兩者合起來才是完整的抽象。

### outside_progs：從外部呼叫單檔程式或 module

目標：不論目標是 shell script、Python module 內的函數、還是 server，呼叫端一律用相同介面：

```python
import outside_progs as op

ret = op.call("../code_senior.sh", {"lang": "c"})
ret = op.call("mymodule.Professor", {"type": "senior c coder"})
```

第一個參數是**天然索引**（路徑或 module 位址），第二個參數是輸入。

library 內部依據 `execution_model`（從 metadata 取得）自動分派：

| execution_model | 內部實作 |
|---|---|
| `pipe-and-script` | subprocess 呼叫，stdin/stdout 傳遞 |
| `one-shot` | subprocess 或直接 import + 呼叫 `run()` |
| `persistent` | JSON-RPC over stdin/stdout |
| `server` | HTTP request |

呼叫端不需要知道底層是哪種，metadata 讀一次就夠。

### inside_procs：程式內函數對外暴露

程式內的函數若要被外部的單檔程式或 shell 呼叫，程式必須主動暴露這些函數。`inside_procs` 做兩件事：

1. **建立內部 registry**（即前述 `FunctionManager`）：`ip.register()` 把函數登記進去
2. **自動生成 CLI dispatch**：讓外部可以用命令列指名呼叫特定函數

```python
import inside_procs as ip

ip.register(func_code_senior, "code_senior", {"lang": "c"})
```

外部單檔程式透過命令列呼叫（假設程式名為 `seniors`）：

```bash
seniors --ip "code_senior" --lang "c"
```

`--ip` 路由到 registry 中對應的函數，其餘參數作為輸入傳入。

`inside_procs` 與 `outside_progs` 是一對：一個負責「把內部暴露出去」，一個負責「從外部統一呼叫進來」。

---

## 與 `protocol/` 的關係

Base class 自然放在 `src/ai_core/protocol/` 下——
`protocol/` 已定義為 function 作者與 manager 作者的共用 helper 出口。
這個 base class 就是 Python 世界裡的「協定」本身。
