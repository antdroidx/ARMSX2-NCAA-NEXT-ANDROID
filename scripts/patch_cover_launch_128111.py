from pathlib import Path

root = Path("platforms/android/app/src/main/java/com/armsx2")
home = root / "data/library/GameLibraryRepository.kt"
s = home.read_text()
old = '''            if (rawRoot?.isDirectory == true) {
                scanRawDirectory(rawRoot, collected, 0)
            } else {
                DocumentFile.fromTreeUri(context, uri)?.let { scanDocumentTree(it, collected, 0) }
            }'''
new = '''            // Prefer SAF content:// document URIs for game boots. The manual ISO picker
            // already uses content:// and boots correctly; raw POSIX library paths may
            // identify a disc without granting the emulation core readable access.
            // Keep raw scanning only as a fallback for non-SAF roots.
            val documentRoot = runCatching { DocumentFile.fromTreeUri(context, uri) }.getOrNull()
            if (documentRoot != null && runCatching { documentRoot.canRead() }.getOrDefault(false)) {
                scanDocumentTree(documentRoot, collected, 0)
            } else if (rawRoot?.isDirectory == true) {
                scanRawDirectory(rawRoot, collected, 0)
            }'''
assert s.count(old) == 1
home.write_text(s.replace(old,new))
print("Prefer picker-equivalent SAF URIs for library launches")
