# 給資深 C++ 工程師的 Taisei 引擎入門

作為一名資深 C++ 工程師，您可能會習慣於使用多態（Polymorphism）、RAII 和強大的 STL 容器。在 Taisei 的 C 語言世界中，這些概念被轉換成了高效的 C 模式，我們將在本文中進行映射。

## 1. 從「對象模型」到「實體接口 (Entity Interface)」

Taisei 並不使用虛擬函數表（vtable），而是使用結構體嵌套和函數指針實現了一種輕量級的多態性。

-   **C++ 的類層次結構**：`class Bullet : public Entity`
-   **Taisei 的實體模型**：`src/entity.h` 定義了 `EntityInterface`。實體數據（如 `Projectile`）會嵌套或指向這個接口。
-   **內存管理**：實體通常被分配在對應的池（Pool）中，以減少頻繁 `malloc/free` 造成的碎片化和 Cache Miss。

## 2. 協程 (Coroutines) vs. 狀態機 (State Machines)

在許多引擎中，您會編寫一個狀態機來處理敵人的行為。Taisei 通過 `koishi` 庫實現了**非搶佔式協程**，這讓您可以編寫看似阻塞（Blocking）但實際上是異步（Asynchronous）的代碼。

-   **C++ 模式**：`update(dt)` 函數中根據 `state` 進行 `switch-case`。
-   **Taisei 模式**：使用 `TASK` 宏編寫線性邏輯，通過 `WAIT(n)` 出讓控制權。這與 C++20 的 `co_await` 非常相似，但完全基於 C 宏實現。

## 3. 資源管理與 RAII 的替代方案

Taisei 沒有解構函數。資源管理遵循明確的 `init/shutdown` 或引用計數模式。

-   **RAII**：`std::unique_ptr<Texture> tex = ...`
-   **Taisei**：使用 `ResourceGroup` 管理一組資源的生命週期。當一個關卡（Stage）結束時，整個資源組會被統一釋放。

## 4. 數值與向量運算

Taisei 廣泛使用 C99 的複數類型 (`complex double`, 縮寫為 `cmplx`) 來處理 2D 向量。

-   **優勢**：旋轉、縮放和位移可以直接通過複數乘法完成。
-   **例子**：`dir = cdir(angle)` (獲取單位向量)，`pos += vel * I` (加上垂直方向的位移)。

---

## 接下來的步驟

1.  **環境與構建**：Taisei 使用 **Meson** 作為構建系統。
2.  **核心 DSL**：學習 `TASK`、`INVOKE_TASK` 和 `WAIT`。
3.  **編寫第一個敵人**：實踐如何定義一個敵人的行為。
