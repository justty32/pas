# thinking_production.md

新想法紀錄（2026-05-20）

---

## 兩個維度：使用 vs 生產

前面所有的討論（index / metadata / hub / outside_progs / inside_procs）都是在處理**使用管理**——如何找到、描述、呼叫已存在的程式或函數，且預設是人類手寫的邏輯、one-shot 的情境。

這裡要開始思考另一個同樣基礎的維度：**生產管理**——如何產生程式或函數。生產者可以是：

- 人類手寫
- 程式生成的程式（meta-programming）
- AI 生成的程式（LLM codegen）

---

## 命令行世界的生產：pipeline 模式

CLI 單檔程式的生產方式很自然，用 pipe 串接：

```bash
code_seniors.sh --lang c \
  | prompt_appen.sh "generate a for loop" \
  | text_inserter.sh --file "main.c" --line 43
```

這條 pipeline 的語意是：「產生一段 C 的 for loop，插入 main.c 第 43 行」。
輸出物是**檔案的一部分**，生產過程是一次性的 pipe。

---

## 待思考的問題

### 1. 產出物很小的情況

當產出物不是一整個程式，而是一個函數、一個片段、甚至一行程式碼時，pipeline 的開銷（行程啟動、stdin/stdout 傳遞）可能遠大於產出物本身。這時：
- 是否應該直接在程式內部呼叫 LLM，而不走 shell pipe？
- 產出的小片段如何被納入 index / metadata / hub 的管理框架？

### 2. 程式內函數的生產

對於程式內部動態生成的函數（參見 `thinking_oop.md` 的邊緣案例）：
- 生成後要如何自動登錄進 `FunctionManager` / registry？
- 生成的函數沒有靜態原始碼位置，index 如何處理？

### 3. 生產與使用的銜接

生產出來的東西，最終還是要被「使用」。生產管理要如何與使用管理的三個理念（index / metadata / hub）銜接？
- 生產完成後，自動補上 metadata？
- 自動登錄進 hub？
