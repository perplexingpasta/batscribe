# The desktop app always uses Fast mode

After using the desktop app for a while, the user found Fast mode's speed (about 2.5x) worth more than the small accuracy loss ADR 0004 weighed against it. The app now always runs Fast mode, and its Fast mode and Redo checkboxes are hidden to keep the window simple. The command line is unchanged: Normal mode by default, `--fast` and `--force` still available, so a careful re-run or a Redo is still possible there.

## Consequences

- Fast mode needs more VRAM than Normal mode, so "The GPU failed" (out of memory) is more likely on small GPUs in the app.
- There is no Redo in the app; delete the Caption files, or use `--force`.
