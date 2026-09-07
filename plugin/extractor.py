#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import re

def sanitize_filename(title: str, ext: str) -> str:
    clean = re.sub(r'[/\\?%*:|"<>!]', '-', title).strip()
    clean = re.sub(r'\s+', ' ', clean)
    if not clean:
        clean = "download"
    clean_ext = ext.lstrip('.').lower()
    if clean.lower().endswith(f".{clean_ext}"):
        return clean
    return f"{clean}.{clean_ext}"

def process_single_media(data, resolution: str):
    title = data.get("title", "Video")
    thumbnail = data.get("thumbnail", "")
    raw_formats = data.get("formats", [])

    if not raw_formats:
        direct_url = data.get("url")
        if direct_url:
            ext = data.get("ext", "mp4")
            return direct_url, None, ext, title, thumbnail
        return None, None, None, None, None

    direct_formats = []
    for f in raw_formats:
        f_url = f.get("url", "")
        if not f_url:
            continue
        proto = str(f.get("protocol", "")).lower()
        if "m3u8" in proto or ".m3u8" in f_url or "manifest/hls" in f_url or ".mpd" in f_url:
            continue
        direct_formats.append(f)

    if not direct_formats:
        direct_formats = raw_formats

    is_audio_only = (resolution.strip().lower() == "audio only")
    chosen_format = None
    chosen_ext = "m4a" if is_audio_only else "mp4"

    if is_audio_only:
        audio_formats = []
        for f in direct_formats:
            acodec = str(f.get("acodec", "none")).lower()
            vcodec = str(f.get("vcodec", "none")).lower()
            if acodec not in ["none", ""] and vcodec in ["none", ""]:
                audio_formats.append(f)

        def audio_sort_key(f):
            ext = str(f.get("ext", "")).lower()
            apple_score = 1 if ext in ["m4a", "mp3", "aac"] else 0
            abr = float(f.get("abr") or f.get("tbr") or 0.0)
            return (apple_score, abr)

        audio_formats.sort(key=audio_sort_key, reverse=True)
        chosen_format = audio_formats[0] if audio_formats else None

        if not chosen_format:
            with_audio = [f for f in direct_formats if str(f.get("acodec", "none")).lower() not in ["none", ""]]
            chosen_format = with_audio[-1] if with_audio else direct_formats[0]

        ext = str(chosen_format.get("ext", "")).lower()
        if ext in ["mp4", "m4a"]:
            chosen_ext = "m4a"
        elif ext == "mp3":
            chosen_ext = "mp3"
        elif ext in ["webm", "opus"]:
            chosen_ext = "opus"
        else:
            chosen_ext = ext or "m4a"
    else:
        requested_height = None
        for h in [2160, 1440, 1080, 720, 480, 360, 240, 144]:
            if str(h) in resolution:
                requested_height = h
                break

        video_formats = []
        for f in direct_formats:
            vcodec = str(f.get("vcodec", "none")).lower()
            note = str(f.get("format_note", "")).lower()
            if vcodec not in ["none", ""] and "storyboard" not in note:
                video_formats.append(f)

        if not video_formats:
            video_formats = direct_formats

        def parse_height(f):
            try:
                return int(f.get("height") or 0)
            except (ValueError, TypeError):
                return 0

        def parse_bitrate(f):
            try:
                return float(f.get("tbr") or f.get("vbr") or 0.0)
            except (ValueError, TypeError):
                return 0.0

        if requested_height:
            under_or_equal = [f for f in video_formats if parse_height(f) <= requested_height]
            pool = under_or_equal if under_or_equal else video_formats
            
            def height_sort_key(f):
                h = parse_height(f)
                has_audio = 1 if str(f.get("acodec", "none")).lower() not in ["none", ""] else 0
                is_mp4 = 1 if str(f.get("ext", "")).lower() == "mp4" else 0
                bitrate = parse_bitrate(f)
                return (h, has_audio, is_mp4, bitrate)

            pool.sort(key=height_sort_key, reverse=True)
            chosen_format = pool[0]
        else:
            def best_sort_key(f):
                h = parse_height(f)
                is_mp4 = 1 if str(f.get("ext", "")).lower() == "mp4" else 0
                has_audio = 1 if str(f.get("acodec", "none")).lower() not in ["none", ""] else 0
                bitrate = parse_bitrate(f)
                return (h, is_mp4, has_audio, bitrate)

            video_formats.sort(key=best_sort_key, reverse=True)
            chosen_format = video_formats[0]

        ext = str(chosen_format.get("ext", "")).lower()
        chosen_ext = ext if ext else "mp4"

    media_url = chosen_format.get("url")
    audio_url = None
    
    if not is_audio_only:
        has_audio = str(chosen_format.get("acodec", "none")).lower() not in ["none", ""]
        if not has_audio:
            audio_formats = [f for f in direct_formats if str(f.get("acodec", "none")).lower() not in ["none", ""] and str(f.get("vcodec", "none")).lower() in ["none", ""]]
            if not audio_formats:
                audio_formats = [f for f in direct_formats if str(f.get("acodec", "none")).lower() not in ["none", ""]]
            if audio_formats:
                def audio_sort_key(f):
                    e = str(f.get("ext", "")).lower()
                    apple_score = 1 if e in ["m4a", "mp3", "aac"] else 0
                    abr = float(f.get("abr") or f.get("tbr") or 0.0)
                    return (apple_score, abr)
                audio_formats.sort(key=audio_sort_key, reverse=True)
                audio_url = audio_formats[0].get("url")

    return media_url, audio_url, chosen_ext, title, thumbnail

