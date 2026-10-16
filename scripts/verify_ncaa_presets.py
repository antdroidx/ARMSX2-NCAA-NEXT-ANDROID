"""Check parsed defaults, override wiring and executable filtering cases."""
from pathlib import Path
import hashlib
import re
import subprocess
import tempfile
import yaml
from patch_conservative_gs import function

s = Path('bin/resources/GameIndex.yaml').read_text()
db = yaml.safe_load(s)
entry = db['SLUS-21214']
assert entry['clampModes']['vuClampMode'] == 3
assert entry['gsHWFixes'] == {'mipmap': 0, 'bilinearFiltering': 2, 'trilinearFiltering': 1}
start = s.index('  # Extended defaults requested by antdroidx, 2026-10-15.', s.index('SLUS-21214:\n'))
end = s.index('SLUS-21215:\n', start)
assert hashlib.sha256((s[:start] + s[end:]).encode()).hexdigest() == 'fbe72f6f77c5d11d36208e73bc12b53653355700cb085102914e463084f7d8a8'
cpp = Path('pcsx2/GameDatabase.cpp').read_text()
h = Path('pcsx2/GameDatabase.h').read_text()
ids = re.findall(r'^\s*(\w+),\s*$', function(h, 'enum class GSHWFixId'), re.M)
names = re.findall(r'"(\w+)"', cpp[cpp.index('static const char* s_gs_hw_fix_names[]'):cpp.index('static_assert(std::size(s_gs_hw_fix_names)')])
assert len(ids) == len(names) and ids[names.index('bilinearFiltering')] == 'BilinearFiltering'
assert ids[-1] == 'BilinearFiltering' and len(ids) <= 64
is_hack = function(cpp, 'bool GameDatabaseSchema::isUserHackHWFix(')
assert is_hack.index('case GSHWFixId::BilinearFiltering:') < is_hack.index('return false;')
ov = Path('pcsx2/PerGameOverrides.cpp').read_text()
for key, fix in [('filter', 'BilinearFiltering'), ('hw_mipmap', 'Mipmap'), ('TriFilter', 'TrilinearFiltering')]:
    assert f'{{"{key}", GSHWFixId::{fix}, GSUserHackOverride::MaxCount}}' in ov
apply = function(cpp, 'void GameDatabaseSchema::GameEntry::applyGSHardwareFixes(')
assert apply.index('const bool pinned =') < apply.index('if (pinned ||') < apply.index('switch (id)')
cases = ''
for name in ['BilinearFiltering', 'TrilinearFiltering', 'Mipmap']:
    m = re.search(r'\n\s*case GSHWFixId::' + name + r':.*?(?=\n\s*case GSHWFixId::)', apply, re.S)
    assert m
    cases += m[0]
config = Path('pcsx2/Config.h').read_text()
enums = '\n'.join(function(config, 'enum class ' + name) + ';' for name in ['BiFiltering', 'TriFiltering'])
code = r'''
#include <cassert>
#include <cstdint>
#include <initializer_list>
using u8=uint8_t;using s8=int8_t;
struct Log {void Warning(const char*){}} Console;
// ENUMS
enum class GSHWFixId {BilinearFiltering,TrilinearFiltering,Mipmap};
struct Config {BiFiltering TextureFiltering=BiFiltering::Forced;TriFiltering TriFilter=TriFiltering::Automatic;bool HWMipmap=true;};
void apply(Config& config,GSHWFixId id,int value,bool pinned=false){
 if(pinned)return;bool quiet=true;
 switch(id){ // CASES
 }
}
int main(){
 Config c;apply(c,GSHWFixId::Mipmap,0);apply(c,GSHWFixId::BilinearFiltering,2);apply(c,GSHWFixId::TrilinearFiltering,1);
 assert(!c.HWMipmap && c.TextureFiltering==BiFiltering::PS2 && c.TriFilter==TriFiltering::PS2);
 for(int i=-4;i<=7;++i){Config x;apply(x,GSHWFixId::BilinearFiltering,i);assert(static_cast<int>(x.TextureFiltering)==(i>=0&&i<=3?i:1));}
 for(auto id:{GSHWFixId::Mipmap,GSHWFixId::BilinearFiltering,GSHWFixId::TrilinearFiltering}){Config x;apply(x,id,0,true);assert(x.HWMipmap&&x.TextureFiltering==BiFiltering::Forced&&x.TriFilter==TriFiltering::Automatic);}
 Config x;x.TriFilter=TriFiltering::Forced;apply(x,GSHWFixId::TrilinearFiltering,1);assert(x.TriFilter==TriFiltering::Forced);
}
'''
code = code.replace('// ENUMS', enums).replace('// CASES', cases)
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / 'presets.cpp'
    p.write_text(code)
    exe = Path(tmp) / 'presets'
    subprocess.run(['g++', '-std=c++20', '-O2', str(p), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=15)
print('NCAA YAML parsed; other entries preserved; enum/override wiring and filter application cases passed')
