"""
功法、境界、典籍等抽象概念名詞。
"""

# 功法流派/屬性名詞
TECHNIQUE_TYPES = {
    "ELEMENT": ["五行功法", "雷系神通", "冰系祕法", "風系遁術", "魔功", "佛法"],
    "STYLE": ["劍道", "體修", "魂術", "符籙", "陣法", "御獸", "傀儡"],
}

# 修為境界名詞 (key 與 adjectives.py 保持一致)
REALM_NOUNS = {
    "QI_REFINEMENT": "練氣期",
    "FOUNDATION_ESTABLISHMENT": "築基期",
    "CORE_FORMATION": "金丹期",
    "NASCENT_SOUL": "元嬰期",
    "SOUL_FORMATION": "化神期",
    "VOID_REFINEMENT": "煉虛期",
}

# 經典/典籍類型
BOOK_NOUNS = {
    "GENERAL": ["法訣", "異聞錄", "藥典", "百獸圖譜", "陣法入門", "符籙全解"],
    "ANCIENT": ["太初經", "混沌訣", "長生經", "九轉神功", "天演論", "因果經"],
}
