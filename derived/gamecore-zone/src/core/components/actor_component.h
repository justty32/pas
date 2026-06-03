#pragma once

namespace zone {

// ActorComponent — 空 tag，標記「有行動資格」的實體（英雄、NPC）。
// advance_turn() 的 actor poll 依此 tag 選取行動者；物品、地形等不掛此 tag。
struct ActorComponent {};

} // namespace zone
