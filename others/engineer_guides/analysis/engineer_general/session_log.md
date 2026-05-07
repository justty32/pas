# 執行日誌 (Session Log) - engineer_general

## 2026-05-07
- 初始化工程領域入門指南研究任務。
- 搜尋土木、機械、電機、化工、材料、生醫、航太、工業、生化九大領域知識。
- 建立 `analysis/engineer_general/tutorial/` 並產出九份領域入門指南（包含簡介與分級列表）。
- 指南涵蓋：高中、大學、碩士、博士四階段。
- 開始「逐一深化」計畫：完成「土木工程」與「機械工程」的深度剖析文件 (`details/` 目錄)。
- 完成「電機工程」深度剖析文件，涵蓋電路、電子、電磁三大核心及 IC 設計與前瞻技術。
- 完成「化學工程」深度剖析文件，詳細探討「三傳一反」核心理論與程序模擬實務。
- 完成「材料工程」深度剖析文件，強調「材料四面體」架構與計算材料科學之前瞻性。
- 完成「生物醫學工程」深度剖析文件，剖析生醫訊號、材料相容性及前沿的腦機介面技術。
- 完成「航太工程」深度剖析文件，涵蓋空氣動力學、推進系統及極超音速等前沿探索。
- 完成「工業工程」深度剖析文件，強調作業研究、精實生產及全球供應鏈優化。
- 完成「生物化學工程」深度剖析文件，剖析生物反應器設計、下游純化及代謝工程。
- **[任務達成]** 已完成九大工程領域的分級指南列表與深度剖析文件。
- 使用者反映舊版（Gemini 產出）過淺、無來源、無分年級、無典型題目；委由 Claude 規劃重做指令書。
- 建立 `gemini_directive.md`：給 Gemini 的工作 SOP，主軸放在大學課綱（70%）、博士前沿降為點綴（10%），強制「3 問題範本」、強制至少 3 所學校來源、強制公認教科書、強制典型題目、附品質檢查清單與反例。
- 設計：產出寫至新建 `v2/` 目錄、不覆蓋舊版；建議 Gemini 先做機械工程一份試樣再批量。
- 建立 `gemini_directive_general.md`：通用版指令書（適用工程以外的其他領域）。設計六種領域類型（學科型／證照型／技藝型／知識型／競技型／混合型）與對應證據基準與主菜結構，要求 Gemini 先判類型再動手。
- 使用者追加兩項規則並同步修改兩份指令書：(1) 來源以國際大學/機構為主（MIT/Stanford/ETH/Oxford/Cambridge 等）、台灣資料僅補充；(2) 移除「畢業後做什麼／薪資／職位」等就業向章節，使用者只對知識本身感興趣。
- [v2] 完成生物化學工程 (Biochemical Engineering)，引用學校：UCL/MIT/UC Berkeley/NTU，URL 4 條。內容嚴格遵循 v2 規範，包含「3 問題範本」與典型題目數值實例。
- [v2] 完成機械工程 (Mechanical Engineering)，引用學校：MIT/Stanford/ETH/NTU，URL 4 條。完成標竿示範，大學部篇幅達 80%，涵蓋三大力學典型題目。
- [v2] 完成電機工程 (Electrical Engineering)，引用學校：MIT/Stanford/ETH/NTU，URL 4 條。強化數學工具（線代/複變）與系統理論（訊號/電磁）的連結。
- [v2] 完成化學工程 (Chemical Engineering)，引用學校：MIT/UC Berkeley/ETH/NTU，URL 4 條。重點解析「三傳一反」核心理論與工業規模化生產邏輯。
- [v2] 完成材料工程 (Materials Science and Engineering)，引用学校：MIT/Northwestern/Stanford/NTU，URL 4 條。以「材料四面體」為核心，涵蓋晶體結構分析、熱力學、動力學與機械性質。
- [v2] 完成生物醫學工程 (Biomedical Engineering)，引用學校：JHU/GT/MIT/NTU，URL 4 條。著重於工程方法量化生理系統，涵蓋生醫訊號、生物力學與生醫材料。
- [v2] 完成航太工程 (Aerospace Engineering)，引用學校：MIT/GT/Purdue/Delft，URL 4 條。核心涵蓋空氣動力學、軌道力學與推進系統，強調極端環境下的設計挑戰。
- [v2] 完成工業工程 (Industrial Engineering)，引用學校：GT/Purdue/Michigan/NTHU/UC Berkeley，URL 4 條。著重於系統優化、作業研究與供應鏈管理之數學建模。
- [v2] 補全土木工程 (Civil Engineering)，引用學校：ETH/Delft/MIT/NTU，URL 4 條。涵蓋結構、大地、水利三大核心與智慧監測研究。
- **[任務達成]** 已完成所有九大工程領域的 v2 版深度報告（生化、機械、電機、土木、化工、材料、生醫、航太、工業），全部存放於 `analysis/engineer_general/v2/`。



