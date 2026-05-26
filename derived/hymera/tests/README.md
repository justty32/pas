# hymera 測試

> 狀態：⏳ 骨架。v1 實作階段才會填入。

## 規劃

依 `../docs/07_examples.md` 與 `../PROJECT.md` §5.4：

1. **節點層**：每個 AST 節點型別至少一個 emit 正向測試（檢查輸出字串）。
2. **Pass 層**：每個 Pass 至少一個輸入/輸出對照測試。
3. **端對端**：四個範例 A/B/C/D 整檔生成 + 外部編譯器接受度（gcc / clang++）。

## 執行

```bash
pytest tests
```

注意：`conftest.py` 必須在第一行 `import hy`，否則 `.hy` 測試檔不會被收集（詳見 `../../../analysis/hy/tutorial/09_testing_interop.md` §2）。
