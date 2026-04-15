# 開發教學 7：如何使用 C++ 開發生物 AI

## 目標
如果您發現 Lua 的效能無法滿足極大規模的生物群集 (Swarm) 或極度複雜的 AI 運算，您可以選擇將 AI 邏輯下放至 C++ 引擎層。本教學將介紹在 Luanti 中以 C++ 開發生態 AI 的兩種主要架構與實作方法。

## 核心概念與架構選擇
在 Luanti 中，所有實體最終都繼承自 C++ 的 `ServerActiveObject` (或其子類別 `UnitSAO`)。
您有兩種方法在 C++ 中實作 AI：

1. **純 C++ 實體 (Custom Engine Fork)**：完全繞過 Lua，直接在 C++ 建立新的實體類別。效能最高，但會使您的遊戲綁定在自定義的引擎分支上，失去 Mod 跨平台相容性。
2. **C++ 邏輯擴充 + Lua 實體 (Hybrid Approach)**：將極度耗時的運算（如群體行為演算法、神經網路）寫在 C++ 並導出為 Lua 函數，然後由 Lua 實體 (`LuaEntitySAO`) 呼叫。**這是官方最推薦的做法。**

---

## 方法 1：Hybrid Approach (C++ 運算 + Lua 控制)

這是在不破壞引擎架構下的最佳解。我們將在 C++ 新增一個名為 `core.calculate_swarm_ai` 的函數。

### 步驟 A：在 C++ 新增 API
開啟 `src/script/lua_api/l_env.cpp`，加入您的 C++ AI 演算法：

```cpp
// 1. 實作 C++ 函數
int ModApiEnv::l_calculate_swarm_ai(lua_State *L)
{
    // 從 Lua 獲取實體與目標的座標
    v3s16 pos = read_v3s16(L, 1);
    v3s16 target = read_v3s16(L, 2);
    
    // 執行極度複雜的 C++ 運算 (例如 Boids 演算法)
    v3f new_velocity = my_custom_c_plus_plus_ai_logic(pos, target);

    // 將結果推回 Lua
    push_v3f(L, new_velocity);
    return 1; // 回傳值數量
}

// 2. 在 l_env.h 的 ModApiEnv 類別中宣告
// static int l_calculate_swarm_ai(lua_State *L);

// 3. 在 Initialize 函數中註冊
void ModApiEnv::Initialize(lua_State *L, int top)
{
    // ... 其他註冊
    API_FCT(calculate_swarm_ai);
}
```

### 步驟 B：在 Lua 端使用
```lua
on_step = function(self, dtime)
    local pos = self.object:get_pos()
    local target_pos = get_target()
    
    -- 呼叫 C++ 高效能 AI 演算法
    local velocity = core.calculate_swarm_ai(pos, target_pos)
    self.object:set_velocity(velocity)
end
```

---

## 方法 2：純 C++ 實體 (Custom Engine Fork)

若您決定打造專屬引擎，可以直接實作繼承自 `UnitSAO` 的新物件。

### 步驟 A：定義 C++ 實體類別
建立 `src/server/mob_sao.h` 與 `mob_sao.cpp`：

```cpp
#pragma once
#include "unit_sao.h"

class MobSAO : public UnitSAO {
public:
    MobSAO(ServerEnvironment *env, v3f pos);
    ~MobSAO() override = default;

    ActiveObjectType getType() const override { return ACTIVEOBJECT_TYPE_GENERIC; }
    ActiveObjectType getSendType() const override { return ACTIVEOBJECT_TYPE_GENERIC; }

    // 每一幀的核心更新邏輯 (AI 大腦)
    void step(float dtime, bool send_recommended) override;
    
    // 序列化，用於存檔
    void getStaticData(std::string *result) const override;
};
```

### 步驟 B：實作 AI 迴圈
在 `step` 函數中實作您的 AI：

```cpp
void MobSAO::step(float dtime, bool send_recommended)
{
    // 呼叫父類別更新基本物理
    UnitSAO::step(dtime, send_recommended);

    // 1. 取得 ServerEnvironment 進行環境掃描
    ServerMap &map = m_env->getServerMap();
    
    // 2. 獲取所有玩家進行索敵
    const std::vector<RemotePlayer*> &players = m_env->getPlayers();
    
    // 3. 呼叫 C++ 原生 Pathfinder 尋路
    // get_path(map, ndef, pos1, pos2, ...)
    
    // 4. 更新移動
    m_base_position += v3f(1.0f * dtime, 0, 0); // 範例：向前走
    
    // 5. 同步給客戶端
    if (send_recommended) {
        m_messages_out.push(ActiveObjectMessage(
            getId(), true,
            generateUpdatePositionCommand(m_base_position, m_velocity, m_acceleration, m_rotation, true, false, dtime)
        ));
    }
}
```

### 步驟 C：註冊實體到伺服器環境
您需要修改 `src/serverenvironment.cpp` 中的 `addActiveObjectRaw` 或建立一個新的 C++ 函數供 Lua 呼叫以生成 (`Spawn`) 這個 `MobSAO`。

## 總結與建議
- 除非您正在製作一個完全獨立且不依賴 Luanti Mod 生態系的遊戲，否則強烈建議使用 **方法 1 (Hybrid Approach)**。
- 這樣可以將最消耗 CPU 的尋路與群體模擬保留在 C++，同時保有 Lua 靈活定義外觀與屬性的優勢。
