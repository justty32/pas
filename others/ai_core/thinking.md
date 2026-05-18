> **狀態（2026-05-18）：本文件所有設計點皆已進入 `docs/architectures/`，僅保留為歷史紀錄，不再作為設計來源。**
>
> 對應表：
> - 第 1 行（metadata 與 entrydata 的關係） → `02_protocol.md` §4.7 entrydata 介面宣告（`has_entries` key）
> - 第 2 行（其他 manager 不一定管 entry） → `01_overview.md` §1「Entry-managing vs Simple singleton server」兩種亞型表
> - 第 4–5 行（metadata / server 常用操作抽 python module） → `06_project.md` §10.1 `protocol/` 共用 helper 出口（含 YAGNI 抽取時機）
> - 第 7–9 行（entry 忙線 + time to wait 逾時） → `03_entry_manager.md` §6.4 `time_to_wait_ms`
> - 第 11 行（entry manager、hub 都要 wrapper CLI） → `pyproject.toml` 已列 `ai-core-server` / `ai-core-call` / `ai-core-hub` / `ai-core-hub-server`
> - 第 13 行（agent.md 更詳細） → `07_agents.md`

---

docs/architecture.md中，關於metadata與entrydata的敘述，應該是說，metadata仍然是了解這東西的唯一介面，只是說，可以從metadata中知道，這東西還有一個介面叫做entrydata可以用。
然後其他類似的manager，有時候不一定是管理entry的，他們有可能就是普通的類似MCP伺服器那樣的工具，不需要管理entry。

我能預想到，以後在製作function時，處理那些metadata的常用操作如檢查某個key存不存在之類，可以弄成一個python module方便使用。
server之類也是。

然後關於LLM entry manager這部分，他應該是說，當某個entry正在處理某個請求時，他可能沒空理會其他請求。
這時若其他請求有設置time to wait，那麼可以直接回應他說：超時。
對，這是時間管理，也是重要的一部分。

LLM entry manager, hub記得也都要做一個wrapper cli

agent.md應該要說明的更詳細，講述這個框架的理念、細節。因為就算講了也不會占用太多token(應該吧，或許少講一點，就講精髓就好)。