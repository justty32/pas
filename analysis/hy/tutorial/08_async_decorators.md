# 非同步、生成器與裝飾器 (08_async_decorators.md)

本章介紹 Hy 如何處理 Python 的現代特性，如 `asyncio` 和裝飾器。

## 1. 非同步編程 (AsyncIO)
Hy 使用 `async-defn` 代替 `defn` 來定義協程，並使用 `await`。

```hylang
(import asyncio)

(async-defn slow-hello []
  (await (asyncio.sleep 1))
  (print "哈囉，非同步！"))

(async-defn main []
  (print "等待中...")
  (await (slow-hello)))

(if (= __name__ "__main__")
    (asyncio.run (main)))
```

## 2. 生成器 (Generators)
在 Hy 中使用 `yield` 和 `yield-from`。

```hylang
(defn count-up [n]
  (setv i 0)
  (while (< i n)
    (yield i)
    (setv i (+ i 1))))

(for [x (count-up 3)]
  (print x)) ; 0, 1, 2
```

## 3. 裝飾器 (Decorators)
Hy 提供 `with-decorator` 宏來應用裝飾器。

```hylang
(defn my-decorator [func]
  (defn wrapper []
    (print "函數執行前")
    (func)
    (print "函數執行後"))
  wrapper)

(with-decorator my-decorator
  (defn say-hi []
    (print "嗨！")))

(say-hi)
```

## 4. 上下文管理器 (Context Managers)
除了 `with`，你也可以定義自己的上下文管理器。

```hylang
(import [contextlib [contextmanager]])

(with-decorator contextmanager
  (defn temp-setup []
    (print "設置中...")
    (yield "資源")
    (print "清理中...")))

(with [res (temp-setup)]
  (print f"正在使用 {res}"))
```
