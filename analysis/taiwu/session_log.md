# Taiwu 分析會話紀錄

- 2026-05-24 三個背景 subagent 完成並整合驗證：①奇遇事件(object_data_dump/奇遇事件/,Adventure196+其他遭遇,含簡短介紹)②NPC模板(NPC模板/,Character882完整欄位+EventActors292)③NPC過月行為(NPC過月行為/,12表374列)。**親驗 Adventure ref 錯位**：反編譯列5→語言檔[91]=家常茶会，但 ref[5]=家常酒宴(ref[4]才是家常茶会)，證實 ref 排序≠反編譯 TemplateId→奇遇須走語言檔行號保 Name+Desc 自洽(與一般 ref 優先相反)。三子夾各有 extract 腳本+README，主 README 已加「事件與 NPC」索引段+逐表漂移警示。NPC模板 agent 另解一坑：反編譯複合參數提升為跨列重名區域變數 argN，須分段就近解析(882列108參數對位)。
