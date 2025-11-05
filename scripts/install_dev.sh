#!/bin/bash
# Development installation script for CrAnki addon

# Find Anki addons directory (common locations)
ANKI_ADDON_DIR=""

if [ -d "$HOME/.local/share/Anki2/addons21" ]; then
    ANKI_ADDON_DIR="$HOME/.local/share/Anki2/addons21"
elif [ -d "$HOME/Documents/Anki2/addons21" ]; then
    ANKI_ADDON_DIR="$HOME/Documents/Anki2/addons21"
elif [ -d "$HOME/Library/Application Support/Anki2/addons21" ]; then
    ANKI_ADDON_DIR="$HOME/Library/Application Support/Anki2/addons21"
fi

if [ -z "$ANKI_ADDON_DIR" ]; then
    echo "❌ Could not find Anki addons directory."
    echo "Please manually copy the cranki folder to your Anki addons21 directory."
    echo ""
    echo "Common locations:"
    echo "  Linux: ~/.local/share/Anki2/addons21/"
    echo "  macOS: ~/Library/Application Support/Anki2/addons21/"
    echo "  Windows: %APPDATA%\\Anki2\\addons21\\"
    exit 1
fi

echo "📁 Found Anki addons directory: $ANKI_ADDON_DIR"

# Create symlink or copy
TARGET_DIR="$ANKI_ADDON_DIR/cranki"

# Backup config if it exists
CONFIG_BACKUP=""
if [ -f "$TARGET_DIR/meta.json" ]; then
    echo "💾 Backing up config..."
    CONFIG_BACKUP=$(mktemp)
    cp "$TARGET_DIR/meta.json" "$CONFIG_BACKUP"
fi

if [ -e "$TARGET_DIR" ]; then
    echo "⚠️  Target directory already exists: $TARGET_DIR"
    echo "🔄 Removing old version..."
    rm -rf "$TARGET_DIR"
fi

# Copy addon files
echo "📦 Installing addon..."
mkdir -p "$TARGET_DIR"
cp -r "$(dirname "$0")/../"__init__.py "$TARGET_DIR/"
cp -r "$(dirname "$0")/../src" "$TARGET_DIR/"
cp "$(dirname "$0")/../manifest.json" "$TARGET_DIR/"
cp "$(dirname "$0")/../config.json" "$TARGET_DIR/"

# Remove the install script from the target if it exists
rm -f "$TARGET_DIR/install_dev.sh"
rm -rf "$TARGET_DIR/scripts"

# Restore config if we backed it up
if [ -n "$CONFIG_BACKUP" ] && [ -f "$CONFIG_BACKUP" ]; then
    echo "♻️  Restoring config..."
    cp "$CONFIG_BACKUP" "$TARGET_DIR/meta.json"
    rm "$CONFIG_BACKUP"
fi

echo "✅ Addon installed successfully!"
echo ""
echo "Next steps:"
echo "1. (Re)start Anki"
echo "2. Create or open a filtered deck"
echo "3. Right-click the deck → Options"
echo "4. You should see 'Auto-rebuild at scheduled time' checkbox"
echo "5. Enable it and set a time"
echo "6. Test by setting a time 1-2 minutes in the future"
