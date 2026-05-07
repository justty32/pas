# 材料工程 (Materials Science and Engineering)：我到底在學啥？

> 材料工程是研究「結構-製程-性質-效能」(The Materials Science and Engineering Tetrahedron) 四者關係的學科。工程師透過操縱原子結構與製程，創造出具有特定性能（如超導、高強、生物相容）的新材料。

## 1. 領域定位（與鄰近領域的差異）

材料工程（MSE）是介於基礎科學（物理、化學）與其他工程（機械、電機、航太）之間的橋樑：

| 領域 | 核心目標 | 關鍵對象 | 典型技術 |
|---|---|---|---|
| **材料工程** | 調控物質微結構以達性能要求 | **金屬、陶瓷、半導體、聚合物** | **晶體結構、相圖、微組織分析** |
| **物理學** | 研究物質的基本運作原理 | 電子、量子能階、凝態物理 | 固態物理、量子力學模型 |
| **化學** | 研究分子的合成與反應 | 化學鍵、有機/無機化合物 | 分子合成、化學反應動力學 |
| **機械工程** | 結構應用與宏觀受力 | 零件、機器、載具 | 有限元素分析 (FEA)、機械加工 |

**補充**：機械工程師通常問：「這根樑受力多少會斷？」而材料工程師會問：「為什麼這種鋼材在低溫下會脆斷？我該如何改變其微結構來防止斷裂？」

## 2. 高中銜接（極簡）

你需要在高中階段打好以下基礎：
- **化學**：元素週期表、原子結構、化學鍵（離子、共價、金屬鍵）、熱化學。
- **物理**：固體與液體的基本性質、熱學基礎、近代物理初步（能階概念）。
- **數學**：幾何與向量（理解晶格結構的關鍵）、基本的微分運算。

## 3. 大學階段：核心課程（主菜）

### 3.1 四年課程地圖總覽

以 **MIT (Course 3)**、**Northwestern** 與 **Stanford** 為主要參考，結合 **國立台灣大學 (NTU)** 的課程架構：

| 學年 | 核心課程類型 | 關鍵科目 (必修) | 學分參考 (以 NTU 為例) |
|---|---|---|---|
| **大一** | 科學基礎 | 微積分、普通物理、普通化學、**材料科學導論** | 各 3-4 學分 |
| **大二** | **結構與熱力學** | **晶體學/繞射**、**材料熱力學**、**材料物理** | 各 3 學分 |
| **大三** | **變遷與機械性質** | **相變/動力學**、**材料機械性質**、電子性質 | 各 3 學分 |
| **大四** | 整合實作與設計 | **材料實驗**、**材料選用與設計**、專題研究 | 3-6 學分 |

### 3.2 大二：結構與能量的本質

#### 晶體學與 X 光繞射 (Crystallography and X-ray Diffraction)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大二上
- **在學什麼**：研究原子在空間中的排列方式（Bravais Lattices），以及如何利用 X 光（Bragg's Law）來測量這些結構。
- **解決什麼問題**：如何判定一種新發現的合金是 FCC 還是 BCC 結構？其晶格常數是多少？這直接影響材料的強度與導電性。
- **典型題目**：給定一組鋁 (Al, FCC 結構) 的 X 光繞射數據與波長 $\lambda$，請計算其 (111) 面與 (200) 面的繞射角 $2\theta$。
- **聖经教科書**：Cullity, *Elements of X-Ray Diffraction*。

#### 材料熱力學 (Thermodynamics of Materials)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大二下
- **在學什麼**：研究材料在熱平衡下的狀態，重點在於吉布斯自由能 (Gibbs Free Energy) 與相圖 (Phase Diagrams)。
- **解決什麼問題**：在高溫下，哪種合金相是最穩定的？合金中加入特定元素會提高還是降低熔點？
- **典型題目**：已知 A-B 二元合金在 1000K 時的混合焓與混合熵，利用共切線法 (Common Tangent Construction) 求出共存之 $\alpha$ 相與 $\beta$ 相的成分。
- **聖經教科書**：Gaskell, *Introduction to the Thermodynamics of Materials* 或 DeHoff。

### 3.3 大三：微結構演化與性能

