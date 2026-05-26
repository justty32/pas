# 非同步、生成器與裝飾器 (08_async_decorators.md)

> 對齊版本：**Hy 1.3.0**。本章修正 Hy 0.x 的多項過時寫法：`async-defn`、`with-decorator`、`yield-from`、2-arg `if` 等。

## 1. 非同步編程 (AsyncIO)

Hy 1.x **沒有** `async-defn`。要定義協程，在 `defn` 後加 `:async` 關鍵字（規則來源：`projects/hy/hy/core/result_macros.py:1587`）。

```hylang
(import asyncio)

(defn :async slow-hello []
  (await (asyncio.sleep 1))
  (print "哈囉，非同步！"))

(defn :async main []
  (print "等待中...")
  (await (slow-hello)))

(when (= __name__ "__main__")
  (asyncio.run (main)))
```

`:async` 也可加在 `fn`（產生 async lambda）上。在 async 函數內可正常使用 `await`、`async-for`（寫法為 `(for :async [...] ...)`）、`async-with`（`(with :async [...] ...)`）。

> ✅ 實測：`(defn :async hello [] (await (asyncio.sleep 0)) (print "async-ok"))` 經 `asyncio.run` 印出 `async-ok`。

## 2. 生成器 (Generators)

`yield` 一個值用法不變。要對應 Python 的 `yield from`，寫成 `(yield :from coll)`：

```hylang
(defn count-up [n]
  (setv i 0)
  (while (< i n)
    (yield i)
    (setv i (+ i 1))))

(for [x (count-up 3)]
  (print x))   ; ✅ 印出 0, 1, 2

;; yield from
(defn flatten-two-lists [a b]
  (yield :from a)
  (yield :from b))

(print (list (flatten-two-lists [1 2] [3 4])))   ; ✅ → [1, 2, 3, 4]
```

## 3. 裝飾器 (Decorators)

Hy 1.x **沒有** `with-decorator`。裝飾器寫在 `defn` 名稱之前的方括號內（規則來源：`projects/hy/hy/core/result_macros.py:1618`）：

```hylang
(defn my-decorator [func]
  (defn wrapper [#* args #** kwargs]
    (print "函數執行前")
    (setv result (func #* args #** kwargs))
    (print "函數執行後")
    result)
  wrapper)

;; 一個裝飾器
(defn [my-decorator] say-hi []
  (print "嗨！"))

;; 多個裝飾器（由下而上套用，與 Python 規則一致）
(defn [staticmethod my-decorator] static-hi []
  (print "靜態方法的嗨！"))

(say-hi)
```

> ✅ 實測：`(defn [deco] say-hi [] (print "hi"))` 印出 `before / hi / after`。

## 4. 上下文管理器 (Context Managers)

定義自訂 context manager 與 Python 一致，用 `contextlib.contextmanager` 當裝飾器：

```hylang
(import contextlib [contextmanager])

(defn [contextmanager] temp-setup []
  (print "設置中...")
  (yield "資源")
  (print "清理中..."))

(with [res (temp-setup)]
  (print f"正在使用 {res}"))
```

使用 `with`：

```hylang
(with [f (open "data.txt")]
  (print (.read f)))

;; 多個資源
(with [a (open "in.txt") b (open "out.txt" "w")]
  (.write b (.read a)))

;; async-with
(with :async [conn (acquire)]
  (await (use conn)))
```
