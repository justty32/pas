"""Phase 4: minor_events 單元測試"""
import sys, json, random
sys.path.insert(0, "C:/code/mine/pas/derived/cws-no-llm/src")

from local_ai.minor_events import gen_minor_event

random.seed(42)
results = []

# SOLO tests
solo_infos = {
    "avatar_info": json.dumps({"name": "青玄"}),
    "location": "天穹峰",
    "event_key": "",
    "event_desc": "...",
    "tone": "中性日常",
}

for key in ["inner_mood_shift", "inner_obsession", "daily_practice",
            "environment_response", "sect_errand", "comic_incident"]:
    solo_infos["event_key"] = key
    r = gen_minor_event(dict(solo_infos))
    text = r["event_text"]
    assert text, f"empty text for {key}"
    assert "青玄" in text, f"name missing in {key}: {text}"
    results.append(f"SOLO {key}: {text}")

# PAIR tests
pair_infos = {
    "avatar_a_name": "玄霄",
    "avatar_b_name": "白鹿",
    "location": "太清宮",
    "event_key": "",
    "event_desc": "...",
    "tone": "中性日常",
    "relation_hint": "不涉及關係變化",
    "current_relation_summary": "...",
}

for key in ["passing_interaction", "asymmetric_attention", "subtle_goodwill",
            "social_friction", "resource_competition", "small_mutual_help"]:
    pair_infos["event_key"] = key
    r = gen_minor_event(dict(pair_infos))
    text = r["event_text"]
    assert text, f"empty text for {key}"
    assert "玄霄" in text or "白鹿" in text, f"names missing in {key}: {text}"
    results.append(f"PAIR {key}: {text}")

# Unknown key fallback
solo_infos["event_key"] = "unknown_event"
r = gen_minor_event(dict(solo_infos))
assert r["event_text"], "empty fallback text"
results.append(f"FALLBACK: {r['event_text']}")

# Write results
with open("C:/code/mine/pas/derived/cws-no-llm/tests/minor_events_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
print("OK: all assertions passed")
