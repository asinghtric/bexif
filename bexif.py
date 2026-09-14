import os
import sys
import shutil
import struct
import tempfile
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict


if sys.platform == "win32":
    os.system("")

# Colors
C_RESET = "\033[0m"
C_BOLD  = "\033[1m"
C_DIM   = "\033[2m"
C_CYAN  = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW= "\033[33m"
C_RED   = "\033[31m"


def ic_jpeg(filepath):
    
    rem = set()
    with open(filepath, "rb") as f:
        data = f.read()

    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return False, rem

    out = bytearray(b"\xff\xd8")
    idx = 2
    modif = False

    while idx < len(data):
        if data[idx] != 0xFF:
            out.extend(data[idx:])
            break

        mark = data[idx + 1]

        if mark == 0xDA:
            out.extend(data[idx:])
            break
        if mark in (0xD8, 0xD9): 
            out.extend(data[idx:idx + 2])
            idx += 2
            continue

        length = struct.unpack(">H", data[idx + 2:idx + 4])[0]
        payl = data[idx + 4 : idx + 2 + length]


        if mark == 0xE1:
            modif = True
            if payl.startswith(b"Exif\x00\x00"):
                rem.add("EXIF Metadata")
                if b"GPS" in payl or b"\x88\x25" in payl:
                    rem.add("GPS Coordinates")
                if b"Make" in payl or b"Model" in payl or b"Apple" in payl or b"Canon" in payl or b"Sony" in payl:
                    rem.add("Camera/Device Details")
                if b"\x90\x03" in payl or b"20" in payl:
                    rem.add("Timestamps / DateOriginal")
            elif b"http://ns.adobe.com/xap/" in payl:
                rem.add("XMP Data / History")
            else:
                rem.add("APP1 Metadata")
        elif mark == 0xED:
            modif = True
            rem.add("IPTC / Photoshop Profile")
        elif mark == 0xFE:
            modif = True
            rem.add("Embedded Comments")

        else:
            out.extend(data[idx : idx + 2 + length])

        idx += 2 + length

    if modif:
        atwrite(filepath, out)
        return True, rem
    return False, rem


def ic_png(filepath):
    rem = set()
    with open(filepath, "rb") as f:
        data = f.read()

    png_sig = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(png_sig):
        return False, rem

    out = bytearray(png_sig)
    idx = 8
    modif = False

    dropc = {
        b"eXIf": "EXIF Metadata",
        b"tEXt": "Text Metadata (tEXt)",
        b"zTXt": "Compressed Text (zTXt)",
        b"iTXt": "International Text / XMP (iTXt)",
        b"tIME": "Creation/Mod Timestamp (tIME)"
    }

    while idx < len(data):
        if idx + 8 > len(data):
            break
        length = struct.unpack(">I", data[idx:idx + 4])[0]
        ctype = data[idx + 4 : idx + 8]
        total_len = 12 + length

        if ctype in dropc:
            modif = True
            rem.add(dropc[ctype])
        else:
            out.extend(data[idx : idx + total_len])

        idx += total_len

    if modif:
        atwrite(filepath, out)
        return True, rem
    return False, rem


def ic_webp(filepath):
    rem = set()
    with open(filepath, "rb") as f:
        data = f.read()

    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return False, rem

    idx = 12
    chunks = []
    modif = False

    while idx < len(data):
        if idx + 8 > len(data):
            break
        fourcc = data[idx:idx + 4]
        size = struct.unpack("<I", data[idx + 4:idx + 8])[0]
        pad = size % 2
        chunk_data = data[idx + 8 : idx + 8 + size]

        if fourcc == b"EXIF":
            modif = True
            rem.add("EXIF Metadata")
        elif fourcc == b"XMP ":
            modif = True
            rem.add("XMP Metadata")
        else:
            chunks.append((fourcc, chunk_data, pad))

        idx += 8 + size + pad

    if modif:
        body = bytearray()
        for fourcc, chunk_data, pad in chunks:
            body.extend(fourcc)
            body.extend(struct.pack("<I", len(chunk_data)))
            body.extend(chunk_data)
            if pad:
                body.extend(b"\x00")

        header = b"RIFF" + struct.pack("<I", len(body) + 4) + b"WEBP"
        atwrite(filepath, header + body)
        return True, rem

    return False, rem


def ic_video(filepath):
    rem = set()
    if not shutil.which("ffmpeg"):
        return False, rem, "ffmpeg not found"

    tmp_out = filepath.with_name(f".clean_{filepath.name}")
    
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(filepath),
        "-map_metadata", "-1",
        "-c", "copy",
        str(tmp_out)
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0 and tmp_out.exists():
            shutil.move(str(tmp_out), str(filepath))
            rem.add("Container Tags / Device Info / GPS")
            return True, rem, None
        else:
            if tmp_out.exists():
                tmp_out.unlink()
            return False, rem, "ffmpeg remux failed"
    except Exception as e:
        if tmp_out.exists():
            tmp_out.unlink()
        return False, rem, str(e)


