from pathlib import Path
import re

ROOT = Path("platforms/android/app/src/main/java")

def find_matching_paren(s: str, open_idx: int) -> int:
    depth = 0
    i = open_idx
    state = "normal"
    while i < len(s):
        if state == "normal":
            if s.startswith('"""', i):
                state = "triple"; i += 3; continue
            if s.startswith("//", i):
                state = "line"; i += 2; continue
            if s.startswith("/*", i):
                state = "block"; i += 2; continue
            ch = s[i]
            if ch == '"':
                state = "string"
            elif ch == "'":
                state = "char"
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        elif state == "string":
            if s[i] == "\\":
                i += 2
            elif s[i] == '"':
                state = "normal"; i += 1
            else:
                i += 1
        elif state == "char":
            if s[i] == "\\":
                i += 2
            elif s[i] == "'":
                state = "normal"; i += 1
            else:
                i += 1
        elif state == "triple":
            if s.startswith('"""', i):
                state = "normal"; i += 3
            else:
                i += 1
        elif state == "line":
            if s[i] == "\n":
                state = "normal"
            i += 1
        elif state == "block":
            if s.startswith("*/", i):
                state = "normal"; i += 2
            else:
                i += 1
    raise RuntimeError("unbalanced parentheses")

def split_top_level_args(body: str):
    parts = []
    start = 0
    paren = bracket = brace = 0
    i = 0
    state = "normal"
    while i < len(body):
        if state == "normal":
            if body.startswith('"""', i):
                state = "triple"; i += 3; continue
            if body.startswith("//", i):
                state = "line"; i += 2; continue
            if body.startswith("/*", i):
                state = "block"; i += 2; continue
            ch = body[i]
            if ch == '"':
                state = "string"; i += 1; continue
            if ch == "'":
                state = "char"; i += 1; continue
            if ch == "(":
                paren += 1
            elif ch == ")":
                paren -= 1
            elif ch == "[":
                bracket += 1
            elif ch == "]":
                bracket -= 1
            elif ch == "{":
                brace += 1
            elif ch == "}":
                brace -= 1
            elif ch == "," and paren == 0 and bracket == 0 and brace == 0:
                parts.append(body[start:i])
                start = i + 1
            i += 1
        elif state == "string":
            if body[i] == "\\":
                i += 2
            elif body[i] == '"':
                state = "normal"; i += 1
            else:
                i += 1
        elif state == "char":
            if body[i] == "\\":
                i += 2
            elif body[i] == "'":
                state = "normal"; i += 1
            else:
                i += 1
        elif state == "triple":
            if body.startswith('"""', i):
                state = "normal"; i += 3
            else:
                i += 1
        elif state == "line":
            if body[i] == "\n":
                state = "normal"
            i += 1
        elif state == "block":
            if body.startswith("*/", i):
                state = "normal"; i += 2
            else:
                i += 1
    if body[start:].strip():
        parts.append(body[start:])
    return parts

