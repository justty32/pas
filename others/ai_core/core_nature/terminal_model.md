# terminal_model.md

Terminal 執行模型基礎——POSIX shell 的原生概念，與本規範無關，是通用的社群知識。

但本規範大致上會依循此概念，以此作為基礎。

---

## §1 Terminal 執行模型基礎

### 1.1 最底層：命令解析

使用者在 shell 輸入一行文字，shell 將其切分為 word list（以空白分隔，特殊字符另行處理）：

```
command arg1 arg2 arg3 ...
```

- **第一個 word**：可執行物（binary、script、shell function、alias...）
- **後續 words**：傳入可執行物的參數，對應 C main 的 `argc` / `argv`

特殊字符（`|`、`>`、`<`、`&` 等）在此層之外，由 shell 自行處理，不進入 argv。

### 1.2 CLI 慣例（約定俗成）

在 argv 的基礎上，社群形成了一套通用慣例，本框架直接遵循，不重造。

#### 旗標形式

| 形式 | 語意 | 例子 |
|---|---|---|
| `-x` | 短旗標（單一字母） | `-v`、`-q` |
| `-x value` | 帶值的短旗標 | `-o file.txt`、`-n 5` |
| `-abc` | 短旗標合併（僅限不帶值的布林旗標） | `-vqr` = `-v -q -r` |
| `--flag` | 長旗標（布林，presence = true） | `--verbose`、`--dry-run` |
| `--flag value` | 帶值的長旗標（空白分隔） | `--output file.txt` |
| `--flag=value` | 帶值的長旗標（等號分隔，無歧義） | `--output=file.txt` |

短旗標與長旗標通常成對存在（`-v` / `--verbose`），但不強制——有些旗標只有長形式，反之亦然。

#### Positional arguments

無 key 標示的參數，解讀為有序 array，語意由工具自行定義：

```bash
git add file1 file2       # file1, file2 都是 positional
cp src dst                # 第一個是來源，第二個是目標
```

#### 特殊慣例

| 形式 | 語意 |
|---|---|
| `--` | 旗標結束標記。其後所有 word 一律視為 positional，不再解析為旗標。用於處理以 `-` 開頭的檔名 |
| `-` | **不在本規範中。** 語意（stdin 或 stdout）依賴程式的具體語意，規範無法裁定，故移除。需要接 stdin/stdout 的工具應改用明確旗標（`--input`、`--output`），或採「未指定檔案時預設讀 stdin」的 Unix 慣例 |
| `-h` / `--help` | 顯示使用說明，幾乎所有工具都應實作 |
| `--version` | 顯示版本號 |

#### stdin / stdout / stderr 慣例

| 串流 | 用途 |
|---|---|
| stdin | 輸入來源（未指定檔案時讀此） |
| stdout | 正常輸出結果（可被 pipe 或重導向） |
| stderr | 錯誤訊息、診斷資訊（不進 pipe，直接顯示給使用者） |

#### Exit code 慣例

| 值 | 語意 |
|---|---|
| `0` | 成功 |
| 非 `0` | 失敗（具體值由工具定義，`1` 最通用） |

### 1.3 Subcommand 模式（git-style）

建立在 1.2 之上的組合模式。第一個 positional arg 作為 subcommand，其後的 args 屬於該 subcommand：

```
command subcommand [flags] [positional...]
```

例：
```bash
git commit -m "msg"
git log --oneline
sfc greet --name Alice
```

本框架的所有工具（sfc、router、hub 等）均採 git-style subcommand CLI。

這種模式的支援僅由程式撰寫者自行實現，本規範只是規定說，若有類似的subcommand操作需要實現，那就必須用這種表現方式。