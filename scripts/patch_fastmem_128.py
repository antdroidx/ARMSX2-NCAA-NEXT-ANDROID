"""Restore selectable EE fastmem in the isolated 128 MB test variant."""
from pathlib import Path
from patch_core_efficiency import replace_once
from patch_conservative_gs import function

if __name__ == '__main__':
    p=Path('pcsx2/Config.h');s=p.read_text()
    s=replace_once(s, '#define CHECK_FASTMEM (false)', '#define CHECK_FASTMEM (EmuConfig.Cpu.Recompiler.EnableEE && EmuConfig.Cpu.Recompiler.EnableFastmem)')
    p.write_text(s)
    p=Path('pcsx2/Pcsx2Config.cpp');s=p.read_text()
    p.write_text(replace_once(s, 'EnableFastmem = false;', 'EnableFastmem = true;'))
    p=Path('pcsx2/vtlb.cpp');s=p.read_text()
    # Reservation failure is recoverable on Android too. LoadSettings already
    # prevents a failed/unavailable area from being resurrected on reload.
    anchor='#if TARGET_OS_IPHONE && !TARGET_OS_SIMULATOR\n\t\t\tConsole.Warning("Fastmem disabled: 4 GB virtual-address reservation failed; continuing without fastmem");'
    s=replace_once(s,anchor,anchor.replace('#if TARGET_OS_IPHONE && !TARGET_OS_SIMULATOR','#if (TARGET_OS_IPHONE && !TARGET_OS_SIMULATOR) || defined(__ANDROID__)'))
    # Keep the VA reservation for a later off->on transition. It is not 4GB of RAM.
    # CHECK_FASTMEM still gates mappings/emission while the INI choice is off.
    s=replace_once(s, 'if (env_force || ini_disabled)', 'if (env_force)')
    s=replace_once(s, '// Force-disable fastmem if explicitly requested via env var or INI.', '// Release only for a process-wide opt-out; retain VA while the INI setting is off.')
    anchor='\t\t\ts_fastmem_area.reset();\n\t\t\tvtlbdata.fastmem_base = 0;'
    s=replace_once(s,anchor, '\t\t\ts_fastmem_area_unavailable = true; // Explicit process-wide opt-out.\n'+anchor)
    # Delete the OLD reverse entry before mapping the new physical page.
    old=function(s,'static void vtlb_CreateFastmemMapping(')
    new=replace_once(old,'\t\tconst bool was_coalesced = vtlb_IsHostCoalesced(page);','\t\tconst u32 old_offset = s_fastmem_virtual_mapping[page];\n\t\tconst bool was_coalesced = vtlb_IsHostCoalesced(page);')
    new=replace_once(new,'s_fastmem_physical_mapping.equal_range(mainmem_offset)','s_fastmem_physical_mapping.equal_range(old_offset)')
    s=replace_once(s,old,new)
    old=function(s,'bool vtlb_GetGuestAddress(')
    new=replace_once(old,'\tconst uptr fastmem_start', '\tif (!vtlbdata.fastmem_base || s_fastmem_virtual_mapping.empty())\n\t\treturn false;\n\n\tconst uptr fastmem_start')
    s=replace_once(s,old,new)
    old=function(s,'bool vtlb_ResolveFastmemMapping(')
    start=old.index('\tuptr uaddr =');end=old.index('\n\tFASTMEM_LOG',start)
    new=old[:start]+'''\tconst uptr uaddr = *addr;
\tu32 vaddr;
\tif (!vtlb_GetGuestAddress(uaddr, &vaddr))
\t\treturn false;'''+old[end:]
    s=replace_once(s,old,new)
    old=function(s,'bool vtlb_BackpatchLoadStore(')
    start=old.index('\tuptr fastmem_start');end=old.index('\n\tauto iter',start)
    new=old[:start]+'''\tu32 guest_addr;
\tif (!vtlb_GetGuestAddress(fault_address, &guest_addr))
\t\treturn false;
'''+old[end:]
    new=replace_once(new,'\tconst u32 guest_addr = static_cast<u32>(fault_address - fastmem_start);\n','')
    s=replace_once(s,old,new)
    p.write_text(s)
    print('Experimental 128 MB fastmem: selectable setting restored; safe reservation fallback, range and reverse-remap handling applied')
