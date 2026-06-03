#pragma once

namespace zone {

// 傳給每個自由函式系統的顯式依賴包。
// 各系統以純函式形式（free function）接受 entt::registry& 與 SystemCtx&，
// 保持無狀態、易於測試。
//
// Phase 1：SystemCtx 為空佔位符，所有系統僅需 registry。
// Phase 2 可擴充：IRandom& rng, Locale& loc 等輕量服務
// Phase 3 可擴充：SaveManager& saves
struct SystemCtx {
    // -- Phase 2 擴充佔位 (commented out until needed) --
    // IRandom& rng;
    // Locale& loc;
};

} // namespace zone