#### 相變與動力學 (Phase Transformations and Kinetics)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三上
- **先修**：材料熱力學
- **在學什麼**：熱力學告訴我們「終點」在哪，動力學告訴我們「多快」能到達。研究擴散 (Diffusion)、成核與長大。
- **解決什麼問題**：鋼鐵淬火後為什麼會變硬（麻田散鐵相變）？如何控制熱處理時間來得到最細緻的晶粒？
- **典型題目**：利用 Fick's Second Law，計算鋼件在 900°C 滲碳 10 小時後，表面下 1mm 處的碳濃度分佈。
- **聖經教科書**：Porter, Easterling, & Sherif, *Phase Transformations in Metals and Alloys*。

#### 材料機械性質 (Mechanical Behavior of Materials)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三
- **在學什麼**：從微觀尺度研究位錯 (Dislocations) 運動如何導致宏觀的塑性變形。
- **解決什麼問題**：為什麼在金屬中加入雜質反而能提高強度（固溶強化）？如何預測材料在循環載荷下的疲勞壽命？
- **典型題目**：給定一個單晶金屬的受力方向與滑移系統，利用施密特法則 (Schmid's Law) 計算臨界剪應力。
- **聖經教科書**：Courtney, *Mechanical Behavior of Materials*。

### 3.4 跨年級工具
- **表徵儀器**：掃描式電子顯微鏡 (SEM)、透射式電子顯微鏡 (TEM)、原子力顯微鏡 (AFM)。
- **軟體**：Thermo-Calc (相圖計算)、VASP/Gaussian (量子力學模擬)、ImageJ (組織定量分析)。

## 4. 研究所階段（簡述）

常見的分組方向：
1. **半導體材料**：寬能隙半導體、光電材料。
2. **能源材料**：鋰電池、燃料電池、熱電材料。
3. **生醫材料**：人工關節、藥物釋放載體、生物相容性支架。
4. **計算材料科學**：密度泛函理論 (DFT)、分子動力學模擬 (MD)。

## 5. 博士前沿研究（最多 3 個）

### 5.1 高熵合金 (High-Entropy Alloys, HEAs)
- **為什麼最近熱？**：傳統合金以一種元素為主，HEAs 由 5 種以上等量元素組成，展現出驚人的耐高溫、高強度與耐蝕性，被視為航太與極地設備的希望。
- **卡在什麼問題？**：成分空間近乎無限，單靠實驗尋找最佳配比效率極低，必須仰賴機器學習預測。
- **代表人物**：葉均蔚教授 (台灣學者，HEAs 之父)。

### 5.2 原子層沉積與二維材料 (ALD & 2D Materials)
- **為什麼最近熱？**：在半導體製程中，我們需要一層只有幾個原子厚、卻極度均勻的薄膜。石墨烯與過渡金屬硫屬化物 (TMDs) 展現了超越傳統矽的電子特性。
- **卡在什麼問題？**：大面積高品質薄膜的生長控制，以及如何將二維材料整合進現有的矽製程產線中。
- **代表團隊**：Rice University 的 James Tour 實驗室。

### 5.3 材料基因組計畫 (Materials Genome Initiative)
- **为什么最近熱？**：模仿人類基因組，透過高通量實驗與數據計算，將研發新材料的時間從 20 年縮短到 5 年內。
- **卡在什麼問題？**：建立跨研究室的標準化數據平台極其困難，且計算模型在預測複雜系統（如陶瓷在高溫下的疲勞）時仍不夠精確。

## 6. 資料來源

### 國際大學系所課程地圖
- **MIT Course 3 DMSE**: [https://dmse.mit.edu/undergraduate/curriculum](https://dmse.mit.edu/undergraduate/curriculum)
- **Northwestern MSE Curriculum**: [https://www.matsci.northwestern.edu/undergraduate/index.html](https://www.matsci.northwestern.edu/undergraduate/index.html)
- **Stanford MATSCI Program**: [https://matsci.stanford.edu/academics/undergraduate](https://matsci.stanford.edu/academics/undergraduate)
- **台大材料系課程介紹**: [https://www.mse.ntu.edu.tw/](https://www.mse.ntu.edu.tw/)

### 教科書與參考資料
- Callister & Rethwisch (Wiley), Gaskell (CRC Press), Cullity (Pearson).
