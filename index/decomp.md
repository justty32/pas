# 反組譯 / 反編譯分析

> [← 回總索引 index.md](../index.md)。本檔收錄逐位元組/反組譯/反編譯導向的逆向專案。

| 專案名稱 | 類型 | 分析深度 | 狀態 | 核心內容摘要 |
| :--- | :--- | :--- | :--- | :--- |
| **Airships: CtS** | 飛行戰艦策略遊戲 (Java) | 高 (Level 1-3, C++重寫導向) | 分析中 | CFR 反編譯 game.jar→`projects/airships-cts/src/`（691 .java）；6 份子系統分析＋C++ 重寫路線圖。核心：確定性鎖步多人、Loadable 資料系統(71 型別)、雙層戰術 Combat/戰略 Campaign、評分式 AI、2D 法線光照渲染。 |
| **mh1j** | PS2 遊戲反組譯 (MIPS/C) | Level 1 | 分析中 | Monster Hunter 1 日版 (SLPM_654.95) 逐位元組匹配反組譯，MetroWerks 編譯器 + splat 拆分，主 ELF + 6 個 Overlay (含 DNAS 加密)。 |
| **pokeemerald** | GBA 遊戲反組譯 (C/ARM) | Level 1-2 | 分析中 | 寶可夢 Emerald pret 反組譯，雙Callback主迴圈、Task協程系統、Script bytecode直譯器、CB2狀態機戰鬥、多Controller架構、AI評分腳本、BoxPokemon XOR加密。 |
