# 生物化學工程 (Biochemical Engineering)：我到底在學啥？

> 生物化學工程是利用工程學原理（傳質、熱力、動力學），將生物反應從實驗室「燒杯」放大到工業化「工廠」，以生產藥物、疫苗、化學品或能源的學科。

## 1. 領域定位（與鄰近領域的差異）

生物化學工程（Biochemical Engineering）常與化學工程、生物醫學工程混淆，其核心差異如下：

| 領域 | 核心目標 | 處理對象 | 關鍵技術 |
|---|---|---|---|
| **化學工程** | 化學反應的大規模生產 | 純化學物質、石油、塑膠 | 化學反應器、石油煉製 |
| **生物化學工程** | **生物反應**的大規模生產 | 微生物、哺乳動物細胞、酵素 | **發酵、生物反應器、下游純化** |
| **生物醫學工程** | 解決醫學臨床問題 | 人體、醫療器材、組織 | 醫學影像、人工關節、訊號處理 |

**補充**：生化工程可視為「化學工程」與「生物技術」的交叉學科。化學工程師關注如何讓反應發生，而生化工程師關注如何讓「活的細胞」在不理想的工業環境中穩定且高效地產出。

## 2. 高中銜接（極簡）

你需要在高中階段打好以下基礎：
- **數學**：微積分（極限、微分、積分概念）是工程學所有建模的工具。
- **化學**：化學平衡與基礎有機化學（官網通常對分子結構有基本認識）。
- **生物**：細胞構造、代謝（ATP/糖解）與遺傳（DNA/RNA/蛋白質合成）的基本邏輯。

## 3. 大學課綱（主菜）

### 3.1 四年課程地圖總覽

以 **UCL (University College London)** 與 **MIT (Course 10-B)** 為主要參考，結合 **國立台灣大學 (NTU)** 的課程架構：

| 學年 | 核心課程類型 | 關鍵科目 (必修) | 學分參考 (以 NTU 為例) |
|---|---|---|---|
| **大一** | 基礎科學地基 | 微積分、普通物理、普通化學、生物學導論 | 各 3-4 學分 |
| **大二** | 工程科學支柱 | 工程數學、熱力學、流體力學、有機化學 | 各 3 學分 |
| **大三** | 生化工程核心 | **生物反應工程 (Kinetics)**、**傳質與熱傳**、**生物分離 (Downstream)** | 各 3 學分 |
| **大四** | 整合與實作 | **生化廠設計 (Capstone Design)**、生化實驗、專題研究 | 3-6 學分 |

### 3.2 大一：打地基
在大一，生化工程系與化學系或普通生物系差別不大，但會多一門「導論」。

#### 生化工程概論 (Introduction to Biochemical Engineering)
- **必/選修**：必修
- **學分**：2
- **通常開在**：大一上
- **先修**：無
- **在學什麼**：介紹從上游菌株開發到下游產物純化的全流程（Platform Process）。學習「質量平衡」的基本概念。
- **解決什麼問題**：讓學生知道生化工程不只是生物課。例如：要生產一劑疫苗，除了生物學家開發的病毒株，為什麼還需要工程師去計算反應器的體積與泵浦功率？
- **典型題目**：一個發酵罐每小時消耗 100 kg 葡萄糖，若產物乙醇的產率 (Yield) 為 0.51 g/g，求每小時產出的乙醇質量與所需的氧氣量（需利用化學計量式平衡）。
- **聖經教科書**：Shuler & Kargi, *Bioprocess Engineering: Basic Concepts*。

### 3.3 大二：工程科學與分子基礎
此階段開始訓練如何定量描述物理行為。

#### 生化熱力學 (Biochemical Thermodynamics)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大二下
- **先修**：微積分、普通化學
- **在學什麼**：研究能量轉換與化學平衡。特別專注於生物系統（如蛋白質摺疊、細胞膜平衡）。
- **解決什麼問題**：生物反應是否會自發發生？例如：預測在特定 pH 值與溫度下，某種抗體蛋白質是否會變性失效。
- **典型題目**：給定某酵素反應在不同溫度下的平衡常數 K，利用 Van't Hoff 方程計算該反應的標準焓變 ($\Delta H^\circ$)。
- **聖經教科書**：Sandler, *Chemical, Biochemical, and Engineering Thermodynamics*。

### 3.4 大三：核心專業（重頭戲）
這是生化工程的核心，90% 的專業知識集中在此。

#### 生物反應工程 (Bioreaction Engineering / Kinetics)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三上
- **先修**：工程數學、生化熱力學
- **在學什麼**：定量描述細胞生長與產物形成的速率。學習 Monod 方程、酵素動力學 (Michaelis-Menten)。
- **解決什麼問題**：決定「要養多久」以及「什麼時候收割」。若反應器內底物濃度太低，細胞不長；太高可能產生毒性。
- **典型題目**：已知某細菌的 $\mu_{max} = 0.5\text{ h}^{-1}$，$K_s = 1\text{ g/L}$。若初始細菌濃度為 $0.1\text{ g/L}$，要在 $10\text{ 小時}$ 內達到 $10\text{ g/L}$，計算所需的初始底物濃度。
- **聖經教科書**：Bailey & Ollis, *Biochemical Engineering Fundamentals*。

#### 生物分離程序 (Bioseparations / Downstream Processing)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三下
- **先修**：流體力學、傳質傳熱
- **在學什麼**：研究如何從幾萬公升的發酵液（充滿雜質）中，提取出那幾克的高純度藥物。包含過濾、離心、層析 (Chromatography) 與凍乾。
- **解決什麼問題**：生物藥品的成本 80% 來自下游。如果不學這個，你生產的「藥」就是一灘充滿細菌碎片的水。
- **典型題目**：利用管柱層析分離兩種蛋白質，已知其保留時間分別為 $15$ 與 $18$ 分鐘，峰寬為 $1$ 分鐘。計算其解析度 ($R_s$) 並評估是否達到工業要求的 $1.5$。
- **聖經教科書**：Raja Ghosh, *Principles of Bioseparations Engineering*。

