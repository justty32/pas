# pokeemerald 分析工作日誌

- **[Level 9 競技大會]** 完成 `architecture/level9_contest_system.md`：5類別×4等級大會架構、ContestPokemon/ContestantStatus/Contest全域資料結構、CalculateAppealMoveImpact評分流程（基礎值→效果函數→Condition加成→Combo組合技→重複懲罰→緊張歸零）、5×5興奮度矩陣（同類+1/衝突-1/中性0）、掌聲表0~4階+溢出閃爍動畫、回合排名Bubble Sort（同分取最佳名次）、下回合順序反轉機制（可被招式效果覆蓋）、最終評分公式（Round1審查分+Round2表演分×2）、平局依Round1→亂數序破平、干擾Jam傳遞與緊張效果、AI評分腳本引擎（moveScores[]）、完整大會流程任務鏈。
