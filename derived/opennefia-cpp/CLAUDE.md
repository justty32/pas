# CLAUDE.md — opennefia-cpp（衍生專案 agent 指導）

## 這是什麼

用 C++20 重寫 OpenNefia 引擎**核心**的衍生小專案，架構藍本＝使用者自有的 `medps`。**本階段只做 godot-free 純 C++ 核心，不碰前端 / Godot。** 完整背景見 `PROJECT.md`。

## 鐵則

1. **輸出與留檔一律繁體中文。**
2. **程式碼必附位置** `path:line`；引用源專案時附其完整路徑（如 `C:/code/mine/medps/src/gcore/zone_io.h:14`）。
3. **核心 godot-free**：`opennefia_core` 目標**不得** include 任何前端 / 圖形 / godot 標頭。前端綁定未來另開目標（仿 medps `gbind/`）。
4. **不靠反射**：序列化用 `entt::type_list` + fold；系統用自由函式 + 明確註冊；不模擬 C# 反射。
5. **每次操作後** append 一句話到 `session_log.md`；重大里程碑更新 `PROJECT.md` 進度區。
6. **設計決策**記 `docs/decisions/`，附追溯連結（借鑒自哪份分析）。
7. **圖表用 Mermaid**，禁止 ASCII art 框線圖。
8. 收到「我要退出了」→ 在 `session_temp/session_resume.md` 建進度快照。

## 構建（規劃，Phase 0 後生效）

```powershell
cmake -S . -B build
cmake --build build
```
- 目標：`opennefia_core`（STATIC，純 C++）＋未來 `opennefia_gd`（GDExtension，暫緩）。
- 仿 medps `CMakeLists.txt`：`GLOB_RECURSE` 排除未來的 `/gbind/`；godot-cpp 在 `C:/code/mine/pas/projects/godot-cpp`（前端階段才用）。

## 參照地圖

- 藍本源碼：`C:/code/mine/medps/src/gcore/`
- medps 分析：`../../analysis/medps/architecture/`
- OpenNefia 分析：`../../analysis/OpenNefia/architecture/`
- 設計文件：`docs/`
</content>
