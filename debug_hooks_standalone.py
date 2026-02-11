import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

from core.guten_core import GutenCore
from core.hook_index_manager import HookIndexManager

def main():
    # Detect the epub folder
    workdir = Path(".").resolve()
    # Assuming the extracted epub is in a subdirectory or is the current directory.
    # GutenCore scans for container.xml.
    
    # Try to find a folder with META-INF/container.xml
    epub_root = None
    for root, dirs, files in os.walk(workdir):
        if "META-INF" in dirs:
            epub_root = Path(root)
            break
            
    if not epub_root:
        print("ERROR: Could not find an extracted EPUB folder (looking for META-INF).")
        return

    print(f"Loading EPUB from: {epub_root}")
    
    try:
        core = GutenCore.open_folder(epub_root)
        print("GutenCore loaded successfully.")
        
        # Check Manifest
        print(f"Manifest items: {len(core.items_by_id)}")
        html_files = core.hook_index._get_all_html_files()
        print(f"HTML Files found in manifest: {len(html_files)}")
        for f in html_files:
            print(f" - {f}")
            
        # Re-build index explicitly
        print("\nBuilding full index...")
        stats = core.hook_index.build_full_index()
        print(f"Stats: {stats}")
        
        # Check hooks
        all_hooks = core.hook_index.get_all_hooks()
        print(f"\nTotal Hooks found: {len(all_hooks)}")
        
        for h in all_hooks:
            print(f" [HOOK] {h.hook_id} (in {h.file_href})")
            
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
