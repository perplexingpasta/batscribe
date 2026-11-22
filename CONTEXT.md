# Batscribe

Batscribe turns a folder of videos into subtitle files: every video gets its own `.srt` beside it, so a normal video player shows captions automatically. It runs locally (on an NVIDIA GPU, or more slowly on the CPU), in batches that can be stopped and continued.

## Language

### What goes in

**Input**:
A folder or a single video the user hands to Batscribe (dropped, chosen, or passed on the command line). Folders are searched recursively.
_Avoid_: Source, target, path

**Video**:
A media file with a recognised video extension found in an Input. Only its audio matters.
_Avoid_: Clip, file, lecture

**Name clash**:
Two Videos in the same folder with the same name but different extensions (`a.mp4`, `a.mkv`), which would share one Caption file. Only the first is captioned; the rest are flagged.
_Avoid_: Duplicate

### What comes out

**Caption file**:
The `<video name>.srt` written next to a Video. Its existence is the only record that the Video is done.
_Avoid_: Subtitle, transcript, output

**Other caption file**:
A caption-type file beside a Video that is not its Caption file (`a.en.srt`, `a.vtt`). Flagged to the user but never used or replaced.
_Avoid_: Existing subtitles

**Captioned**:
A Video that already has its Caption file. Captioned Videos are left alone unless the user asks to Redo.
_Avoid_: Done, processed, transcribed

**Cue**:
One subtitle entry: a time span plus at most two short lines of text.
_Avoid_: Subtitle, segment, line

### Running

**Batch**:
One run over the to-do list of Videos chosen from the Inputs (every Video that is not Captioned and not a Name clash). A Batch ends as finished, stopped, or crashed.
_Avoid_: Job, run, session

**Redo**:
Including Captioned Videos in a Batch so their Caption files are replaced. Called `--force` on the command line; the desktop app has no Redo.
_Avoid_: Force, overwrite, re-run

**Normal mode**:
The most accurate way of transcribing; the command line's default.
_Avoid_: Accurate mode, slow mode

**Fast mode**:
Transcribing about 2.5x faster with slightly worse accuracy; always used by the desktop app, opt-in (`--fast`) on the command line.
_Avoid_: Batched mode, turbo

**Spoken language**:
The language the Video's speech is in, either chosen by the user for the whole Batch or detected once per Video ("Auto-detect").
_Avoid_: Locale, subtitle language

**Device**:
Where transcription runs: the NVIDIA GPU, or the CPU as a much slower fallback when no GPU is found.
_Avoid_: Backend, accelerator

**Chunk**:
A piece of a long Video's audio (at most 10 minutes) transcribed on its own; Chunks are stitched back into one Caption file.
_Avoid_: Segment, part

**Speed**:
Seconds of audio transcribed per second of wall-clock time, shown as "Nx realtime".
_Avoid_: Throughput, rate

### When things go wrong

**Failed video**:
A Video that could not be captioned (e.g. unreadable audio). It is logged and the Batch moves on.
_Avoid_: Error, broken file

**GPU error**:
A failure of the graphics card itself (out of memory, driver fault). Unlike a Failed video it stops the Batch, because every remaining Video would fail too.
_Avoid_: CUDA error, crash

**Stopped**:
A Batch the user ended early. The Video in progress gets no Caption file and is redone next time.
_Avoid_: Cancelled, aborted, paused

**Crashed batch**:
A Batch whose process died without recording an end (hard crash, power loss, console closed). Reported once at the next launch.
_Avoid_: Unfinished batch, lost batch

**Setup problem**:
A missing prerequisite (ffmpeg, ffprobe, or the transcription engine) that would make every Video fail, checked before a Batch can start. A missing GPU is not one; it means running on the CPU.
_Avoid_: Prerequisite error, environment issue

### Records

All three live in the user's data folder (`%LOCALAPPDATA%\Batscribe`).

**Error log**:
`batscribe_errors.log`: full details of each Failed video.

**History log**:
`batscribe_history.log`: one line per Batch start/end and per Video outcome, shared by the command line and the window.
_Avoid_: Activity log, run log

**Crash log**:
`batscribe_crash.log`: unexpected errors and native crashes of the window app.
