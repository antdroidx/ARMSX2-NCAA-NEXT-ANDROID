#include "TextureFileIndex.h"
#include <cassert>
#include <algorithm>
#include <thread>
#include <chrono>
#include <iostream>

int main(int argc, char** argv)
{
    assert(argc == 2);
    namespace fs = std::filesystem;
    const fs::path base(argv[1]), root = base / "pack", cache = base / "index.idx";
    fs::create_directories(root / "nested");
    auto write = [](const fs::path& p, const std::string& data) { std::ofstream(p, std::ios::binary) << data; };
    write(root / "a.png", "pixels");
    write(root / "nested/b.png", "pixels");
    std::vector<std::string> files, first;
    bool hit = true;
    auto read = [&] { return TextureFileIndex::GetFiles(root.string(), cache.string(), &files, &hit); };
    assert(read() && !hit && files.size() == 2);
    first = files;
    assert(read() && hit && files == first);
    // Pixel changes do not require rebuilding a filename-only cache.
    write(root / "a.png", "new pixels");
    assert(read() && hit);
    std::this_thread::sleep_for(std::chrono::milliseconds(30));
    write(root / "nested/c.png", "pixels");
    assert(read() && !hit && files.size() == 3);
    assert(read() && hit);
    fs::rename(root / "nested/c.png", root / "nested/d.png");
    assert(read() && !hit && files.size() == 3);
    assert(std::find(files.begin(), files.end(), (root / "nested/d.png").string()) != files.end());
    fs::remove(root / "nested/b.png");
    assert(read() && !hit && files.size() == 2);
    fs::create_directories(root / "empty");
    assert(read() && !hit);
    assert(read() && hit);
    fs::remove(root / "empty");
    assert(read() && !hit);
    write(cache, "truncated");
    assert(read() && !hit && files.size() == 2);
    assert(read() && hit);
    // A valid checksum does not allow filenames to escape the pack root.
    std::vector<TextureFileIndex::Directory> dirs;
    std::vector<std::string> names;
    assert(TextureFileIndex::Scan(root, "", &dirs, &names, 0));
    TextureFileIndex::Save(cache, root.string(), dirs, {"../outside.png"});
    assert(read() && !hit && files.size() == 2);
    TextureFileIndex::Save(cache, root.string(), dirs, {"/outside.png"});
    assert(read() && !hit);
    TextureFileIndex::Save(cache, "other-pack", dirs, names);
    assert(read() && !hit);
    // Cannot write cache: scanning still succeeds, with no false cache hit.
    assert(TextureFileIndex::GetFiles(root.string(), (base / "absent/index.idx").string(), &files, &hit) && !hit);
    std::error_code ec;
    fs::create_directory_symlink(root / "nested", root / "linked", ec);
    if (!ec)
        assert(!read()); // Caller must use the original walker for symlink trees.
    assert(!TextureFileIndex::SafeRelative("a/../b"));
    assert(!TextureFileIndex::SafeRelative("a//b"));
    assert(!TextureFileIndex::SafeRelative("C:/b"));
    assert(TextureFileIndex::SafeRelative("nested/a.png"));
    std::cout << "Texture index cache behavior passed\n";
}
