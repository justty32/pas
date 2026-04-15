#include <core/GameController.hpp>
#include <core/ioc/ServiceLocator.hpp>
#include <core/config/ConfigManager.hpp>
#include <core/resources/ResourceCache.hpp>
#include <core/resources/AssetManager.hpp>
#include <core/graphics/Graphics.hpp>
#include <core/ui/UIManager.hpp>
#include <iostream>

namespace opennefia {
namespace core {

bool GameController::Startup() {
    try {
        // 1. 初始化資源系統 (VFS)
        auto resourceCache = std::make_shared<ResourceCache>();
        resourceCache->Initialize("userdata"); // 使用者目錄
        resourceCache->Mount("/", "assets");   // 基本掛載點
        ServiceLocator::RegisterInstance<IResourceCache>(resourceCache);

        // 2. 初始化資產管理器
        auto assetManager = std::make_shared<DefaultAssetManager>();
        assetManager->Initialize(*resourceCache);
        ServiceLocator::RegisterInstance<AssetManager>(assetManager);

        // 3. 初始化圖形系統 (raylib)
        auto graphics = std::make_shared<RaylibGraphics>();
        int width = CVars::DisplayWidth.Get();
        int height = CVars::DisplayHeight.Get();
        graphics->Initialize(width, height, "OpenNefia C++ (Raylib)");
        ServiceLocator::RegisterInstance<IGraphics>(graphics);

        // 4. 初始化 UI 管理器
        auto uiManager = std::make_shared<UIManager>();
        uiManager->Initialize();
        ServiceLocator::RegisterInstance<IUIManager>(uiManager);

        _initialized = true;
        std::cout << "Engine systems initialized successfully." << std::endl;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Engine initialization failed: " << e.what() << std::endl;
        return false;
    }
}

void GameController::Run() {
    if (!_initialized) return;

    auto& graphics = ServiceLocator::Resolve<IGraphics>();
    auto& ui = ServiceLocator::Resolve<IUIManager>();

    while (!graphics.WindowShouldClose()) {
        float dt = ::GetFrameTime();

        // 1. 更新 (Logic)
        ui.Update(dt);

        // 2. 渲染 (Draw)
        graphics.BeginDraw();
        
        // 繪製背景或底層
        graphics.DrawRectangle(0, 0, (float)graphics.GetWidth(), (float)graphics.GetHeight(), DARKGRAY);

        // 繪製 UI 層
        ui.Draw();

        graphics.EndDraw();
    }
}

void GameController::Shutdown() {
    if (!_initialized) return;

    ServiceLocator::Resolve<IUIManager>().Shutdown();
    ServiceLocator::Resolve<IGraphics>().Shutdown();
    ServiceLocator::Resolve<AssetManager>().Shutdown();
    ServiceLocator::Clear();

    _initialized = false;
    std::cout << "Engine systems shut down." << std::endl;
}

} // namespace core
} // namespace opennefia
