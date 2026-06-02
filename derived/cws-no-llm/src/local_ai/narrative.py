"""
Phase 2: 詞庫組合敘事系統
處理 story_teller、interaction_feedback、backstory 任務。

story_teller infos:
  event, res, avatar_name_1, avatar_name_2, [gathering_info, events, details]
interaction_feedback infos:
  world_info, avatar_infos, avatar_name_1, avatar_name_2, action_name,
  action_info, response_actions, feedback_actions
backstory infos:
  world_info, world_lore, avatar_info (str — 呼叫端做了 str() 轉換)
"""
import random
import re


# ═══════════════════════════════════════════════════════════════════════════════
# story_teller
# ═══════════════════════════════════════════════════════════════════════════════

_SINGLE_OPENERS = [
    "{name}踽踽獨行，",
    "這一月，{name}",
    "{name}靜心修行，",
    "山風輕拂，{name}",
    "天地寂然之中，{name}",
    "靈氣氤氳，{name}",
]

_DUAL_OPENERS = [
    "{name1}與{name2}相遇，",
    "{name1}邂逅{name2}，",
    "緣分牽引，{name1}與{name2}",
    "巧合之下，{name1}與{name2}",
    "{name1}偶遇{name2}，",
]

_ENDINGS = [
    "靈氣浮動，天地默然作證。",
    "修仙路漫漫，此行不虛。",
    "世事無常，修士自強不息。",
    "功法精進，非一日之功。",
    "因緣際會，皆有深意。",
    "山河為鑒，道途無悔。",
    "",  # 偶爾留白，使語感自然
    "",
]

_GATHERING_LEADS = [
    "眾修士匯聚一堂，",
    "一場難得的盛會，",
    "天南地北的修士雲集，",
    "修仙界一時風雲際會，",
]


def _tell_story(infos: dict) -> str:
    event = str(infos.get("event", "")).strip()
    res   = str(infos.get("res", "")).strip()
    name1 = str(infos.get("avatar_name_1", "")).strip()
    name2 = str(infos.get("avatar_name_2", "")).strip()

    # 集會故事
    if "gathering_info" in infos:
        lead   = random.choice(_GATHERING_LEADS)
        g_info = str(infos.get("gathering_info", "盛事"))[:80]
        events = str(infos.get("events", ""))[:150]
        ending = random.choice(_ENDINGS)
        parts  = [lead + g_info + "。"]
        if events:
            parts.append(events)
        if ending:
            parts.append(ending)
        return " ".join(p for p in parts if p).strip()

    # 雙人故事
    if name1 and name2:
        opener = random.choice(_DUAL_OPENERS).format(name1=name1, name2=name2)
        body   = (event + "，") if event else ""
        result = (res + "。") if res else ""
        ending = random.choice(_ENDINGS)
        return (opener + body + result + ending).strip()

    # 單人故事
    if name1:
        opener = random.choice(_SINGLE_OPENERS).format(name=name1)
        body   = (event + "，") if event else ""
        result = (res + "。") if res else ""
        ending = random.choice(_ENDINGS)
        return (opener + body + result + ending).strip()

    # 兜底
    if event and res:
        return f"{event}。{res}。"
    return event or res or "修行之路，點滴積累。"


def gen_story(infos: dict) -> dict:
    return {"story": _tell_story(infos)}


# ═══════════════════════════════════════════════════════════════════════════════
# interaction_feedback
# ═══════════════════════════════════════════════════════════════════════════════

# 動作類別 → (接受回應池, 拒絕回應池)
_FEEDBACK_BY_KEY = {
    "spar": (
        ["{t2}接下{t1}的邀約，雙方拆招過招，各有所得。",
         "{t2}欣然應戰，切磋過後相視而笑。",
         "一番比拼，{t2}深感功力又有精進。"],
        ["{t2}婉拒了{t1}的邀約，言稱時機未到。",
         "{t2}搖頭謝絕，此時不宜妄動。"],
    ),
    "conversation": (
        ["{t2}與{t1}暢談一番，各抒所見，頗有收穫。",
         "二人相談甚歡，{t2}覺得此行有所啟發。",
         "{t2}耐心聆聽，心中若有所悟。"],
        ["{t2}敷衍幾句，無意深談。",
         "{t2}僅是點頭應承，心思並不在此。"],
    ),
    "gift": (
        ["{t2}欣然收下，道謝離去。",
         "收到{t1}的贈禮，{t2}頗為感激。",
         "{t2}微笑接受，心中記下這份情誼。"],
        ["{t2}婉拒了好意，言稱無功不受祿。",
         "{t2}推讓再三，終究沒有收下。"],
    ),
    "impart": (
        ["{t2}認真聆聽{t1}的傳授，若有所悟。",
         "{t2}受教了，拱手致謝。",
         "{t2}細細體悟，感激涕零。"],
        ["{t2}禮貌地婉拒，自有修行之道。"],
    ),
    "attack": (
        ["{t2}迎戰{t1}，二人展開激烈衝突。",
         "面對{t1}的挑釁，{t2}毫不退縮。"],
        ["{t2}選擇迴避，此時不宜正面交鋒。",
         "{t2}轉身離去，不與{t1}糾纏。"],
    ),
    "brotherhood": (
        ["{t2}與{t1}把酒言歡，義結金蘭。",
         "{t2}欣然同意，二人從此情同手足。"],
        ["{t2}婉拒了，緣分未到，難以結義。"],
    ),
}