def named_args(body: str):
    out = []
    for part in split_top_level_args(body):
        m = re.search(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*", part)
        if not m:
            continue
        name = m.group(1)
        expr = part[m.end():].strip()
        # Drop leading/trailing comments which got carried across a comma.
        expr = re.sub(r"^\s*(?://[^\n]*\n\s*)+", "", expr)
        expr = re.sub(r"\s*//[^\n]*$", "", expr).strip()
        if not expr:
            raise RuntimeError(f"empty expression for {name}")
        out.append((name, expr))
    return out

def replace_copy_call(s: str, marker: str, receiver: str, prefix: str = ""):
    start = s.find(marker)
    if start < 0:
        raise RuntimeError(f"copy marker not found: {marker}")
    open_idx = s.find("(", start)
    end = find_matching_paren(s, open_idx)
    args = named_args(s[open_idx + 1:end])
    if not args:
        raise RuntimeError(f"no named args found for: {marker}")
    indent = re.search(r"(?m)^(\s*)[^\n]*$", s[s.rfind("\n", 0, start)+1:start+1])
    # Use a compact lambda; expressions keep their original receiver references.
    statements = "; ".join(f'put("{name}", {expr})' for name, expr in args)
    replacement = f"{prefix}{receiver}.withJson {{ {statements} }}"
    return s[:start] + replacement + s[end + 1:]

# ---------------------------------------------------------------------------
# Settings.kt: eliminate the two Settings.copy$default calls and the no-arg
# Settings() call inside fromJson(). 246 primary fields + receiver + 8 Kotlin
# default masks + marker = 256 invoke registers, which overflows DEX's 8-bit
# invoke/range argument count on Android 17.
# ---------------------------------------------------------------------------
sp = ROOT / "com/armsx2/config/Settings.kt"
s = sp.read_text()

ctor_start = s.index("data class Settings(")
ctor_end = s.index("\n) {", ctor_start)
ctor_text = s[ctor_start:ctor_end]
defaults = {}
for line in ctor_text.splitlines():
    m = re.match(r"^\s*val\s+(\w+)\s*:\s*.+?=\s*(.+?),\s*(?://.*)?$", line)
    if m:
        defaults[m.group(1)] = m.group(2).strip()
if len(defaults) != 246:
    raise RuntimeError(f"Expected 246 Settings defaults, found {len(defaults)}")

# fromJson() already passes all 246 primary-constructor args explicitly (safe:
# 247 registers including receiver). Replace def.foo fallbacks with literal defaults
# so it never emits Settings() -> synthetic default constructor.
fj = s.index("        fun fromJson(json: JSONObject): Settings {")
fj_open = s.index("{", fj)
# Find function closing brace with a simple brace scanner that is safe enough here.
depth = 0
fj_end = None
state = "normal"
i = fj_open
while i < len(s):
    if state == "normal":
        if s.startswith('"""', i): state="triple"; i+=3; continue
        if s.startswith("//", i): state="line"; i+=2; continue
        if s.startswith("/*", i): state="block"; i+=2; continue
        ch=s[i]
        if ch=='"': state="string"
        elif ch=="'": state="char"
        elif ch=="{": depth+=1
        elif ch=="}":
            depth-=1
            if depth==0:
                fj_end=i+1; break
        i+=1
    elif state=="string":
        if s[i]=="\\": i+=2
        elif s[i]=='"': state="normal"; i+=1
        else: i+=1
    elif state=="char":
        if s[i]=="\\": i+=2
        elif s[i]=="'": state="normal"; i+=1
        else: i+=1
    elif state=="triple":
        if s.startswith('"""', i): state="normal"; i+=3
        else: i+=1
    elif state=="line":
        if s[i]=="\n": state="normal"
        i+=1
    elif state=="block":
        if s.startswith("*/", i): state="normal"; i+=2
        else: i+=1
if fj_end is None:
    raise RuntimeError("Could not locate fromJson end")

from_json = s[fj:fj_end]
if "val def = Settings()" not in from_json:
    raise RuntimeError("fromJson Settings() fallback not found")
from_json = from_json.replace(
    "            val def = Settings()\n",
    "            // NCAA NEXT Android 17: avoid Kotlin's 256-register synthetic default constructor.\n",
    1,
)
for name, expr in defaults.items():
    from_json = re.sub(rf"\bdef\.{re.escape(name)}\b", f"({expr})", from_json)
if re.search(r"\bdef\.", from_json):
    missing = sorted(set(re.findall(r"\bdef\.(\w+)", from_json)))
    raise RuntimeError(f"Unreplaced defaults in fromJson: {missing}")
s = s[:fj] + from_json + s[fj_end:]

# Add a verifier-safe replacement for Settings.copy(...).
tojson_marker = "    fun toJson(): JSONObject = JSONObject().apply {"
if "fun withJson(" not in s:
    pos = s.index(tojson_marker)
    helper = '''    /** Android/Dex-safe Settings update path. Avoids the generated copy$default
     *  helper whose invocation requires 256 registers with this 246-field data class. */
    fun withJson(update: JSONObject.() -> Unit): Settings =
        Settings.fromJson(toJson().apply(update))

'''
    s = s[:pos] + helper + s[pos:]

# lowEndPreset(base).copy(...)
marker = "fun lowEndPreset(base: Settings, mtvu: Boolean): Settings = base.copy("
idx = s.find(marker)
if idx < 0:
    raise RuntimeError("lowEndPreset copy block not found")
open_idx = s.find("(", idx + marker.index("base.copy"))
end = find_matching_paren(s, open_idx)
args = named_args(s[open_idx+1:end])
stmts = "; ".join(f'put("{n}", {e})' for n,e in args)
s = s[:idx] + f"fun lowEndPreset(base: Settings, mtvu: Boolean): Settings = base.withJson {{ {stmts} }}" + s[end+1:]

# readFromIni(): return this.copy(...)
marker = "return this.copy("
idx = s.find(marker)
if idx < 0:
    raise RuntimeError("readFromIni this.copy block not found")
open_idx = s.find("(", idx)
end = find_matching_paren(s, open_idx)
args = named_args(s[open_idx+1:end])
stmts = "\n".join(f'        recovered.put("{n}", {e})' for n,e in args)
replacement = "val recovered = this.toJson()\n" + stmts + "\n        return Settings.fromJson(recovered)"
s = s[:idx] + replacement + s[end+1:]

# Guardrails: code (comments excluded loosely) must no longer contain active .copy(
# in Settings.kt, and fromJson must not construct Settings() through defaults.
code_no_comments = re.sub(r"/\*.*?\*/|//[^\n]*", "", s, flags=re.S)
if ".copy(" in code_no_comments:
    raise RuntimeError("Settings.kt still contains active .copy(")
if "val def = Settings()" in s:
    raise RuntimeError("Settings.fromJson still uses Settings()")

sp.write_text(s)

# ---------------------------------------------------------------------------
# ConfigStore.kt: all Settings() and Settings.copy(...) call sites.
# ---------------------------------------------------------------------------
cp = ROOT / "com/armsx2/config/ConfigStore.kt"
c = cp.read_text()
c = c.replace("Settings()", "Settings.fromJson(JSONObject())")

# Every .copy in ConfigStore is a com.armsx2.config.Settings copy in this pinned tree.
while True:
    m = re.search(r"\b(parsed|g|global)\.copy\(", c)
    if not m:
        break
    receiver = m.group(1)
    open_idx = c.find("(", m.start())
    end = find_matching_paren(c, open_idx)
    args = named_args(c[open_idx+1:end])
    if not args:
        raise RuntimeError(f"ConfigStore {receiver}.copy had no named args")
    stmts = "; ".join(f'put("{n}", {e})' for n,e in args)
    replacement = f'{receiver}.withJson {{ {stmts} }}'
    c = c[:m.start()] + replacement + c[end+1:]

code_no_comments = re.sub(r"/\*.*?\*/|//[^\n]*", "", c, flags=re.S)
if re.search(r"\bSettings\(\)", code_no_comments):
    raise RuntimeError("ConfigStore still contains Settings()")
if ".copy(" in code_no_comments:
    raise RuntimeError("ConfigStore still contains active .copy(")
cp.write_text(c)

# ---------------------------------------------------------------------------
# Other startup/UI state holders which directly call the unsafe Settings().
# ---------------------------------------------------------------------------
for rel in (
    "com/armsx2/ui/InGameOverlay.kt",
    "com/armsx2/ui/emulation/EmulationMenuViewModel.kt",
    "com/armsx2/ui/patches/PatchManagerViewModel.kt",
    "com/armsx2/ui/textures/TextureManagerViewModel.kt",
):
    p = ROOT / rel
    t = p.read_text()
    if "Settings()" in t:
        t = t.replace("Settings()", "Settings.fromJson(org.json.JSONObject())")
    p.write_text(t)

print("Applied global Settings default/copy DEX verifier fix")
print(f"Parsed {len(defaults)} Settings defaults")
