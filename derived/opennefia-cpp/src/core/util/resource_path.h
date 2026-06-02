#pragma once
#include <string>
#include <string_view>

namespace opennefia {

// 資源路徑的強型別封裝，避免裸 std::string 被誤用。
// 路徑以 "/" 為分隔（VFS 層統一規格，不依賴 OS 路徑）。
class ResourcePath {
public:
    ResourcePath() = default;
    explicit ResourcePath(std::string path) : path_(std::move(path)) {}
    explicit ResourcePath(std::string_view path) : path_(path) {}

    const std::string& str()    const { return path_; }
    std::string_view   view()   const { return path_; }
    bool               empty()  const { return path_.empty(); }

    bool operator==(const ResourcePath& o) const { return path_ == o.path_; }
    bool operator!=(const ResourcePath& o) const { return path_ != o.path_; }
    bool operator< (const ResourcePath& o) const { return path_ <  o.path_; }

    template<class Archive>
    void serialize(Archive& ar) { ar(path_); }

private:
    std::string path_;
};

} // namespace opennefia
