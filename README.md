
---
# BEXIF

Bulk metadata and EXIF remover for images and videos. 

Works directly in terminal (Bash, Zsh, Fish, PowerShell, CMD) across macOS, Linux, and Windows 11. Removes metadata at the file-structure level, meaning your images are **not** re-compressed and lose zero visual quality.

---

## Run Instantly (No Installation)

No need to run `pip`, though you **MUST** have python installed on your machine.

### Linux & MacOS (Bash / Zsh / Fish)
```bash
curl -sSL https://raw.githubusercontent.com/asinghtric/bexif/main/bexif.py | python3 - /path/to/your/folder
```

### Windows 11 (PowerShell)
```powershell
irm https://raw.githubusercontent.com/asinghtric/bexif/main/bexif.py | py - "$HOME\Pictures"
```

### Windows 11 (Command Prompt)
```cmd
curl -sSL https://raw.githubusercontent.com/asinghtric/bexif/main/bexif.py | python - "C:\Users\%USERNAME%\Pictures"
```

### Using "uvx"
If you use Astral's `uv`:
```bash
uvx --from git+https://github.com/asinghtric/bexif bexif /path/to/your/folder
```

---

## What It Erases

At the end of each run, `bexif` gives you an exact summary of what it erased:

- **Location Data:** Embedded GPS coordinates and altitude data.
- **Hardware Identifiers:** Camera/phone make, model, lens details, serial numbers.
- **Timestamps:** Original creation dates, digitized dates, modification timestamps.
- **Editing History:** Photoshop profiles, IPTC records, Adobe XMP packets.
- **Hidden Text:** Camera comments, creator notes, software signatures.

---

## Supported Formats & Mechanics

| Format | File Types | Method | Quality Loss? |
| :--- | :--- | :--- | :--- |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.webp` | Pure Python chunk/marker removal | **0%** (Bit-exact pixels preserved, zero recompression) |
| **Videos** | `.mp4`, `.mov`, `.m4v`, `.mkv` | Stream copy via `ffmpeg` (`-c copy`) | **0%** (Container rewritten, streams untouched) |

> **Note on Videos:** Video stripping relies on `ffmpeg` being available in your system `$PATH`. If `ffmpeg` is not installed, video files will be safely skipped with a notice, while all image files will still be erased normally.

---

## Requirements

- **Python 3.8+** (Standard library only — zero `pip` dependencies).
- **ffmpeg** *(Optional)* — Only needed if you want to erase video containers.

---