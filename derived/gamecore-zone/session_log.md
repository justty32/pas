# session_log — gamecore-zone

- 移除死亡 include（event_bus.h、meta_data_component.h、prototype_manager.h），更新 system_ctx.h（移除 EventBus 依賴）、entity_manager.h/cpp（移除 spawn/PrototypeManager）；改寫四份測試檔，25 tests 全綠。
