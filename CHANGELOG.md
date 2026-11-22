# Changelog

## Unreleased

- Desktop app: Fast mode is now always on and its checkbox is gone; the command line still uses normal mode unless you pass `--fast` (ADR 0007).
- Desktop app: the Redo checkbox is gone. To redo videos, delete their `.srt` files or use `--force` on the command line.
- Desktop app: the **New batch** button is gone. When a batch finishes, **Start** becomes **Start over**, which clears the window.

## 0.1.0 – 2026-11-22

First public release.

- Batch-caption every video in a folder (recursively) to a `.srt` next to it, with faster-whisper `large-v3-turbo`.
- Desktop app with drag and drop, per-video status, progress, speed and time left; command line and `captions.bat` drag-and-drop.
- Resumable: videos that already have an `.srt` are skipped; Redo option to replace them.
- Spoken language auto-detected per video, or chosen (99 languages).
- Optional Fast mode (batched inference, about 2.5x faster).
- Runs on an NVIDIA GPU, or falls back to the CPU when there is none.
- Long videos are transcribed in pieces to keep memory use low.
- Robustness: broken videos are logged and skipped, GPU errors stop the batch cleanly, crashed runs are reported at the next launch, the PC is kept awake while running.
- Logs in `%LOCALAPPDATA%\Batscribe`.
