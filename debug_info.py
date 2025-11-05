"""
Debug helper to check CrAnki installation
Run this in Anki's debug console: Tools → Add-ons → [CrAnki] → "View Files" button
Then add this to the debug console:

import sys
sys.path.insert(0, '/home/joe/.local/share/Anki2/addons21/cranki')
import debug_info
debug_info.check_installation()
"""

def check_installation():
    """Check if CrAnki is properly installed and configured"""
    print("\n" + "="*60)
    print("CrAnki Installation Diagnostic")
    print("="*60)
    
    try:
        from aqt import mw
        print("✓ Anki main window accessible")
        
        # Check addon manager
        cfg = mw.addonManager.getConfig("cranki")
        print(f"✓ Config loaded: {cfg}")
        
        # Check if filtered deck dialog classes exist
        try:
            from aqt.filtered_deck import FilteredDeckConfigDialog
            print(f"✓ Found FilteredDeckConfigDialog: {FilteredDeckConfigDialog}")
        except ImportError as e:
            print(f"✗ FilteredDeckConfigDialog not found: {e}")
            
            try:
                from aqt.dyndeckconf import DeckConf
                print(f"✓ Found DeckConf (legacy): {DeckConf}")
            except ImportError as e2:
                print(f"✗ DeckConf not found: {e2}")
        
        # Check for filtered decks
        print("\nFiltered decks in collection:")
        for did in mw.col.decks.all_names_and_ids():
            deck = mw.col.decks.get(did.id)
            if deck.get('dyn', False):
                print(f"  - {deck['name']} (ID: {did.id})")
        
        # Check hooks
        from aqt import gui_hooks
        print(f"\n✓ gui_hooks available")
        if hasattr(gui_hooks, 'dialog_manager_did_open_dialog'):
            print(f"✓ dialog_manager_did_open_dialog hook available")
        else:
            print(f"✗ dialog_manager_did_open_dialog hook NOT available")
        
        print("\n" + "="*60)
        print("Diagnostic complete!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"✗ Error during diagnostic: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_installation()
