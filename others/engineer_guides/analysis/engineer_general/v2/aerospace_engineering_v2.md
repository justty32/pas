# 航太工程 (Aerospace Engineering)：我到底在學啥？

> 航太工程是研究大氣層內飛行（航空）與大氣層外飛行（太空）之載具的設計、開發與維護的學科。它是極致性能的追求，涉及流體、結構、推進與控制的深度整合。

## 1. 領域定位（與鄰近領域的差異）

航太工程（AE）常與機械、電機、天文學重疊，其核心差異如下：

| 領域 | 核心目標 | 關鍵對象 | 典型技術 |
|---|---|---|---|
| **航太工程** | 極端環境下的機動與生存 | **飛機、衛星、火箭、無人機** | **空氣動力學、軌道力學、推進系統** |
| **機械工程** | 通用能量與力之轉換 | 車輛、機器人、發動機 | 靜動力學、熱力學、製造技術 |
| **電機工程** | 訊號處理與控制架構 | 航電系統、通信、感測器 | 自動控制、嵌入式系統、雷達 |
| **物理/天文** | 探索自然規律與天體 | 恆星、黑洞、基本粒子 | 廣義相對論、天體物理 |

**補充**：機械工程是航太的基礎。航太工程則是在此基礎上增加了「重量極端限制」與「高速流體力學」的挑戰。在航太界，每減少 1 克的重量都有其經濟價值。

## 2. 高中銜接（極簡）

你需要在高中階段打好以下基礎：
- **數學**：微積分、三角函數、空間幾何。
- **物理**：流體性質、向心力與引力定律、理想氣體、功與能。
- **其他**：對航空模型或天文現象的基本興趣。

## 3. 大學階段：核心課程（主菜）

### 3.1 四年課程地圖總覽

以 **MIT (Course 16)**、**Georgia Tech** 為主要參考，結合 **國立成功大學 (NCKU)** 的課程架構：

| 學年 | 核心課程類型 | 關鍵科目 (必修) | 學分參考 (以 NCKU 為例) |
|---|---|---|---|
| **大一** | 工具與科學基礎 | 微積分、普通物理、普通化學、**航太工程導論** | 各 3-4 學分 |
| **大二** | **工程支柱** | **工程靜力/動力學**、**熱力學**、工程數學 | 各 3 學分 |
| **大三** | **航太核心** | **空氣動力學**、**飛行力學**、**航太構造** | 各 3 學分 |
| **大四** | 推進與系統整合 | **航太推進學**、**軌道力學**、**飛機設計 (Capstone)** | 3-6 學分 |

### 3.2 大二：流體與能量基礎

#### 熱力學 (Thermodynamics)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大二上
- **在學什麼**：研究能量、熱與功的轉換，特別是布雷頓循環 (Brayton Cycle) 與噴嘴流動。
- **解決什麼問題**：如何計算噴射發動機在高空的熱效率？
- **典型題目**：一個理想的布雷頓循環，已知進氣壓力和壓縮比 $\gamma$，計算其熱效率並判斷如何透過「回熱」提高效能。
- **聖經教科書**：*Fundamentals of Engineering Thermodynamics* (Moran & Shapiro)。

### 3.3 大三：航太三大核心

#### 空氣動力學 (Aerodynamics)
- **必/選修**：必修
- **學分**：3+3 (通常分低速與壓縮流)
- **通常開在**：大三
- **在學什麼**：研究空氣繞過物體産生的升力 (Lift) 與阻力 (Drag)。涵蓋薄翼理論、震波 (Shock Wave)。
- **解決什麼問題**：機翼要設計成什麼形狀才能在超音速下保持穩定？
- **典型題目**：已知翼型在大氣壓力 $P_\infty$ 下以 0.8 馬赫飛行，利用普朗特-格勞厄脫 (Prandtl-Glauert) 公式修正升力係數 $C_L$。
- **聖經教科書**：*Fundamentals of Aerodynamics* (John D. Anderson)。

#### 飛行力學 (Flight Mechanics)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三
- **在學什麼**：研究飛機在空中的受力平衡與運動方程 (EOM)，以及靜態/動態穩定性。
- **解決什麼問題**：當飛行員拉動操縱桿時，飛機的仰角會如何隨時間變化？它會自動恢復平衡嗎？
- **典型題目**：計算飛機的中性點 (Neutral Point)，並判斷當重心 (CG) 位在該點後方時，飛機是否具有縱向靜穩定性。
- **聖經教科書**：*Flight Stability and Automatic Control* (Nelson)。

