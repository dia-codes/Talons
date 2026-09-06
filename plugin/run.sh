#!/bin/bash
# Talons Media Extractor wrapper for Grabbit (macOS Apple Silicon)
# This script wraps yt-dlp to conform to the Grabbit Plugin JSON interface.

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Mode dispatch
if [ "$1" == "--extract" ] || [ "$1" == "--dump-json" ]; then
    URL="$2"
    RESOLUTION="${3:-Best Quality}"
    python3 "$DIR/extractor.py" "$URL" "$RESOLUTION"
elif [ "$1" == "--raw" ]; then
    URL="$2"
    if [ -d "$DIR/yt-dlp" ]; then
        PYTHONPATH="$DIR/yt-dlp:$PYTHONPATH" python3 -m yt_dlp --no-warnings -q --dump-json --yes-playlist -- "$URL"
    elif [ -f "$DIR/yt-dlp" ]; then
        "$DIR/yt-dlp" --no-warnings -q --dump-json --yes-playlist -- "$URL"
    else
        python3 -m yt_dlp --no-warnings -q --dump-json --yes-playlist -- "$URL"
    fi
else
    # Default: treat first argument as URL if no flag is provided
    URL="$1"
    RESOLUTION="${2:-Best Quality}"
    python3 "$DIR/extractor.py" "$URL" "$RESOLUTION"
fi
