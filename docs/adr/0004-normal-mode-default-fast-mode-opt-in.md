# Normal mode is the default; Fast mode is opt-in

_Superseded for the desktop app by [ADR 0007](0007-desktop-app-always-uses-fast-mode.md); still true for the command line._

A speed study on a 10-minute excerpt (RTX 3060 Laptop, 6 GB) measured: current settings 23.7x realtime, beam size 1 31.5x, faster-whisper batched pipeline (batch 8) ~60x, Parakeet TDT 0.6B v2 13–64x depending on piece length, two parallel workers only 27.5x combined. The batched pipeline was clearly fastest, but the user judged its output less accurate (e.g. "mums" → "mumps"). So Normal mode (sequential `transcribe`, VAD filter, beam 5, no conditioning on previous text) stays the default, and batched is offered as "Fast mode" (`--fast`).

## Considered Options

- **Parakeet (onnx-asr)**: only fast on very short pieces and adds a second engine; rejected.
- **Parallel workers on one GPU**: barely faster than one worker on 6 GB VRAM; rejected.
- **Beam size 1**: modest gain; not adopted.
