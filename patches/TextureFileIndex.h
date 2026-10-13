// SPDX-License-Identifier: GPL-3.0+
#pragma once

// A filename-only cache. Images are still decoded/uploaded by the existing loader.
// Native metadata is required: SAF/virtual paths and symlink trees use the old scan.
#include <cstdint>
#include <chrono>
#include <atomic>
#include <utility>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace TextureFileIndex
{
namespace fs = std::filesystem;
constexpr std::uint64_t MAX_BYTES = 64 * 1024 * 1024;
constexpr std::uint64_t MAX_ENTRIES = 500000;
struct Directory
{
    std::string relative;
    std::vector<std::uint64_t> stamp;
};

inline std::uint64_t Hash(const std::string& bytes)
{
    std::uint64_t value = 14695981039346656037ULL;
    for (unsigned char c : bytes)
        value = (value ^ c) * 1099511628211ULL;
    return value;
}

inline bool SafeRelative(const std::string& path, bool root = false)
{
    if (path.empty())
        return root;
    if (path.front() == '/' || path.find('\\') != std::string::npos ||
        path.find(':') != std::string::npos || path.find('\0') != std::string::npos)
        return false;
    std::size_t start = 0;
    do
    {
        const std::size_t end = path.find('/', start);
        const std::string part = path.substr(start, end - start);
        if (part.empty() || part == "." || part == "..")
            return false;
        if (end == std::string::npos)
            return true;
        start = end + 1;
    } while (start < path.size());
    return false;
}

inline bool Stamp(const fs::path& path, std::vector<std::uint64_t>* result)
{
    std::error_code ec;
    const auto status = fs::symlink_status(path, ec);
    if (ec || !fs::is_directory(status) || fs::is_symlink(status))
        return false;
    const auto modified = fs::last_write_time(path, ec);
    struct stat st{};
    if (ec || ::stat(path.string().c_str(), &st) != 0)
        return false;
    std::uint64_t change_nsec = 0;
#if defined(__APPLE__)
    change_nsec = st.st_ctimespec.tv_nsec;
#elif !defined(_WIN32)
    change_nsec = st.st_ctim.tv_nsec;
#endif
    *result = {static_cast<std::uint64_t>(modified.time_since_epoch().count()),
        static_cast<std::uint64_t>(st.st_ctime), change_nsec,
        static_cast<std::uint64_t>(st.st_dev), static_cast<std::uint64_t>(st.st_ino)};
    return true;
}

inline bool Unchanged(const fs::path& root, const std::vector<Directory>& dirs)
{
    if (dirs.empty() || !dirs.front().relative.empty())
        return false;
    for (const auto& dir : dirs)
    {
        std::vector<std::uint64_t> current;
        if (!Stamp(root / fs::u8path(dir.relative), &current) || current != dir.stamp)
            return false;
    }
    return true;
}

inline void Number(std::string& bytes, std::uint64_t value)
{
    for (int i = 0; i < 8; ++i)
        bytes.push_back(static_cast<char>(value >> (i * 8)));
}
inline void String(std::string& bytes, const std::string& value)
{
    Number(bytes, value.size());
    bytes += value;
}
struct Reader
{
    const std::string& bytes;
    std::size_t offset = 0;
    bool Number(std::uint64_t* value)
    {
        if (bytes.size() - offset < 8)
            return false;
        *value = 0;
        for (int i = 0; i < 8; ++i)
            *value |= static_cast<std::uint64_t>(static_cast<unsigned char>(bytes[offset++])) << (i * 8);
        return true;
    }
    bool String(std::string* value)
    {
        std::uint64_t size;
        if (!Number(&size) || size > 4096 || size > bytes.size() - offset)
            return false;
        *value = bytes.substr(offset, static_cast<std::size_t>(size));
        offset += static_cast<std::size_t>(size);
        return true;
    }
};

inline bool Load(const fs::path& cache, const std::string& root_name,
    std::vector<std::string>* files)
{
    std::ifstream in(cache, std::ios::binary | std::ios::ate);
    if (!in)
        return false;
    const auto size = in.tellg();
    if (size < 8 || static_cast<std::uint64_t>(size) > MAX_BYTES)
        return false;
    std::string bytes(static_cast<std::size_t>(size), '\0');
    in.seekg(0);
    if (!in.read(bytes.data(), static_cast<std::streamsize>(bytes.size())))
        return false;
    Reader checksum{bytes, bytes.size() - 8};
    std::uint64_t expected;
    if (!checksum.Number(&expected) || Hash(bytes.substr(0, bytes.size() - 8)) != expected)
        return false;
    bytes.resize(bytes.size() - 8);
    Reader reader{bytes};
    std::uint64_t version, count;
    std::string stored_root;
    if (!reader.Number(&version) || version != 1 || !reader.String(&stored_root) || stored_root != root_name ||
        !reader.Number(&count) || count == 0 || count > MAX_ENTRIES || count > bytes.size() / 48)
        return false;
    std::vector<Directory> dirs;
    for (std::uint64_t i = 0; i < count; ++i)
    {
        Directory dir;
        if (!reader.String(&dir.relative) || !SafeRelative(dir.relative, i == 0))
            return false;
        for (int n = 0; n < 5; ++n)
        {
            std::uint64_t value;
            if (!reader.Number(&value))
                return false;
            dir.stamp.push_back(value);
        }
        dirs.push_back(std::move(dir));
    }
    if (!Unchanged(fs::u8path(root_name), dirs) || !reader.Number(&count) ||
        count > MAX_ENTRIES || count > bytes.size() / 8)
        return false;
    std::vector<std::string> names;
    for (std::uint64_t i = 0; i < count; ++i)
    {
        std::string name;
        if (!reader.String(&name) || !SafeRelative(name))
            return false;
        names.push_back(std::move(name));
    }
    if (reader.offset != bytes.size())
        return false;
    *files = std::move(names);
    return true;
}

inline void Save(const fs::path& cache, const std::string& root,
    const std::vector<Directory>& dirs, const std::vector<std::string>& files)
{
    std::string bytes;
    Number(bytes, 1);
    String(bytes, root);
    Number(bytes, dirs.size());
    for (const auto& dir : dirs)
    {
        String(bytes, dir.relative);
        for (auto value : dir.stamp)
            Number(bytes, value);
    }
    Number(bytes, files.size());
    for (const auto& name : files)
        String(bytes, name);
    if (bytes.size() > MAX_BYTES - 8)
        return;
    Number(bytes, Hash(bytes));
    // A partial write never becomes the live index. Failure to write is harmless.
    static std::atomic<unsigned> sequence{0};
    const fs::path temp = cache.string() + ".tmp-" +
        std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
        "-" + std::to_string(sequence++);
    {
        std::ofstream out(temp, std::ios::binary | std::ios::trunc);
        if (!out || !out.write(bytes.data(), static_cast<std::streamsize>(bytes.size())) || !out.flush())
        {
            out.close();
            std::error_code ec;
            fs::remove(temp, ec);
            return;
        }
    }
    std::error_code ec;
    #if defined(_WIN32)
    // Windows rename cannot replace a file. A missing index is safe to rebuild.
    fs::remove(cache, ec);
    ec.clear();
#endif
    fs::rename(temp, cache, ec);
    if (ec)
        fs::remove(temp, ec);
}

// Recurse immediately, matching the existing walk's first-match priority.
inline bool Scan(const fs::path& root, const std::string& relative,
    std::vector<Directory>* dirs, std::vector<std::string>* files, unsigned depth)
{
    if (depth > 128 || dirs->size() + files->size() >= MAX_ENTRIES)
        return false;
    Directory dir{relative, {}};
    const fs::path path = root / fs::u8path(relative);
    if (!Stamp(path, &dir.stamp))
        return false;
    dirs->push_back(std::move(dir));
    std::error_code ec;
    fs::directory_iterator it(path, ec), end;
    if (ec)
        return false;
    for (; it != end; it.increment(ec))
    {
        if (ec)
            return false;
        const auto status = it->symlink_status(ec);
        if (ec || fs::is_symlink(status))
            return false;
        const std::string name = it->path().lexically_relative(root).generic_string();
        if (!SafeRelative(name) || name.size() > 4096)
            return false;
        if (fs::is_directory(status))
        {
            if (!Scan(root, name, dirs, files, depth + 1))
                return false;
        }
        else if (fs::is_regular_file(status))
            files->push_back(name);
        if (dirs->size() + files->size() > MAX_ENTRIES)
            return false;
    }
    return !ec;
}

inline bool GetFiles(const std::string& root_name, const std::string& cache_name,
    std::vector<std::string>* output, bool* cache_hit)
{
    *cache_hit = false;
    const fs::path root = fs::u8path(root_name);
    const fs::path cache = fs::u8path(cache_name);
    std::vector<std::string> files;
    if (Load(cache, root_name, &files))
        *cache_hit = true;
    else
    {
        std::vector<Directory> dirs;
        if (!Scan(root, "", &dirs, &files, 0))
            return false;
        // Capture each directory BEFORE enumerating it, then check again. If the
        // pack changed during scanning, use these results once but don't cache them.
        if (Unchanged(root, dirs))
            Save(cache, root_name, dirs, files);
    }
    std::vector<std::string> full;
    full.reserve(files.size());
    for (const auto& name : files)
        full.push_back((root / fs::u8path(name)).string());
    *output = std::move(full);
    return true;
}
} // namespace TextureFileIndex