#### 傳質與傳熱 (Mass and Heat Transfer)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三上
- **先修**：流體力學
- **在學什麼**：研究物質（尤其是氧氣）與熱量如何在流體中傳遞。
- **解決什麼問題**：大型反應器最常見的死因是「細胞缺氧」。大罐子中心跟邊緣的氧氣濃度不同，工程師必須計算攪拌速度以確保氧氣傳質係數 ($k_La$) 足夠。
- **典型題目**：一萬公升的生物反應器，細胞耗氧速率為 $20\text{ mmol/L/h}$。已知飽和溶氧為 $0.25\text{ mmol/L}$，若要維持溶氧在 20% 以上，計算所需的最低 $k_La$ 值。
- **聖經教科書**：Welty, Rorrer, & Foster, *Fundamentals of Momentum, Heat, and Mass Transfer*。

### 3.5 大四：整合與畢業設計

#### 生化廠設計 (Bioprocess Plant Design / Capstone Project)
- **通常做什麼**：分組完成一個完整的生物工廠設計報告。例如「年產一百萬劑 mRNA 疫苗的工廠設計」。
- **內容包含**：質量與能量衡算、設備規格選用（選多大的泵、多大的罐子）、PID 控制流程圖、以及經濟成本分析（這批藥賣多少錢能回本）。
- **工具**：會使用 ASPEN Plus 或 SuperPro Designer 等軟體進行流程模擬。

### 3.6 跨年級工具課
- **程式語言**：Python 或 MATLAB（用於求解複雜的動力學常微分方程）。
- **CAD 軟體**：AutoCAD（畫工廠配管圖）。
- **實驗課**：通常有三學期的實驗（普通化學、有機化學、生化工程實驗）。

### 3.7 公認教科書清單
1. **入門聖經**：Shuler, Kargi & DeLisa, *Bioprocess Engineering: Basic Concepts* (第 3 版)。
2. **動力學經典**：Bailey & Ollis, *Biochemical Engineering Fundamentals*。
3. **分離技術**：Belter, Cussler & Hu, *Bioseparations: Downstream Processing for Biotechnology*。

## 4. 研究所階段（簡述）

研究所開始分流，常見的方向有：
1. **生技程序組 (Bioprocess Engineering)**：專注於放大生產、製程優化。
2. **生物分子工程 (Biomolecular Engineering)**：專注於蛋白質工程、合成生物學，改造細胞本身的「代工廠」。
3. **藥物製劑與藥動組 (Pharmaceutics)**：研究藥物進入人體後的代謝行為。

## 5. 博士前沿研究（最多 3 個）

### 5.1 代謝工程與合成生物學 (Metabolic Engineering)
- **為什麼最近熱？**：為了實現永續發展，我們想讓細菌產出「原本產不出來」的東西（如飛機燃料、人造蛛絲、高價值抗癌藥物）。
- **卡在什麼問題？**：細胞是活的，當你修改它的代謝路徑時，細胞會產生抗性甚至死亡（代謝負擔問題）。
- **代表團隊**：MIT 的 Gregory Stephanopoulos、Berkeley 的 Jay Keasling。

### 5.2 細胞與基因療法製造 (Cell & Gene Therapy Manufacturing)
- **為什麼最近熱？**：CAR-T 細胞療法能治癒癌症，但一劑要價千萬台幣。關鍵在於無法「大規模、標準化」地在體外擴增病人的免疫細胞。
- **卡在什麼問題？**：從「不鏽鋼大罐子」轉向「一次性生物反應器 (Single-use systems)」的自動化控制，以及如何確保細胞在擴增過程中不失去攻擊癌細胞的能力。
- **代表團隊**：UCL Biochemical Engineering 的 Vax-Hub 團隊。

### 5.3 生化製程數位雙生 (Digital Twins in Bioprocessing)
- **為什麼最近熱？**：生物反應不穩定，傳統「抽樣檢測」太慢。數位雙生利用感測器數據加上 AI，在電腦裡模擬出一模一樣的反應器。
- **卡在什麼問題？**：生物系統是非線性的且充滿噪音，目前的模型還難以完全精準預測細胞的突發行為。
- **代表公司/研究**：Sartorius, Siemens 都在投入相關研發。

## 6. 資料來源

### 國際大學系所課程地圖
- **UCL Biochemical Engineering BEng**: [https://www.ucl.ac.uk/biochemical-engineering/study/undergraduate](https://www.ucl.ac.uk/biochemical-engineering/study/undergraduate)
- **MIT Chemical-Biological Engineering (Course 10-B)**: [https://cheme.mit.edu/undergraduate/curriculum/](https://cheme.mit.edu/undergraduate/curriculum/)
- **UC Berkeley Chemical & Biomolecular Engineering**: [https://chemistry.berkeley.edu/ugrad/degrees/cbe](https://chemistry.berkeley.edu/ugrad/degrees/cbe)
- **國立台灣大學化學工程學系 (生化工程組必修建議)**: [https://www.che.ntu.edu.tw/](https://www.che.ntu.edu.tw/)

### 教科書與參考資料
- Shuler, M. L., & Kargi, F. (2017). *Bioprocess Engineering: Basic Concepts*.
- MIT OpenCourseWare (10.37 Chemical and Biological Reaction Engineering).
- UCL Biochemical Engineering Pilot Plant Resources.
