#pragma once
#include <filesystem>
#include <fstream>
#include <iterator>
#include <optional>
#include <string>
#include <vector>

// SaveStore：bytes ↔ 儲存後端的抽象（仿 medps zone_store.h，但以字串 slot name 取代 ZoneKey）。
//
// zone_io（save_load.h）處理 registry ↔ bytes；SaveStore 處理 bytes ↔ 儲存。
// Phase 3 提供 FolderSaveStore（每個 slot 一個 .bin 檔）。
// Phase 4 起可視需要加入 ChunkedSaveStore 等後端，不需改動上層序列化邏輯。

namespace zone::serialize {

struct SaveStore {
    virtual ~SaveStore() = default;

    virtual void                       write(const std::string& slot_name,
                                             const std::string& bytes) = 0;
    virtual std::optional<std::string> read(const std::string& slot_name) = 0;
    virtual bool                       has(const std::string& slot_name) = 0;

    // 將待寫資料提交到持久儲存。資料夾後端是 no-op；資料庫 / 打包後端用此做交易點。
    virtual void flush() {}
};

// ---- FolderSaveStore：每個 slot 一個 .bin 檔 --------------------------------
// 目錄下的檔名 = slot_name + ".bin"。
// 仿 medps FolderZoneStore，slot name 取代十六進位 ZoneKey 作為檔名前綴。

class FolderSaveStore : public SaveStore {
public:
    explicit FolderSaveStore(std::filesystem::path dir) : dir_(std::move(dir)) {}

    std::filesystem::path path_for(const std::string& slot_name) const {
        return dir_ / (slot_name + ".bin");
    }

    void write(const std::string& slot_name, const std::string& bytes) override {
        std::filesystem::create_directories(dir_);
        std::ofstream ofs{path_for(slot_name), std::ios::binary};
        ofs.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    }

    std::optional<std::string> read(const std::string& slot_name) override {
        auto p = path_for(slot_name);
        if (!std::filesystem::exists(p)) return std::nullopt;
        std::ifstream ifs{p, std::ios::binary};
        return std::string{std::istreambuf_iterator<char>(ifs),
                           std::istreambuf_iterator<char>()};
    }

    bool has(const std::string& slot_name) override {
        return std::filesystem::exists(path_for(slot_name));
    }

private:
    std::filesystem::path dir_;
};

} // namespace zone::serialize
