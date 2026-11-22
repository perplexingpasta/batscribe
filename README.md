<p align="center"><img src="batscribe.png" width="96" alt="Batscribe icon"></p>

# Batscribe

[![tests](https://github.com/perplexingpasta/batscribe/actions/workflows/tests.yml/badge.svg)](https://github.com/perplexingpasta/batscribe/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Caption a whole folder of videos at once, locally, on your own PC.**

> **Platform:** Windows 10/11. Fast with an **NVIDIA GPU** (about 20–25x realtime); without one it falls back to the CPU, which works but is roughly 10x slower. The command line should also work on Linux, but that is untested.

Drop a folder onto Batscribe and every video inside it (including subfolders) gets a matching `.srt` subtitle file right next to it. Players like VLC and MPC pick those up automatically, so you can watch with captions straight away. Nothing is uploaded: transcription runs on your machine using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and the Whisper `large-v3-turbo` model.

<p align="center"><img src="docs/images/screenshot.png" width="560" alt="Batscribe window captioning a folder of videos"></p>

```
Course/
├── 01 Intro.mp4
├── 01 Intro.srt        ← created by Batscribe
├── Module 2/
│   ├── Lesson 1.mp4
│   └── Lesson 1.srt    ← created by Batscribe
```

## Features

- **Batch everything**: folders are searched recursively; `.mp4 .mkv .mov .avi .webm .m4v` supported.
- **Resumable**: videos that already have an `.srt` are skipped, so you can stop at any time and pick up later.
- **Two ways to use it**: a desktop window with drag and drop, or a command line / drag-onto-`captions.bat`.
- **99 languages**: the spoken language is detected per video, or you can choose it.
- **Progress you can trust**: per-video and overall progress, speed (e.g. "24x realtime") and time left.
- **Fast mode**: the desktop app uses it, about 2.5x faster than normal mode for slightly lower accuracy. The command line uses normal mode unless you pass `--fast`.
- **Handles long videos and long nights**: long videos are processed in pieces to keep memory low, the PC is kept awake during a run, and you get a sound and message when it finishes.
- **Safe with problems**: a broken video is logged and skipped; a GPU failure stops the run cleanly; a crash is reported the next time you open the app.

## Requirements

- Windows 10/11
- Python 3.10 or newer (developed on 3.12)
- [ffmpeg](https://ffmpeg.org/download.html), with `ffmpeg` and `ffprobe` on your PATH (e.g. `winget install ffmpeg`)
- Recommended: an NVIDIA GPU with a recent driver and at least 4 GB of VRAM (developed on an RTX 3060 Laptop with 6 GB). You don't need the CUDA toolkit; the CUDA libraries come from pip.

## Install

```powershell
git clone https://github.com/perplexingpasta/batscribe.git
cd batscribe
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` takes current compatible versions. If something breaks, `requirements-lock.txt` has the exact versions Batscribe was tested with.

The first run downloads the Whisper model (about 1.6 GB).

Optional: create a Start menu shortcut (with the icon, and pinnable to the taskbar):

```powershell
powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
```

## Use

### Desktop app

Open **Batscribe** from the Start menu (or run `.venv\Scripts\pythonw.exe batscribe_gui.py`).

1. Drop a folder or some videos on the window, or use **Choose folder…** / **Choose videos…**.
2. Check the list: what's to do, what's already captioned, and any warnings.
3. Press **Start**. You can **Stop** at any time; the video in progress is simply redone next time.

Double-click a video to play it. **Logs** opens the history of all runs. When a batch finishes, **Start** becomes **Start over**, which clears the window so you can choose new videos.

Option:
- **Spoken language**: Auto-detect (the default) or a specific language. Choosing one avoids the rare wrong guess, e.g. on a video that starts with music.

### Drag and drop onto `captions.bat`

Drag a folder (or video files) onto `captions.bat`. A console window shows progress and stays open at the end.

### Command line

```powershell
.venv\Scripts\python.exe batscribe.py "D:\Videos\Course" [more folders or videos] [options]
```

| Option | Meaning |
|---|---|
| `--language CODE` | Spoken language, e.g. `en`, `de`, `es`, `ja` (default `auto`: detect per video) |
| `--fast` | Fast mode: about 2.5x faster, slightly less accurate |
| `--force` | Redo videos that already have an `.srt` |
| `--device auto\|cuda\|cpu` | Where to run (default `auto`: NVIDIA GPU if found, otherwise CPU) |
| `--model NAME` | Whisper model (default `large-v3-turbo`) |
| `--compute-type T` | CTranslate2 precision (default `int8_float16` on GPU, `int8` on CPU) |

Exit code is 0 on success, 1 if any video failed (or setup is broken), 130 if interrupted.

## Good to know

- **Speed**: on an RTX 3060 Laptop expect roughly 20–25x realtime (a 1-hour video in about 3 minutes), and 50–60x in Fast mode. On a CPU, expect roughly 1–2x realtime.
- **Same-name videos**: `lesson.mp4` and `lesson.mkv` in one folder would share one `lesson.srt`, so only the first is captioned. Rename one to caption both.
- **Other subtitles**: existing files like `lesson.en.srt` or `lesson.vtt` are left untouched; Batscribe still writes `lesson.srt`.
- **Privacy**: everything runs locally. The only network access is downloading the model from Hugging Face on first use.

## Logs

All logs are in `%LOCALAPPDATA%\Batscribe` (the **Logs** button opens the history).

| File | What |
|---|---|
| `batscribe_history.log` | every run and every video's result |
| `batscribe_errors.log` | full details of videos that failed |
| `batscribe_crash.log` | unexpected errors in the desktop app |

## Troubleshooting

- **"ffmpeg was not found"**: install ffmpeg and make sure `ffmpeg -version` works in a new terminal.
- **"No NVIDIA GPU was found"** (or it's unexpectedly slow): update the NVIDIA driver; on laptops, make sure the GPU isn't disabled. Without a GPU, Batscribe runs on the CPU.
- **"The GPU failed"**: usually out of video memory. Close games or other GPU-heavy apps (or restart), then press Start again; finished videos are kept. Fast mode needs more VRAM than normal mode.
- **"The last run didn't finish"**: the PC crashed, lost power or the window was closed. Choose the same folder and press Start to continue.
- **Wrong language in the captions**: choose the language instead of Auto-detect, then redo those videos (delete their `.srt` files, or use `--force` on the command line).

## Contributing

Issues and pull requests are welcome. Run the tests before sending a change:

```powershell
.venv\Scripts\python.exe -m unittest discover tests
```

The tests use a fake model, so no GPU, ffmpeg or videos are needed; they also run on GitHub Actions for every pull request.

For how the code is organised, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The project vocabulary is in [`CONTEXT.md`](CONTEXT.md) and design decisions are in [`docs/adr/`](docs/adr/). Changes are listed in [`CHANGELOG.md`](CHANGELOG.md).

## License

[MIT](LICENSE). Batscribe uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT), OpenAI's [Whisper](https://github.com/openai/whisper) models (MIT) and [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) (MIT). ffmpeg is not bundled.
