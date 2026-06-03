#pragma once

namespace zone {

// 傳給每個自由函式系統的顯式依賴包（仿 medps global_manager.h:ZoneSystem，但
// opennefia 系統常需跨服務存取，不能完全無狀態，所以顯式傳 context 取代 DI 反射）。
//
// Phase 1：EventBus 已移除（無實作），SystemCtx 為空佔位符。
// Phase 2 會補：PrototypeManager& proto, IRandom& rng, Locale& loc
// Phase 3 會補：SaveManager& saves
struct SystemCtx {
    // -- Phase 2 擴充佔位 (commented out until needed) --
    // PrototypeManager& proto;
    // IRandom& rng;
    // Locale& loc;
};

} // namespace zone
