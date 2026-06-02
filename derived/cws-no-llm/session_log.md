# Session Log — cws-no-llm

**起始時間**: 2026-06-01
**Agent**: Claude Code (Sonnet 4.6)
**源專案**: cultivation-world-simulator (analysis/cultivation-world-simulator/)
**衍生目標**: 將 CWS 的 LLM 智能層完整替換為本地規則 AI + 詞庫組合文字，使遊戲在零網路/零 API 環境下可完整運行

---

- 2026-06-01：建立衍生專案目錄結構（derived/cws-no-llm/）
- 2026-06-01：撰寫 PROJECT.md（目標、技術棧、完成定義）
- 2026-06-01：撰寫 docs/design_overview.md（完整設計計畫，含 5 階段與各子系統方案）
- 2026-06-02：核對原始碼確認全部 14 個 task 的實際返回格式（發現 action_decision/relation_resolver/story_teller/sect_decider/sect_thinker 格式與設計文件假設不符）
- 2026-06-02：建立 derived/cws-no-llm/src/local_ai/__init__.py 與 dispatcher.py（Phase 0 全任務 stub）
- 2026-06-02：複製 local_ai 模組到 projects/cultivation-world-simulator/src/local_ai/
- 2026-06-02：打 shim 至 projects/cultivation-world-simulator/src/utils/llm/client.py（call_llm_with_task_name 函數）
- 2026-06-02：更新 docs/task_interface_spec.md（填入原始碼核對的實際格式，標記 sect_random_event 不走 dispatcher）
- 2026-06-02：修正 dispatcher action_decision stub — action_name 需大寫 PascalCase 且從 general_action_infos 選可用動作（Respire > Meditate > Retreat > Rest）
- 2026-06-02：patch sect_random_event.py 的 _generate_reason_fragment() 加 local AI shim，返回 stub reason fragment 跳過 LLM
- 2026-06-02：patch autonomous_custom_content_service.py 的 should_trigger() 在本地 AI 模式下返回 False
- 2026-06-02：實機驗證 Phase 0：102→107 年模擬無崩潰、零 ERROR、零非法動作警告（9 個角色存活）
- 2026-06-02：Phase 1 — 建立 decision.py（softmax 效用 AI）、goals.py（目標模板生成）、relations.py（relation_delta 公式引擎）
- 2026-06-02：Phase 1 實機驗證：103→108 年 17 月模擬無崩潰，10 個角色存活，動作多樣化（Respire/Retreat/Plant）
- 2026-06-02：Phase 2 — 建立 narrative.py（story_teller 詞庫組合、interaction_feedback 動作分類回應、backstory 五段模板）
- 2026-06-02：Phase 2 — 建立 epithets.py（nickname 前綴+主題+後綴詞庫，5% 稀有特殊外號，境界感知前綴池）
- 2026-06-02：Phase 2 單元驗證：story/backstory 結構正確，nickname 10 次全唯一，部署至 projects/cultivation-world-simulator/src/local_ai/
