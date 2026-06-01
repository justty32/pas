"""
丹藥、食物、毒物等消耗品相關名詞。
"""
# From ITEM_NOUNS in nouns.py
PILL_NOUNS = [
    "凝元丹", "九轉還魂丹", "補氣散",
    "化毒丹", "定神丹", "涅槃丹", "長生丹"
]

# 仙家飲食 (Spiritual Cuisine)
SPIRITUAL_FOOD = {
    "DRINK": ["百果釀", "萬年靈乳", "晨露", "瓊漿玉液"],
    "DISH": ["龍肝鳳髓", "麒麟肉", "千年靈筍", "仙果"],
}

# 毒物與暗器名詞
EXTREME_NOUNS = {
    "POISON": ["斷腸草", "鶴頂紅", "化屍粉", "悲酥清風", "十香軟筋散"],
    "WEAPON": ["袖箭", "飛鏢", "透骨釘", "暴雨梨花針", "如意珠"], # Note: 暗器 are weapons but often single-use, so keeping them here.
}
