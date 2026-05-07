# 電機工程 (Electrical Engineering)：我到底在學啥？

> 電機工程是研究「電能的產生與傳輸」以及「資訊的電子化處理」的學科。從微小的晶片訊號到跨越國境的高壓電網，都是電機工程的範疇。

## 1. 領域定位（與鄰近領域的差異）

電機工程（EE）常與資工（CS）、物理、機械工程重疊，其核心差異如下：

| 領域 | 核心目標 | 關鍵對象 | 典型技術 |
|---|---|---|---|
| **電機工程** | 電能與訊號的處理 | **電路、半導體、電磁波** | **電路分析、類比/數位電子、通訊原理** |
| **資工 (CS)** | 資訊的運算與演算法 | 軟體、資料結構、作業系統 | 程式設計、人工智慧、軟體架構 |
| **物理學** | 探索自然基本規律 | 原子、場、基本粒子 | 量子力學、相對論、實驗觀測 |
| **機械工程** | 能量與力的轉換 | 機構、引擎、馬達 | 三大力學、熱力學、製造技術 |

**補充**：電機系位於「物理」與「軟體」之間。我們利用物理現象（電磁感應、半導體特性）來建造硬體，並為軟體提供運算的基礎平台。

## 2. 高中銜接（極簡）

你需要在高中階段打好以下基礎：
- **數學**：微積分（電機系的語言）、複數（描述交流電訊號的必備工具）。
- **物理**：電學（庫倫定律、電路基本概念）、磁學（法拉第定律）、波動與光學。

## 3. 大學課綱（主菜）

### 3.1 四年課程地圖總覽

以 **MIT (Course 6-2)** 與 **Stanford** 為主要參考，結合 **國立台灣大學 (NTU)** 的課程架構：

| 學年 | 核心課程類型 | 關鍵科目 (必修) | 學分參考 (以 NTU 為例) |
|---|---|---|---|
| **大一** | 基礎工具與地基 | 微積分、普通物理、計算機程式、線性代數 | 各 3-4 學分 |
| **大二** | **電子與電路**基礎 | **電路學**、**電子學 (一)**、**工程數學 (複變/微分方程)** | 各 3 學分 |
| **大三** | 系統與場論核心 | **電子學 (二)**、**信號與系統**、**電磁學**、自動控制 | 各 3 學分 |
| **大四** | 專業選修與專題 | 數位系統、通訊原理、**實務專題 (Capstone)** | 3-6 學分 |

### 3.2 大一：打地基

#### 線性代數 (Linear Algebra)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大一
- **先修**：無
- **在學什麼**：研究矩陣運算、向量空間。
- **解決什麼問題**：電機工程中幾乎所有問題（如電路網分析、影音壓縮、AI 運算）最後都會化簡成超大型矩陣運算。
- **典型題目**：給定一個 $3 \times 3$ 矩陣，求其特徵值 (Eigenvalues) 與特徵向量 (Eigenvectors)，並說明該矩陣是否可對角化。
- **聖經教科書**：Gilbert Strang, *Introduction to Linear Algebra*。

### 3.3 大二：核心基礎（電機系的敲門磚）

#### 電路學 (Circuits)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大二上
- **先修**：普通物理
- **在學什麼**：學習集總電路模型 (Lumped Model)。掌握 KVL、KCL、戴維寧等效電路、相量 (Phasor) 分析。
- **解決什麼問題**：這是所有電機問題的起點。無論是一個手機充電器還是電腦主機板，你都必須先算出電流與電壓的分佈。
- **典型題目**：給定一個含有電壓源、電阻與電感的交流電路，請計算負載端所能獲得的最大功率輸出。
- **聖經教科書**：Hayt et al., *Engineering Circuit Analysis*。

#### 電子學 (Electronics)
- **必/選修**：必修
- **學分**：3+3 (通常分兩學期)
- **通常開在**：大二下、大三上
- **先修**：電路學
- **在學什麼**：研究半導體元件（二極體、BJT、MOSFET）。學習如何用這些元件做成放大器 (Amplifier) 或開關。
- **解決什麼問題**：手機收訊弱時需要放大訊號、電腦需要開關來處理 0 與 1。這門課教你如何設計這些硬體。
- **典型題目**：設計一個共源極 (Common-Source) MOSFET 放大器，已知 $V_{DD} = 5\text{ V}$，$I_D = 1\text{ mA}$，計算所需的偏壓電阻值以達到 $20\text{ dB}$ 的電壓增益。
- **聖經教科書**：Sedra & Smith, *Microelectronic Circuits*。

### 3.4 大三：系統與物理場

#### 信號與系統 (Signals and Systems)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三上
- **先修**：工程數學
- **在學什麼**：研究訊號在頻域 (Frequency Domain) 的行為。學習傅立葉轉換 (Fourier)、拉普拉斯轉換 (Laplace)。
- **解決什麼問題**：這是通訊、影像處理、控制系統的共通理論基礎。例如：如何將你的聲音壓縮成 MP3，或者如何設計一個穩定且不晃動的無人機控制系統。
- **典型題目**：已知一個線性非時變系統 (LTI System) 的脈衝響應 $h(t) = e^{-3t}u(t)$，請利用卷積 (Convolution) 計算當輸入訊號為階梯函數時的輸出響應。
- **聖經教科書**：Oppenheim, *Signals and Systems*。

