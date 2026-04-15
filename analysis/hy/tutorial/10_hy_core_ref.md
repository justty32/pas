# Hy 核心庫參考 (10_hy_core_ref.md)

Hy 內置了一些方便的函數（位於 `hy.core`），這些函數讓 Python 的操作更具 Lisp 風格。

## 1. 常用檢查函數
*   `empty?`: 檢查容器是否為空。
*   `even?` / `odd?`: 檢查奇偶性。
*   `none?`: 是否為 `None`。
*   `instance?`: 等同於 `isinstance`。

```hylang
(print (empty? []))      ; True
(print (even? 10))       ; True
(print (none? None))     ; True
```

## 2. 數值工具
*   `inc`: 加一。
*   `dec`: 減一。

```hylang
(print (inc 5)) ; 6
(print (dec 5)) ; 4
```

## 3. 符號與模型操作
如果你在編寫宏，這些函數非常重要：
*   `hy.models.Symbol`: 創建符號。
*   `hy.models.Keyword`: 創建關鍵字。
*   `hy.models.Expression`: 創建表達式。

## 4. 動態求值
*   `hy.eval`: 在運行時求值 Hy 表達式。
*   `hy.read`: 將字串解析為 Hy 模型（不執行）。

```hylang
(setv model (hy.read "(+ 1 2)"))
(print (hy.eval model)) ; 3
```

## 5. 總結
Hy 不僅僅是語法糖，它還通過這些核心工具優化了開發體驗。建議在開發時隨時查閱 `hy.core` 的官方文檔。
