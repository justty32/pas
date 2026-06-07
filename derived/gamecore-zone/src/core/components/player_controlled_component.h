#pragma once

namespace zone {

// 玩家操控標記（tag）。多角色：可掛在多個 actor 上（取代單一 hero 假設）。
// 排程器對掛此 tag 的 actor，行動指令來自玩家（pending）；無 pending 且 idle → 阻塞。
struct PlayerControlledComponent {
    template<class Archive>
    void serialize(Archive&) {}
};

} // namespace zone
