#include "core/turn/zone_effects.h"
#include "core/turn/turn_world.h"
#include "core/turn/move_dir.h"
#include "core/turn/action_def.h"
#include "core/turn/timed_effect.h"
#include "core/maps/map_data.h"
#include "core/components/spatial_component.h"
#include "core/components/actor_component.h"
#include "core/components/health_component.h"
#include "core/components/combat_stats_component.h"
#include "core/components/item_component.h"
#include "core/components/player_controlled_component.h"
#include <algorithm>
#include <string>

namespace zone {

namespace {
void emit(TurnWorld& w, EventKind k, entt::entity a,
          entt::entity b = entt::null, int amount = 0) {
    if (w.events) w.events->push_back(ZoneEvent{ k, a, b, amount });
}
std::string eid(entt::entity e) {
    // 只取 entity index（去掉 version 高位），預設 entt 32-bit 配置為低 20 bits。
    return "#" + std::to_string(static_cast<unsigned>(entt::to_integral(e)) & 0xFFFFFu);
}
// 死亡：玩家操控的 actor 不 destroy（保留實體供 game over / restart），其餘消滅。
void die(entt::registry& reg, entt::entity e) {
    if (!reg.all_of<PlayerControlledComponent>(e)) reg.destroy(e);
}
} // namespace

// ---- 持續效果（DoT）--------------------------------------------------------

void apply_timed_effect(entt::registry& reg, entt::entity e,
                        TimedEffectKind kind, int turns, int power) {
    auto& comp = reg.get_or_emplace<TimedEffectsComponent>(e);
    comp.effects.push_back(TimedEffect{ kind, turns, power });
}

void tick_timed_effects(TurnWorld& w, entt::entity e) {
    auto& reg = w.reg;
    auto* comp = reg.try_get<TimedEffectsComponent>(e);
    if (!comp) return;
    auto* hp = reg.try_get<HealthComponent>(e);

    for (auto& ef : comp->effects) {
        const char* kn = ef.kind == TimedEffectKind::Burning ? "燃燒"
                       : ef.kind == TimedEffectKind::Poison  ? "中毒" : "回復";
        if (hp) {
            if (ef.kind == TimedEffectKind::Regen)
                hp->hp = std::min(hp->max_hp, hp->hp + ef.power);
            else  // Burning / Poison
                hp->hp -= ef.power;
            if (w.trace) w.trace("  DoT " + eid(e) + " " + kn + " "
                + (ef.kind == TimedEffectKind::Regen ? "+" : "-") + std::to_string(ef.power)
                + " → HP " + std::to_string(hp->hp) + " (剩" + std::to_string(ef.turns_left - 1) + ")");
        }
        --ef.turns_left;
    }
    comp->effects.erase(
        std::remove_if(comp->effects.begin(), comp->effects.end(),
                       [](const TimedEffect& x) { return x.turns_left <= 0; }),
        comp->effects.end());

    if (hp && hp->hp <= 0) {
        if (w.trace) w.trace("  " + eid(e) + " 因 DoT 死亡");
        emit(w, EventKind::ActorDied, e, e);
        die(reg, e);
    }
}

// ---- 可組合原語 ------------------------------------------------------------

void resolve_move(TurnWorld& w, entt::entity self, int dx, int dy) {
    auto& reg = w.reg;
    auto* sp = reg.try_get<SpatialComponent>(self);
    if (!sp || !w.map) return;

    const int nx = sp->x + dx, ny = sp->y + dy;
    MapData& map = *w.map;

    if (!map.in_bounds(nx, ny) || !map.at(nx, ny).is_walkable()) {
        if (w.trace) w.trace(eid(self) + " 撞牆 (" + std::to_string(nx) + "," + std::to_string(ny) + ")");
        emit(w, EventKind::BumpedWall, self);
        return;
    }

    // 目標格有 actor → 攻擊（不移動）
    for (auto e : reg.view<ActorComponent, SpatialComponent>()) {
        if (e == self) continue;
        const auto& esp = reg.get<SpatialComponent>(e);
        if (esp.x != nx || esp.y != ny) continue;

        int dmg = 3;
        if (auto* cs = reg.try_get<CombatStatsComponent>(self)) dmg = cs->attack;
        if (auto* hp = reg.try_get<HealthComponent>(e)) {
            hp->hp -= dmg;
            if (hp->hp <= 0) {
                if (w.trace) w.trace(eid(self) + " 擊殺 " + eid(e) + " (-" + std::to_string(dmg) + ")");
                die(reg, e); emit(w, EventKind::ActorDied, self, e);
            } else {
                if (w.trace) w.trace(eid(self) + " 攻擊 " + eid(e) + " -" + std::to_string(dmg)
                    + " → HP " + std::to_string(hp->hp));
                emit(w, EventKind::BumpedActor, self, e, dmg);
            }
        }
        return;
    }

    sp->x = nx;
    sp->y = ny;
    if (w.trace) w.trace(eid(self) + " 移動→(" + std::to_string(nx) + "," + std::to_string(ny) + ")");

    // 自動拾取
    for (auto e : reg.view<ItemComponent, SpatialComponent>()) {
        const auto& isp = reg.get<SpatialComponent>(e);
        if (isp.x != nx || isp.y != ny) continue;
        const auto& item = reg.get<ItemComponent>(e);
        int heal = 0;
        if (item.type == ItemType::health_potion) {
            if (auto* hp = reg.try_get<HealthComponent>(self)) {
                heal = std::min(item.value, hp->max_hp - hp->hp);
                hp->hp += heal;
            }
        }
        reg.destroy(e);
        if (w.trace) w.trace(eid(self) + " 拾取血瓶 +" + std::to_string(heal) + "HP");
        emit(w, EventKind::ItemPickedUp, self, e, heal);
        break;
    }

    if (map.at(nx, ny).is_stair_down())
        emit(w, EventKind::ReachedStairDown, self);
}

void resolve_nova(TurnWorld& w, entt::entity self, int damage,
                  int dot_turns, int dot_power, int radius, int dot_kind) {
    auto& reg = w.reg;
    auto* sp = reg.try_get<SpatialComponent>(self);
    if (!sp) return;
    if (radius < 1) radius = 1;
    const auto kind = static_cast<TimedEffectKind>(dot_kind);
    const char* kname = kind == TimedEffectKind::Poison ? "中毒"
                      : kind == TimedEffectKind::Regen  ? "回復" : "燃燒";

    std::vector<entt::entity> hits;
    for (auto e : reg.view<ActorComponent, SpatialComponent, HealthComponent>()) {
        if (e == self) continue;
        const auto& esp = reg.get<SpatialComponent>(e);
        const int adx = esp.x - sp->x, ady = esp.y - sp->y;
        const int cheb = (adx < 0 ? -adx : adx) > (ady < 0 ? -ady : ady)
                       ? (adx < 0 ? -adx : adx) : (ady < 0 ? -ady : ady);
        if (cheb <= radius) hits.push_back(e);
    }
    if (w.trace) w.trace(eid(self) + " nova(r" + std::to_string(radius) + "): 命中 "
        + std::to_string(hits.size()) + " 個, 每個 -" + std::to_string(damage)
        + (dot_turns > 0 ? std::string(" +") + kname + std::to_string(dot_turns) + "回" : ""));
    for (auto e : hits) {
        auto& hp = reg.get<HealthComponent>(e);
        hp.hp -= damage;
        if (hp.hp <= 0) {
            if (w.trace) w.trace("  nova 擊殺 " + eid(e));
            die(reg, e);
            emit(w, EventKind::ActorDied, self, e);
        } else {
            emit(w, EventKind::BumpedActor, self, e, damage);
            if (dot_turns > 0 && kind != TimedEffectKind::Regen)
                apply_timed_effect(reg, e, kind, dot_turns, dot_power);
        }
    }
}

// ---- 寫死的 effect（呼叫原語）---------------------------------------------

void MoveEffects::on_resolve(TurnWorld& w, entt::entity self, const Action& a) {
    int dx, dy;
    decode_dir(a.param, dx, dy);
    resolve_move(w, self, dx, dy);
}

void CastEffects::on_resolve(TurnWorld& w, entt::entity self, const Action&) {
    resolve_nova(w, self, damage, 3, 2);
}

// ---- 資料驅動 effect（讀 ActionDef 組合原語）------------------------------

void LibraryEffects::on_resolve(TurnWorld& w, entt::entity self, const Action& a) {
    if (!lib || a.def < 0 || a.def >= lib->size()) return;
    const ActionDef& d = lib->at(a.def);

    if (w.trace) w.trace(eid(self) + " 施放技能 [" + d.name + "]");
    if (d.do_move) {
        int dx, dy;
        decode_dir(a.param, dx, dy);
        resolve_move(w, self, dx, dy);
    }
    if (d.nova_damage > 0)
        resolve_nova(w, self, d.nova_damage, d.dot_turns, d.dot_power, d.radius, d.dot_kind);
    if (d.self_heal > 0) {
        if (auto* hp = w.reg.try_get<HealthComponent>(self))
            hp->hp = std::min(hp->max_hp, hp->hp + d.self_heal);
    }
    if (d.self_regen_turns > 0)
        apply_timed_effect(w.reg, self, TimedEffectKind::Regen, d.self_regen_turns, d.self_regen_power);
}

} // namespace zone