#### 航太構造 (Aerospace Structures)
- **必/選修**：必修
- **學分**：3
- **通常開在**：大三
- **在學什麼**：研究薄壁結構 (Thin-walled structures) 的剪力流、挫曲 (Buckling) 與複合材料。
- **解決什麼問題**：如何讓機翼既輕量又能承受極大的彎矩而不發生變形？
- **典型題目**：給定一個多室盒型樑 (Multi-cell Wing Box) 截面，計算在受扭矩作用下的剪力流 $q$ 分佈。
- **聖經教科書**：*Aircraft Structures for Engineering Students* (Megson)。

### 3.4 大四：太空與推進

#### 軌道力學 (Orbital Mechanics)
- **通常在學**：克卜勒定律、霍曼轉移 (Hohmann Transfer)、衛星姿態控制。
- **典型題目**：計算衛星從 400km 圓軌道轉移到地球同步軌道 (GEO) 所需的兩次脈衝速度增量 $\Delta V$。

#### 航太推進 (Aerospace Propulsion)
- **通常在學**：渦輪扇發動機、沖壓發動機、液態/固態火箭發動機。
- **典型題目**：使用火箭方程 (Tsiolkovsky equation) 計算單級火箭在真空中的最終速度。

### 3.5 跨年級工具
- **軟體**：STK (軌道分析)、XFOIL (翼型設計)、ANSYS Fluent (CFD 流體模擬)、MATLAB (控制系統)。

## 4. 研究所階段（簡述）

常見的分組方向：
1. **空氣動力與燃燒**：高效能燃室設計、計算流體力學 (CFD)。
2. **結構與材料**：航太級複合材料、結構疲勞與斷裂分析。
3. **導航、控制與航電**：自動駕駛演算法、無人機集群 (Swarm)。
4. **太空系統**：衛星熱控、深空探測路徑規劃。

## 5. 博士前沿研究（最多 3 個）

### 5.1 極超音速飛行 (Hypersonics)
- **為什麼最近熱？**：馬赫數 5 以上的飛行。能實現全球一小時到達，也是國防軍備賽的核心。
- **卡在什麼問題？**：極高溫導致的空氣解離與熱化學非平衡流動極難預測，且材料需要承受數千度高溫。
- **代表團隊**：Purdue University, University of Queensland.

### 5.2 全電式航空推進 (Electric Propulsion for Aircraft)
- **為什麼最近熱？**：為了航空減碳。研究高能量密度電池或氫燃料電池驅動馬達轉動扇葉。
- **卡在什麼問題？**：電池能量密度遠低於航空燃油（約 1/40），且高壓電系統在高空的放電效應（電暈）需解決。
- **代表公司**：Joby Aviation, Airbus (E-Fan X).

### 5.3 軌道碎片清除與在軌服務 (Active Debris Removal)
- **為什麼最近熱？**：低地軌道日益擁擠（Kessler Syndrome）。研究利用機械臂、雷射或網子清理廢棄衛星。
- **卡在什麼問題？**：抓取快速旋轉且無合作性 (Non-cooperative) 的物體極具挑戰，且法律責任歸屬複雜。
- **代表團隊**：Astroscale, EPFL (ClearSpace-1).

## 6. 資料來源

### 國際大學系所課程地圖
- **MIT Aeronautics and Astronautics (Course 16)**: [https://aeroastro.mit.edu/academics/undergraduate-program/](https://aeroastro.mit.edu/academics/undergraduate-program/)
- **Georgia Tech Daniel Guggenheim School of AE**: [https://ae.gatech.edu/undergraduate-program](https://ae.gatech.edu/undergraduate-program)
- **Purdue Aeronautics and Astronautics**: [https://engineering.purdue.edu/AAE/academics/undergraduate](https://engineering.purdue.edu/AAE/academics/undergraduate)
- **TU Delft BSc Aerospace Engineering**: [https://www.tudelft.nl/en/education/programmes/bachelors/ae/bachelor-of-aerospace-engineering/](https://www.tudelft.nl/en/education/programmes/bachelors/ae/bachelor-of-aerospace-engineering/)

### 教科書與參考資料
- Anderson (McGraw-Hill), Sutton (Wiley), Megson (Elsevier).