def atwrite(filepath, cbyte):
    dirname = filepath.parent
    with tempfile.NamedTemporaryFile(delete=False, dir=dirname) as tf:
        tf.write(cbyte)
        temp_name = tf.name
    shutil.move(temp_name, str(filepath))




# Terminal UI UX

def render_progress(done, total, current_filename):
    term_width = shutil.get_terminal_size((80, 20)).columns
    percent = (done / total) if total > 0 else 1.0
    bar_width = 24
    filled = int(bar_width * percent)
    bar = f"{C_GREEN}{'█' * filled}{C_DIM}{'░' * (bar_width - filled)}{C_RESET}"
    
    prefix = f"[{bar}] {int(percent * 100):>3}% ({done}/{total}) "
    remaining = term_width - len(prefix) - 2
    
    if remaining > 10:
        clean_name = current_filename if len(current_filename) <= remaining else f"...{current_filename[-(remaining - 3):]}"
    else:
        clean_name = ""

    sys.stdout.write(f"\r{prefix}{C_CYAN}{clean_name}{C_RESET}")
    sys.stdout.flush()


# Main CLI

SUPP_IMG = {".jpg", ".jpeg", ".png", ".webp"}
SUPP_VID = {".mp4", ".mov", ".m4v", ".mkv"}

def main():
    parser = argparse.ArgumentParser(
        description="bexif - Bulk metadata scrubber for images and videos."
    )
    parser.add_argument("target", help="Directory or file path to scrub")
    parser.add_argument("-r", "--recursive", action="store_true", default=True, help="Scan directories recursively (default: on)")
    args = parser.parse_args()

    targetpath = Path(args.target).expanduser().resolve()
    if not targetpath.exists():
        sys.stderr.write(f"{C_RED}Error: Path '{targetpath}' does not exist.{C_RESET}\n")
        sys.exit(1)

    # Collect files
    if targetpath.is_file():
        files = [targetpath]
    else:
        pattern = "**/*" if args.recursive else "*"
        files = [p for p in targetpath.glob(pattern) if p.is_file()]

    valid_files = [f for f in files if f.suffix.lower() in (SUPP_IMG | SUPP_VID)]

    if not valid_files:
        print(f"{C_YELLOW}No supported image or video files found in {targetpath}{C_RESET}")
        sys.exit(0)

    print(f"\n{C_BOLD}bexif{C_RESET} {C_DIM}— scrubbing metadata across {len(valid_files)} file(s){C_RESET}\n")

    cleaned_count = 0
    skipped_count = 0
    summary_tags = defaultdict(int)
    warnings = []

    has_ffmpeg = bool(shutil.which("ffmpeg"))

    for i, file_path in enumerate(valid_files, start=1):
        render_progress(i, len(valid_files), file_path.name)

        ext = file_path.suffix.lower()
        modif = False
        rem = set()

        try:
            if ext in {".jpg", ".jpeg"}:
                modif, rem = ic_jpeg(file_path)
            elif ext == ".png":
                modif, rem = ic_png(file_path)
            elif ext == ".webp":
                modif, rem = ic_webp(file_path)
            elif ext in SUPP_VID:
                if not has_ffmpeg:
                    warnings.append(f"{file_path.name}: skipped (ffmpeg required for video metadata)")
                else:
                    modif, rem, err = ic_video(file_path)
                    if err:
                        warnings.append(f"{file_path.name}: {err}")
            
            if modif:
                cleaned_count += 1
                for tag in rem:
                    summary_tags[tag] += 1
            else:
                skipped_count += 1

        except Exception as e:
            warnings.append(f"{file_path.name}: {e}")
            skipped_count += 1


    sys.stdout.write("\r" + " " * shutil.get_terminal_size((80, 20)).columns + "\r")
    sys.stdout.flush()


    print(f"{C_BOLD}{C_GREEN}✓ Complete{C_RESET}")
    print(f"  Files scanned : {len(valid_files)}")
    print(f"  Scrubbed      : {cleaned_count}")
    print(f"  Unchanged     : {skipped_count}")

    if summary_tags:
        print(f"\n{C_BOLD}What was rem:{C_RESET}")
        for tag, count in sorted(summary_tags.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {tag:<30} {C_DIM}(found in {count} file{'s' if count > 1 else ''}){C_RESET}")

    if warnings:
        print(f"\n{C_YELLOW}Warnings:{C_RESET}")
        for w in warnings[:5]:
            print(f"  {C_DIM}! {w}{C_RESET}")
        if len(warnings) > 5:
            print(f"  {C_DIM}...and {len(warnings) - 5} more issues.{C_RESET}")

    print("")

main()