# data_format.md

跨工具的通用資料格式規範。

---

## §3 資料結構：JSON 作為通用格式

### 3.1 設計立場

系統以 **JSON** 作為跨工具的通用資料格式。所有工具的結構化輸入輸出、metadata、設定檔，一律以 JSON 表示。

CLI 參數（argv）與 JSON 之間的轉換是日常操作，不自行實作，直接採用現有工具。

### 3.2 CLI argv → JSON（不重造輪子）

| 工具 | 環境 | 說明 |
|---|---|---|
| `argparse` + `vars()` | Python 標準庫 | `vars(parser.parse_args())` 直接得到 dict，`json.dumps()` 完成轉換。零外部相依，**首選**。 |
| `click` | Python（外部） | 比 argparse 更人性化，context 物件可取出所有參數為 dict，但引入外部相依。 |
| `jsonargparse` | Python（外部） | 專為 CLI ↔ JSON/YAML 設計，支援 nested object（`--model.layer 3`），功能最強，相依最重。 |
| `jo` | Shell | `jo name=Alice age=30` → `{"name":"Alice","age":30}`，輕量但不解析 `--flag` 語法。 |

**結論**：主力使用 `argparse` + `vars()`，符合「最少相依、CLI 一等公民」原則。Subcommand 結構透過 `add_subparsers` 處理，輸出 dict 結構直接對應 subcommand 樹。
