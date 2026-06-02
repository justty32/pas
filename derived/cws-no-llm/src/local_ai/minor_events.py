"""
Phase 4: random_minor_event 詞庫模板生成器

12 個事件類型（6 solo / 6 pair），每種 2–4 句模板，
根據 event_key + 人名 + 地點組合生成事件文字。

infos keys (SOLO):
  avatar_info (str, JSON), location, world_info, event_key, event_desc, tone

infos keys (PAIR):
  avatar_a_name, avatar_a_info, avatar_b_name, avatar_b_info,
  location, world_info, event_key, event_desc, tone,
  relation_hint, current_relation_summary
"""
import json
import random

# ── SOLO 模板 ──────────────────────────────────────────────────────────────────

_SOLO_TEMPLATES: dict[str, list[str]] = {
    "inner_mood_shift": [
        "{name}打坐間忽然思緒萬千，沉寂片刻後重回定境。",
        "{name}修行至半，心湖無端泛起漣漪，片刻後歸於平靜。",
        "{name}閉目凝神，念頭卻不受控地飄向遠處，良久方定。",
        "{name}靜修中忽感心境微澀，調息再三方才疏通。",
    ],
    "inner_obsession": [
        "{name}心底莫名浮起一縷執念，難以言喻，久久難散。",
        "{name}盤膝時忽有所感，某個念頭反覆縈繞，不得其解。",
        "{name}收功後獨坐良久，心中有個疑惑始終難以釋懷。",
    ],
    "daily_practice": [
        "{name}按照慣例研習功法，在{location}中度過了平靜的一天。",
        "{name}拿出法寶仔細擦拭，借機感悟其中紋路，略有所得。",
        "{name}在{location}演練招式，偶有靈感，隨手記錄下來。",
        "{name}潛心溫習功法心要，點滴積累，雖無突破卻頗為踏實。",
    ],
    "environment_response": [
        "{name}佇立{location}，眺望遠山雲海，心胸微微開闊。",
        "{name}漫步{location}，感受靈氣流轉，若有所思。",
        "{name}憑欄而立，望著{location}的景色，思緒飄遠。",
        "{name}在{location}感受到靈氣異動，略作感悟後繼續修煉。",
    ],
    "sect_errand": [
        "{name}奉命在{location}辦理宗門雜務，一切如常。",
        "{name}走訪{location}幾處，完成了今日份內的宗門事務。",
        "{name}領了宗門差事，費了些心力，總算一一辦妥。",
    ],
    "comic_incident": [
        "{name}不慎打翻了身旁器物，狼狽收拾一番，幸無大礙。",
        "{name}今日出了個小差錯，被同門善意調侃了幾句，哭笑不得。",
        "{name}在{location}路過時踩空了一步，幸及時穩住，左右無人，暗自慶幸。",
        "{name}爐火失控了一瞬，驚出一身冷汗，所幸有驚無險。",
    ],
}

# ── PAIR 模板 ──────────────────────────────────────────────────────────────────

_PAIR_TEMPLATES: dict[str, list[str]] = {
    "passing_interaction": [
        "{a}與{b}在{location}擦肩而過，彼此頷首示意，未多言語。",
        "{a}途經{location}時遇上{b}，兩人寒暄幾句便各自離去。",
        "{a}和{b}恰好走過同一條道，對視片刻，各自點頭示意。",
    ],
    "asymmetric_attention": [
        "{a}注意到{b}今日似乎有些心事，卻沒開口詢問。",
        "{a}遠遠望見{b}，對方渾然未覺，各自繼續行事。",
        "{a}偶然聽聞有人談起{b}的近況，心下微有一念，隨即散去。",
    ],
    "subtle_goodwill": [
        "{a}在{location}偶遇{b}，話不多，氣氛卻出乎意料地和諧。",
        "{a}見{b}忙碌，順手提了個醒，對方道了聲謝，氣氛融洽。",
        "{a}與{b}同路一段，閒聊間各有所得，分道時心情略好。",
    ],
    "social_friction": [
        "{a}與{b}在{location}交談時，言語間出現了些微裂痕，不歡而散。",
        "{a}和{b}意見相左，各自冷哼一聲，不再多說。",
        "{a}對{b}的某句話頗感不悅，雖未發作，卻也沒好臉色。",
    ],
    "resource_competition": [
        "{a}與{b}同時看中了{location}的一處靈材，相持片刻後各退一步。",
        "{a}和{b}在修行機緣上起了小爭執，最終以平局收場。",
        "{a}見{b}搶先取走自己眼饞已久的材料，只得按捺心中不悅。",
    ],
    "small_mutual_help": [
        "{a}提點了{b}一個修煉要訣，對方頗為受用，回以謝意。",
        "{a}見{b}遇到困難，伸手相助，雙方氣氛融洽。",
        "{a}與{b}無意間互換了各自欠缺的靈材，各取所需，皆大歡喜。",
    ],
}

_DEFAULT_SOLO = [
    "{name}在{location}度過了平靜普通的一天，波瀾不驚。",
]
_DEFAULT_PAIR = [
    "{a}與{b}在{location}相遇，交流幾句，各自散去。",
]


def _extract_name(avatar_info_raw: str) -> str:
    """從 JSON 字串或字典提取角色名。"""
    if isinstance(avatar_info_raw, dict):
        return str(avatar_info_raw.get("name", "修士"))
    try:
        data = json.loads(avatar_info_raw)
        return str(data.get("name", "修士"))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    # fallback: regex
    import re
    m = re.search(r"['\"]name['\"]\s*:\s*['\"]([^'\"]{1,20})['\"]", avatar_info_raw)
    return m.group(1) if m else "修士"


def gen_minor_event(infos: dict) -> dict:
    event_key = str(infos.get("event_key", ""))
    location = str(infos.get("location", "此地"))

    is_pair = "avatar_a_name" in infos

    if is_pair:
        a = str(infos.get("avatar_a_name", "甲"))
        b = str(infos.get("avatar_b_name", "乙"))
        pool = _PAIR_TEMPLATES.get(event_key, _DEFAULT_PAIR)
        tmpl = random.choice(pool)
        text = tmpl.format(a=a, b=b, location=location)
    else:
        raw_info = infos.get("avatar_info", "")
        name = _extract_name(raw_info)
        pool = _SOLO_TEMPLATES.get(event_key, _DEFAULT_SOLO)
        tmpl = random.choice(pool)
        text = tmpl.format(name=name, location=location)

    return {"event_text": text}