_FEEDBACK_DEFAULT = (
    ["{t2}與{t1}各自道別，此行平淡無波。",
     "{t2}點頭示意，繼續自己的修行。",
     "{t2}應對{t1}的舉動，彼此相安無事。"],
    ["{t2}婉拒了{t1}，各自散去。",
     "{t2}搖頭謝絕，無意參與。"],
)


def _classify_action(action_name: str) -> str:
    n = action_name.lower()
    if any(k in n for k in ("spar", "切磋", "比武", "拆招")):
        return "spar"
    if any(k in n for k in ("conversation", "talk", "交流", "對話", "聊", "談")):
        return "conversation"
    if any(k in n for k in ("gift", "贈", "送禮")):
        return "gift"
    if any(k in n for k in ("impart", "傳", "授", "教")):
        return "impart"
    if any(k in n for k in ("attack", "攻", "殺")):
        return "attack"
    if any(k in n for k in ("brotherhood", "結義", "結拜", "sworn")):
        return "brotherhood"
    return ""


def _gen_feedback(infos: dict) -> dict:
    name1  = str(infos.get("avatar_name_1", "對方")).strip() or "對方"
    name2  = str(infos.get("avatar_name_2", "另一方")).strip() or "另一方"
    action = str(infos.get("action_name", "")).strip()

    key = _classify_action(action)
    accept_pool, reject_pool = _FEEDBACK_BY_KEY.get(key, _FEEDBACK_DEFAULT)

    # interaction_feedback 呼叫時 response_actions 通常為空；保留判斷供未來擴充。
    response_actions = infos.get("response_actions", [])
    if "Reject" in response_actions and random.random() < 0.25:
        template = random.choice(reject_pool)
    else:
        template = random.choice(accept_pool)

    response = template.format(t1=name1, t2=name2)
    return {"response": response, "thinking": ""}


def gen_interaction_feedback(infos: dict) -> dict:
    return _gen_feedback(infos)


# ═══════════════════════════════════════════════════════════════════════════════
# backstory
# ═══════════════════════════════════════════════════════════════════════════════

_ORIGINS = [
    "凡人家庭", "落魄修仙世家", "山村獵戶之家", "書香門第",
    "邊疆小城", "偏遠農村", "漁村海濱", "商賈之家",
    "江湖散修門派", "遺落的小宗族",
]

_TALENT_TRAITS = [
    "展露修仙資質",
    "偶然覺醒靈根",
    "因緣際會習得基礎法術",
    "憑藉頑強意志踏上修煉之路",
    "受長輩指點習得初級功法",
    "於危難中激發潛能",
]

_EARLY_EVENTS = [
    "歷經磨難，始終未曾放棄",
    "輾轉多地尋訪名師",
    "嘗遍冷暖，愈挫愈勇",
    "一路顛沛，積累了豐富的江湖閱歷",
    "數度生死關頭，僥倖脫險",
    "憑藉機緣突破瓶頸，一步步走到今日",
]

_CURRENT_STATUS = [
    "已在修仙界站穩腳跟",
    "仍在艱辛修行之中",
    "逐漸嶄露頭角",
    "默默無聞地積蓄實力",
    "聲名初顯，前途未可限量",
]

_AMBITIONS = [
    "在這修仙世界留下自己的名字",
    "突破境界，窺見長生之道",
    "保護身邊之人，不再讓親友蒙難",
    "尋得那傳說中的機緣，一飛沖天",
    "以自身功法，為後輩開闢一條新路",
    "查明身世之謎，了卻心中執念",
]


def _extract_name_from_str(avatar_info_str: str) -> str:
    """backstory 呼叫端傳的是 str(dict)，嘗試提取 name 字段。"""
    m = re.search(r"['\"]name['\"]\s*:\s*['\"]([^'\"]{1,20})['\"]", avatar_info_str)
    if m:
        return m.group(1)
    return "此人"


def _gen_backstory(infos: dict) -> str:
    avatar_info = infos.get("avatar_info", "")

    if isinstance(avatar_info, dict):
        name = avatar_info.get("name", "") or "此人"
    else:
        name = _extract_name_from_str(str(avatar_info))

    origin   = random.choice(_ORIGINS)
    talent   = random.choice(_TALENT_TRAITS)
    early    = random.choice(_EARLY_EVENTS)
    status   = random.choice(_CURRENT_STATUS)
    ambition = random.choice(_AMBITIONS)

    return (
        f"{name}出身{origin}，自幼{talent}，由此踏上修仙之途。"
        f"年少時{early}，深感此路艱辛。"
        f"如今{status}，立志{ambition}。"
    )


def gen_backstory(infos: dict) -> dict:
    return {"backstory": _gen_backstory(infos)}