def extract_media(url: str, default_resolution: str = "Best Quality"):
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    ytdlp_dir = os.path.join(plugin_dir, "yt-dlp")
    ytdlp_bin = os.path.join(plugin_dir, "yt-dlp")
    
    env = os.environ.copy()
    if os.path.isdir(ytdlp_dir):
        env["PYTHONPATH"] = f"{ytdlp_dir}:{env.get('PYTHONPATH', '')}"
        cmd = [
            sys.executable or "python3",
            "-m",
            "yt_dlp",
            "--no-warnings",
            "-q",
            "--dump-json",
            "--yes-playlist",
            "--",
            url
        ]
    elif os.path.isfile(ytdlp_bin) and os.access(ytdlp_bin, os.X_OK):
        cmd = [
            ytdlp_bin,
            "--no-warnings",
            "-q",
            "--dump-json",
            "--yes-playlist",
            "--",
            url
        ]
    else:
        cmd = [
            sys.executable or "python3",
            "-m",
            "yt_dlp",
            "--no-warnings",
            "-q",
            "--dump-json",
            "--yes-playlist",
            "--",
            url
        ]

    import concurrent.futures

    flat_cmd = cmd.copy()
    if "--dump-json" in flat_cmd:
        flat_cmd.remove("--dump-json")
    if "--yes-playlist" in flat_cmd:
        idx = flat_cmd.index("--yes-playlist")
        flat_cmd[idx] = "--flat-playlist"
    flat_cmd.insert(-2, "--dump-single-json")

    try:
        proc = subprocess.Popen(flat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        stdout, stderr = proc.communicate()
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute yt-dlp: {str(e)}"}

    if not stdout or not stdout.strip():
        err_msg = stderr.strip() if stderr else "No output from yt-dlp"
        return {"status": "error", "message": err_msg}

    playlist_title = None
    urls_to_fetch = []

    for line in stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith('{'):
            continue
        try:
            metadata = json.loads(line)
            
            # Extract playlist title from the first item if available
            if not playlist_title and metadata.get("playlist_title"):
                playlist_title = metadata.get("playlist_title")

            if metadata.get("_type") == "playlist":
                for entry in metadata.get("entries", []):
                    u = entry.get("url") or entry.get("webpage_url")
                    if u:
                        urls_to_fetch.append(u)
            else:
                u = metadata.get("url") or metadata.get("webpage_url")
                if u:
                    urls_to_fetch.append(u)
        except Exception:
            pass

    if not urls_to_fetch:
        return {"status": "error", "message": "No playable URLs found in playlist"}
        
    urls_to_fetch = list(dict.fromkeys(urls_to_fetch))
    is_playlist_mode = len(urls_to_fetch) > 1
    
    if is_playlist_mode:
        final_title = playlist_title if playlist_title else "Playlist"
        print(json.dumps({"type": "header", "total": len(urls_to_fetch), "playlist_title": final_title}), flush=True)

    parsed_items = []
    resolutions_to_check = ["Best Quality", "1080p", "720p", "480p", "Audio Only"]

    def fetch_single(vid_url):
        single_cmd = cmd.copy()
        if "--yes-playlist" in single_cmd:
            single_cmd[single_cmd.index("--yes-playlist")] = "--no-playlist"
        single_cmd[-1] = vid_url
        try:
            p = subprocess.Popen(single_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            out, _ = p.communicate(timeout=45)
            if out and out.strip().startswith('{'):
                return json.loads(out)
        except Exception:
            pass
        return None

    # Fetch concurrently — capped at 3 workers to avoid rate-limiting
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(fetch_single, urls_to_fetch)
        for i, data in enumerate(results):
            if data:
                item_formats = {}
                best_url = None
                best_audio_url = None
                best_ext = "mp4"
                item_title = "Video"
                item_thumb = ""

                for res in resolutions_to_check:
                    media_url, audio_url, ext, title, thumb = process_single_media(data, res)
                    if media_url:
                        item_formats[res] = media_url
                        if res == default_resolution or (best_url is None):
                            best_url = media_url
                            best_audio_url = audio_url
                            best_ext = ext
                            item_title = title
                            item_thumb = thumb
                
                if best_url:
                    if is_playlist_mode:
                        chunk = {
                            "type": "item",
                            "index": i,
                            "title": item_title,
                            "url": best_url,
                            "ext": best_ext,
                            "formats": item_formats,
                            "thumbnail": item_thumb
                        }
                        if best_audio_url:
                            chunk["audioUrl"] = best_audio_url
                        print(json.dumps(chunk, ensure_ascii=False), flush=True)
                    else:
                        playlist_item = {
                            "title": item_title,
                            "url": best_url,
                            "ext": best_ext,
                            "formats": item_formats,
                            "thumbnail": item_thumb
                        }
                        if best_audio_url:
                            playlist_item["audioUrl"] = best_audio_url
                        parsed_items.append(playlist_item)

    if is_playlist_mode:
        # We already streamed all output directly to stdout for Grabbit to parse
        sys.exit(0)

    if not parsed_items:
        return {"status": "error", "message": "Failed to resolve direct playable stream URLs"}

    return {
        "status": "success",
        "title": parsed_items[0]["title"],
        "playlist": parsed_items
    }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Usage: extractor.py <url> [resolution]"}))
        sys.exit(1)

    url = sys.argv[1]
    resolution = sys.argv[2] if len(sys.argv) > 2 else "Best Quality"

    result = extract_media(url, resolution)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
