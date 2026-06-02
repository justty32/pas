#pragma once
#include <string>
#include <unordered_map>

namespace opennefia {

// LocaleRegistry：語言字串鍵值查找 + {var} 占位符替換。
//
// 使用例：
//   locale.load("data/locale/zh-TW.yaml");
//   locale.get("npc.putit")                                    // → "普提特"
//   locale.get("msg.npc_died", {{"name", "普提特"}})            // → "普提特 倒下了！"
//   locale.get("unknown.key")                                  // → "unknown.key"（fallback）
//
// 設計原則：
//   - 找不到 key 時回傳 key 本身（不丟例外），利於前向相容與除錯
//   - {var} 占位符：模板字串中的 {varname} 以 vars["varname"] 替換；找不到的占位符保留原樣
//   - load() 不存在的檔案 = no-op（保留已載入的字串）
class LocaleRegistry {
public:
    // 從 YAML 檔載入字串表（可多次呼叫；後載入的 key 覆蓋先前的）
    void load(const std::string& path);

    bool has(const std::string& key) const;

    // 查找字串；找不到時回傳 key 本身
    std::string get(const std::string& key) const;

    // 查找字串；找不到時回傳 fallback（而非 key 本身）
    std::string get(const std::string& key, const std::string& fallback) const;

    // 查找字串並替換 {var} 占位符
    std::string get(const std::string& key,
                    const std::unordered_map<std::string, std::string>& vars) const;

private:
    std::unordered_map<std::string, std::string> strings_;

    // 將模板字串中的 {varname} 以 vars 的對應值替換
    static std::string substitute(const std::string& tmpl,
                                  const std::unordered_map<std::string, std::string>& vars);
};

} // namespace opennefia