#### 電磁學 (Electromagnetics)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三上
- **先修**：工數、普物
- **在學什麼**：研究電荷、電流與電磁場的相互作用。學習麥克斯韋方程組 (Maxwell's Equations)。
- **解決什麼問題**：研究無線通訊（手機天線）、馬達轉動、變壓器原理。當電路頻率極高時，傳統電路學會失效，必須靠電磁學才能解釋。
- **典型題目**：利用安培定律計算一個具有無限長度的同軸電纜在不同半徑處的磁場強度分佈。
- **聖經教科書**：Ulaby, *Fundamentals of Applied Electromagnetics*；Griffiths, *Introduction to Electrodynamics*。

### 3.5 大四：專業選修與整合

#### 數位系統設計 / VLSI
- **通常做什麼**：學習使用硬體描述語言 (Verilog/VHDL) 來設計晶片。這是在台灣電機系非常熱門的分組（IC 設計）。
- **實務專題 (Capstone)**：例如設計一個「具有人臉辨識功能的自動追蹤相機系統」，整合電路、訊號處理、控制與程式設計。

### 3.6 跨年級工具課
- **軟體**：MATLAB（數學運算、通訊模擬）、LTspice/PSpice（電路模擬）、Verilog/SystemVerilog（晶片設計）。
- **硬體**：示波器、訊號產生器、三用電表、FPGA 開發版。

### 3.7 公認教科書清單
1. **電子學聖經**：Sedra & Smith, *Microelectronic Circuits*。
2. **訊號經典**：Oppenheim, *Signals and Systems*。
3. **電路基礎**：Agarwal & Lang, *Foundations of Analog and Digital Electronic Circuits*。

## 4. 研究所階段（簡述）

電機系在研究所的分流極細：
1. **電子/積體電路組 (ICS)**：設計 CPU、記憶體、通訊晶片（台灣最賺錢的組別）。
2. **光電組 (Photonics)**：研究雷射、太陽能電池、光纖通訊。
3. **通訊組 (Comm)**：研究 5G/6G 演算法、錯誤更正碼。
4. **電力組 (Power)**：研究智慧電網、電動車電機。
5. **控制組 (Control)**：研究機器人、工業自動化。

## 5. 博士前沿研究（最多 3 個）

### 5.1 量子計算硬體 (Quantum Computing Hardware)
- **為什麼最近熱？**：傳統晶片的製程已逼近物理極限。量子位元能提供指數級的運算增長，是未來超級電腦的關鍵。
- **卡在什麼問題？**：量子位元極度不穩定（退相干問題），需要在接近絕對零度（數 mK）的低溫下工作，且極難擴大規模。
- **代表團隊**：Google Quantum AI 團隊、IBM Research、MIT 的 Will Oliver。

### 5.2 神經形態運算 (Neuromorphic Computing)
- **為什麼最近熱？**：目前的 AI 運算極度耗電。仿生晶片模擬大腦神經元，只在「有訊號」時耗電（Spiking Neural Networks），能讓 AI 在手機端甚至手錶端高效運行。
- **卡在什麼問題？**：硬體架構與目前的馮紐曼架構完全不同，缺乏成熟的編譯器與軟體生態系統。
- **代表團隊/晶片**：Intel 的 Loihi 晶片、ETH Zurich 的 Giacomo Indiveri。

### 5.3 寬能隙半導體 (Wide Bandgap Semiconductors, GaN/SiC)
- **為什麼最近熱？**：電動車與快充系統需要處理極高電壓與溫度。GaN（氮化鎵）與 SiC（碳化矽）比傳統矽晶片更耐壓、體積更小。
- **卡在什麼問題？**：材料生產成本依然偏高，且大尺寸晶圓的良率仍待提升。
- **代表公司**：Tesla (首家大規模採用 SiC 的車廠)、TSMC。

## 6. 資料來源

### 國際大學系所課程地圖
- **MIT EECS Undergraduate Curriculum**: [https://www.eecs.mit.edu/academics/undergraduate-programs/curriculum/](https://www.eecs.mit.edu/academics/undergraduate-programs/curriculum/)
- **Stanford EE Degree Requirements**: [https://ee.stanford.edu/academics/undergraduate/degree-requirements](https://ee.stanford.edu/academics/undergraduate/degree-requirements)
- **ETH Zurich BSc EEIT**: [https://ee.ethz.ch/studies/bachelor.html](https://ee.ethz.ch/studies/bachelor.html)
- **台大電機系修業地圖**: [https://web.ee.ntu.edu.tw/](https://web.ee.ntu.edu.tw/)

### 教科書與參考資料
- Sedra/Smith (Oxford Press), Oppenheim (Pearson).
- MIT OpenCourseWare (6.002, 6.003).
