# CrAnki - Auto Rebuild Filtered Decks Configuration

## Purpose

This addon automatically rebuilds filtered decks at user-specified times. This ensures your filtered decks always contain fresh content based on their search criteria.

## How to Use

1. Open the options for any filtered deck (right-click deck → Options)
2. Check the box "Auto-rebuild at scheduled time"
3. Set your desired rebuild time using the time picker (24-hour format)
4. Click Save

Each filtered deck has independent scheduling - you can set different times for different decks.

## How It Works

- The addon checks every 60 seconds whether any scheduled rebuilds should occur
- When the current time matches a deck's scheduled time, the deck is automatically rebuilt
- Each deck is rebuilt only once per day at the scheduled time
- **Important**: Anki must be running at the scheduled time for the rebuild to occur

## Troubleshooting

If a rebuild doesn't occur:
- Ensure Anki is open and running at the scheduled time
- Verify the filtered deck still exists (not deleted or renamed)
- Check that "Auto-rebuild at scheduled time" is enabled in the deck options
- The addon performs one rebuild per day - if you already manually rebuilt today, it won't rebuild again until tomorrow at the scheduled time

## Configuration

All settings are stored per-deck automatically. No manual configuration file editing is required.
