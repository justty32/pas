# 工業工程 (Industrial Engineering)：我到底在學啥？

> 工業工程與作業研究 (IEOR) 是研究「系統優化」的學科。它不像傳統工程學專注於機器或材料，而是專注於如何設計、改進並實施複雜的系統（包含人、機器、資金、資訊與能源），以達到最高的效率與品質。

## 1. 領域定位（與鄰近領域 the 差異）

工業工程（IE）常與管理學、統計學、資工重疊，其核心差異如下：

| 領域 | 核心目標 | 關鍵對象 | 典型技術 |
|---|---|---|---|
| **工業工程** | 系統效率與優化 | **供應鏈、生產線、服務流程** | **作業研究、機率模型、人因工程** |
| **管理學** | 組織領導與決策 | 團隊、品牌、市場戰略 | 行為科學、財務分析 |
| **統計學** | 數據建模與預測 | 樣本、母體、變數 | 推論統計、實驗設計 (DOE) |
| **資訊工程** | 資料運算與自動化 | 軟體、演算法、網路 | 程式設計、數據庫、人工智慧 |

**補充**：工業工程師常被稱為「工程師中的管理師」，他們用嚴謹的數學與工程工具來解決管理上的效率問題。

## 2. 高中銜接（極簡）

你需要在高中階段打好以下基礎：
- **數學**：機率與統計（IE 的靈魂）、排列組合、線性方程組。
- **邏輯**：演算法思維、流程圖分析。
- **社會科學**：對組織運作、經濟與效率的基本理解。

## 3. 大學階段：核心課程（主菜）

### 3.1 四年課程地圖總覽

以 **Georgia Tech (ISyE)**、**Purdue** 為主要參考，結合 **國立清華大學 (NTHU)** 的課程架構：

| 學年 | 核心課程類型 | 關鍵科目 (必修) | 學分參考 (以 NTHU 為例) |
|---|---|---|---|
| **大一** | 工具與科學基礎 | 微積分、線性代數、計算機程式、普通物理 | 各 3-4 學分 |
| **大二** | **數學與分析**基礎 | **工程統計學**、**作業研究 (一) 決定論** | 各 3 學分 |
| **大三** | **系統與機率**核心 | **作業研究 (二) 隨機模型**、**供應鏈管理**、人因工程 | 各 3 學分 |
| **大四** | 整合實作與品質 | **製造系統**、**品質管制**、畢業專題 (Capstone) | 3-6 學分 |

### 3.2 大二：優化的起點

#### 作業研究 I - 決定論 (Operations Research I: Deterministic Models)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大二下
- **在學什麼**：研究如何用線性規劃 (LP)、整數規劃 (IP) 來找最佳解。
- **解決什麼問題**：工廠有 10 種機器與 100 種零件，如何排程才能在有限時間內獲得最大產值？
- **典型題目**：使用單體法 (Simplex Method) 求解一個含有 3 個決策變數與 2 個約束條件的極大化獲利問題。
- **聖經教科書**：Hillier & Lieberman, *Introduction to Operations Research*。

#### 工程統計學 (Engineering Statistics)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大二
- **在學什麼**：研究數據的分佈、推論與實驗設計 (DOE)。
- **解決什麼問題**：生產線換了新員工後，良率真的有顯著下降嗎？還是隻是隨機誤差？
- **典型題目**：已知產品直徑服從常態分佈 $N(10, 0.5^2)$，計算抽樣 50 個樣本中，平均值超過 10.2 的機率（P-value）。
- **聖經教科書**：Montgomery, *Applied Statistics and Probability for Engineers*。

### 3.3 大三：隨機性與複雜系統

#### 作業研究 II - 隨機模型 (Operations Research II: Stochastic Models)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三上
- **在學什麼**：研究含不確定性的系統，包含馬可夫鏈 (Markov Chains) 與排隊理論 (Queueing Theory)。
- **解決什麼問題**：銀行的櫃檯要開幾個，才能讓客戶平均等待時間少於 5 分鐘，同時不浪費人力？
- **典型題目**：一個 M/M/1 排隊系統，到達率 $\lambda=8$ 人/時，服務率 $\mu=10$ 人/時，求系統中平均人數與客戶平均等待時間。
- **聖經教科書**：Sheldon Ross, *Introduction to Probability Models*。

#### 供應鏈管理 (Supply Chain Management)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三
- **在學什麼**：研究從原料採購、生產、倉儲到配送的物流網絡優化。
- **解決什麼問題**：如何減少「長鞭效應」(Bullwhip Effect)？存貨應該放多少才能平衡缺貨風險與倉儲成本？
- **典型題目**：利用 EOQ (Economic Order Quantity) 模型計算在年需求量 10,000 件、訂購成本 $50、持有成本 $2 下的最佳訂購量。
- **聖經教科書**：Chopra & Meindl, *Supply Chain Management*。

### 3.4 跨年級工具
- **軟體**：Gurobi/CPLEX (優化求解器)、AnyLogic/Arena (離散事件模擬)、Minitab/R/Python (統計分析)。

## 4. 研究所階段（簡述）

常見的分組方向：
1. **作業研究組**：深入離散優化、非線性規劃、博弈論。
2. **數據科學與分析組**：預測模型、工業大數據、機器學習應用。
3. **健康系統工程**：優化醫院排班、急診流程、資源配置。
4. **金融工程**：風險管理、投資組合理論。

## 5. 博士前沿研究（最多 3 個）

### 5.1 韌性供應鏈與全球性風險 (Resilient Supply Chains)
- **為什麼最近熱？**：後疫情時代與地緣政治波動。研究如何建立在地震、戰爭或貿易衝突下仍能快速恢復的供應鏈網絡。
- **卡在什麼問題？**：效率 (Cost) 與韌性 (Resilience) 的權衡極難量化；多階層供應鏈的資訊透明度不足。

### 5.2 協作機器人與人機交互 (Human-Robot Collaboration)
- **為什麼最近熱？**：智慧工廠不再追求全自動化，而是人與機器共事。研究如何設計機器人行為，使其符合人類心理與安全需求，提升整體協作效率。
- **卡在什麼問題？**：人類行為的隨機性極高，難以建立精確的模型供機器人即時預測與反應。

### 5.3 大規模隨機優化與強化學習 (RL for Large-scale Optimization)
- **為什麼最近熱？**：當系統變數達到百萬級別時，傳統數學規劃太慢。研究如何結合深度強化學習 (Deep RL) 來快速找到接近最優的動ative 決策。
- **卡在什麼問題？**：強化學習模型的「可解釋性」與「穩定性」在嚴謹的工業生產環境中仍面臨挑戰。

## 6. 資料來源

### 國際大學系所課程地圖
- **Georgia Tech ISyE Undergraduate**: [https://www.isye.gatech.edu/academics/undergraduate/degrees/bs-industrial-engineering](https://www.isye.gatech.edu/academics/undergraduate/degrees/bs-industrial-engineering)
- **Purdue IE Undergraduate Curriculum**: [https://engineering.purdue.edu/IE/academics/undergraduate/curriculum](https://engineering.purdue.edu/IE/academics/undergraduate/curriculum)
- **University of Michigan IOE**: [https://ioe.engin.umich.edu/academics/undergraduate/](https://ioe.engin.umich.edu/academics/undergraduate/)
- **清華大學工業工程與工程管理學系**: [https://ie.site.nthu.edu.tw/](https://ie.site.nthu.edu.tw/)

### 教科書與參考資料
- Hillier & Lieberman (McGraw-Hill), Sheldon Ross (Elsevier), Montgomery (Wiley).
