"""Cache raw replacement filenames; keep method-specific parsing and decoding intact."""
from pathlib import Path
import shutil

patches = Path(__file__).resolve().parent.parent / 'patches'
native = Path('pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp')
s = native.read_text()
anchor = '#include "common/FileSystem.h"'
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + '\n#include "TextureFileIndex.h"', 1)
old = '\tif (!FileSystem::FindFiles(replacement_dir.c_str(), "*", FILESYSTEM_FIND_FILES | FILESYSTEM_FIND_HIDDEN_FILES | FILESYSTEM_FIND_RECURSIVE, &files))\n\t\treturn;'
new = '''	std::vector<std::string> indexed_files;
	bool index_cache_hit = false;
	const std::string index_path = Path::Combine(EmuFolders::Cache,
		fmt::format("texture-index-v1-{:016x}.idx", TextureFileIndex::Hash(replacement_dir)));
	if (TextureFileIndex::GetFiles(replacement_dir, index_path, &indexed_files, &index_cache_hit))
	{
		files.reserve(indexed_files.size());
		for (std::string& path : indexed_files)
		{
			FILESYSTEM_FIND_DATA fd{};
			fd.FileName = std::move(path);
			files.push_back(std::move(fd));
		}
		Console.WriteLnFmt("Texture filename index: {}", index_cache_hit ? "cache hit" : "rebuilt");
	}
	else if (!FileSystem::FindFiles(replacement_dir.c_str(), "*", FILESYSTEM_FIND_FILES | FILESYSTEM_FIND_HIDDEN_FILES | FILESYSTEM_FIND_RECURSIVE, &files))
		return;'''
assert s.count(old) == 1
native.write_text(s.replace(old, new, 1))
shutil.copyfile(patches / 'TextureFileIndex.h', native.parent / 'TextureFileIndex.h')

ui = Path('platforms/android/app/src/main/java/com/armsx2/ui/settings/RendererTab.kt')
s = ui.read_text()
anchor = '            TextureManagerRow()'
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + '\n            SettingsDivider()\n            RefreshTextureIndexRow()', 1)
s += '''

@Composable
private fun RefreshTextureIndexRow() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val busy = remember { mutableStateOf(false) }
    Box(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(rowAura())
            .clickable(enabled = !busy.value) {
                busy.value = true
                scope.launch {
                    val failed = withContext(Dispatchers.IO) {
                        val cache = File(MainActivityRuntime.assetCopyRoot(context), "cache")
                        cache.listFiles()?.filter {
                            it.isFile && it.name.matches(Regex("texture-index-v1-[0-9a-f]{16}\\\\.idx"))
                        }?.count { !it.delete() } ?: 0
                    }
                    busy.value = false
                    Toast.makeText(context,
                        if (failed == 0) "Restart the game to refresh the texture index."
                        else "Some texture indexes could not be cleared. Close the game and retry.",
                        Toast.LENGTH_LONG).show()
                }
            }.padding(horizontal = 6.dp, vertical = 5.dp),
    ) {
        Column {
            Text(if (busy.value) "Refreshing texture index…" else "Refresh texture index",
                color = MaterialTheme.colorScheme.onSurface, fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(2.dp))
            Text("Rebuilds the filename cache on the next game start. Use after changing a texture pack if files are missing.",
                color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 13.sp)
        }
    }
}
'''
ui.write_text(s)
print('Added persistent texture filename index and manual refresh')
