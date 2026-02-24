# Episode Increment Renamer 🎬

A simple GUI-based Python application for batch renaming TV show video episodes by incrementing the episode numbers (e.g., `S03E01` -> `S03E02`). 

> **Note**: This was 100% vibe-coded for personal use! It handles my specific needs for adjusting episode numbers to align with downloaded subtitle tracks.

## Features
- **Regex-based Detection**: Finds `SXXEXX` patterns anywhere in the filename and increments the episode number while preserving zero-padding.
- **Preview Changes**: A clean Tkinter interface showing what the new filenames will look like before applying them.
- **Dry-Run Mode**: Safely simulate the rename changes to confirm how your files will look.
- **Undo Functionality**: Made a mistake? Undo the last batch of changes with a single click.
- **Safe Conflict Handling**: Prompts with options (skip, auto-append `_1`, force overwrite) if target names already exist, including a smart second-pass cleanup to automatically resolve temporary suffix issues.
- **Cross-Platform**: Built purely with standard Python libraries (`os`, `re`, `tkinter`). No extra dependencies required!

## Usage

1. **Prerequisites**: Ensure you have Python 3 installed.
2. Run the script from the terminal:
   ```bash
   py episode_renamer.py
   ```
3. Click "Select Folder" and pick the directory containing your video files (`.mkv`, `.mp4`, `.avi`, `.mov`).
4. Set the increment value (e.g., `+1`, `-1`).
5. Select the files you want to rename in the GUI list.
6. Click "Rename Selected" to execute.

## License
Vibe coded for exactly what it needs to do. Do whatever you want with this.
