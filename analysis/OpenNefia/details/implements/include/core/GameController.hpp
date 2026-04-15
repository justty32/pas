#pragma once

#include <string>

namespace opennefia {
namespace core {

/**
 * @brief 遊戲主控制器。
 * 負責初始化所有子系統並執行主循環。
 */
class GameController {
public:
    GameController() = default;
    ~GameController() = default;

    /**
     * @brief 初始化所有引擎子系統。
     * @return true 若初始化成功。
     */
    bool Startup();

    /**
     * @brief 進入遊戲主循環。
     */
    void Run();

    /**
     * @brief 關閉引擎並釋放資源。
     */
    void Shutdown();

private:
    bool _initialized = false;
};

} // namespace core
} // namespace opennefia
