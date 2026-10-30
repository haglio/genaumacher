# genaumacher — Project-Specific Instructions

Shared rules are in the global `~/.claude/CLAUDE.md`. This file contains only genaumacher-specific overrides.

## Test commands

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Architecture

Genaumacher is a standalone PyQt6/OpenCV video clip editor, extracted from the fun_time project. Key relationships:

- **What the suite tells genaumacher**: exactly two things, both about one video. Fun Time's `;` pushes — it reads the Main Funestra's status file and runs `python -m genaumacher.create_session --video <path> --time <seconds>`. `genaumacher/main_funestra_prefill.py` pulls the same two fields out of the same file, for the case where genaumacher is opened on its own; the file's location is one optional key in genaumacher's own `content.local.json`. **Genaumacher does not read fun_time's config**, and has no path to the fun_time checkout. It used to do both, for a VLC prefill the suite outgrew.
- **Output dirs**: The settings all of Haglio shares (`~/.haglio/settings.json`) say where Genau's folder is, as `genau_dir`, and where its sounds go, as `genau_audio_dir`. `genaumacher/paths.py` reads each through `app_support.haglio_settings` in one function (`_genau_dir`, `audio_dir`) and no other file spells either place, so moving them is a change to the settings and to nothing here. Clips export to `<genau_dir>/clips/2D/non_AI/`, VR clips to `<genau_dir>/clips/VR/`, audio to `<genau_audio_dir>/`; the two need not share a parent. Genau's `genau_contract.json` names the 2D and VR folders, and `tests/test_genau_contract.py` holds these to it.
- **What an export records**: what made each finished clip, as `provenance.cut` on the clip's metadata sidecar (`<library-root>/videos/metadata/genau/clips/2D/non_AI/<name>.json`, the record Evolver keeps for that clip). A sweep reads it to find the clips made before a change and remake them. The sidecar is filed by the clip's path beneath the library's videos folder, so it stays at that place whether `genau_dir` is `<library-root>/videos/genau` or `<library-root>/videos/videos/genau`; `tests/test_sidecar.py` holds it there for both.
- **Entry point**: `python -m genaumacher` -> `__main__.py` -> `app.py:main()` -> launcher dialog -> UI.
- **Launcher chain**: `Genaumacher.lnk` -> `wscript.exe` -> `launch_genaumacher.vbs` -> `python -m genaumacher`. `Genaumacher.lnk` is git-ignored, so it is made by hand on each machine; every start stamps the taskbar's pinned copy with the AppUserModelID the app claims, so the running window groups under the pin instead of opening a second, unlabelled button. `launch_genaumacher.vbs` is rendered from its spec in `pyproject.toml` by `python -m app_support.launcher --write`, and `tests/test_launcher_contract.py` fails on a hand edit.
- **Shared scaffolding**: logging setup, exception hooks and `hidden_subprocess_kwargs` come from the sibling `../app_support`, which every app in this family installs editable — fix those there, not here. Install it with `--config-settings editable_mode=compat`; its README says why, and its `tests/test_install.py` goes red without it.

## Fetching RIFE

The frame interpolator the normalize step defaults to is **not in the repo**.
A fresh checkout has no `tools/rife-ncnn-vulkan-20221029-windows/`; fetch it once:

```powershell
.\.venv\Scripts\python.exe tools\fetch_rife.py
```

That pulls upstream's 432 MB release, keeps the six files genaumacher uses (17 MB),
puts them where `genaumacher/interpolator_environment.py` looks, and deletes the
zip. The directory is git-ignored. `--require` additionally exits non-zero
unless the binary actually *runs*, which is what the merge gate uses.

Same shape as `funestra/vendor/libmpv-2.dll`, with one difference worth
knowing: funestra deliberately does *not* give CI its DLL, because fun_time's
hidden-desktop suite covers the real engine. Genaumacher has no second suite, and
windows-latest is the only place a Windows PE can execute — so genaumacher's gate
fetches it and `--require`s it, and that one step is the whole assertion that
the real binary turns these flags into a frame.

**The suite itself never needs it.** The seam-bridge tests drive the pipeline
through a stand-in for the process, so they run on a checkout that never
fetched. A checkout that never fetched still exports clips — normalizing falls
back to its geometric seam — and `genaumacher/interpolator_environment.py` writes
that into `state/genaumacher.log` on the way up, because the fallback is otherwise
silent and the clips are just quietly worse.

## Bump normalize's version when its output changes

Every clip the normalize step writes is stamped with `NORMALIZE_VERSION` from
`genaumacher/normalize_pipeline.py`, and that number is what a later sweep
compares to tell the clips made before a change from the ones made after it.
**Bump it in the commit that changes what the normalize step writes**: a
transform in `normalize_transforms.py`, how `normalize_pipeline.py` builds the
frames or shrinks the file, the encode in `normalize_media.py`, a default in
`normalize_options.py`, or the RIFE build `tools/fetch_rife.py` fetches.

The stamp names the step `clip_postprocess`, its name when the first of those
clips was made, and `NORMALIZE_METHOD` keeps it: a sweep finds the clips by that
name, so renaming it would hide every clip stamped before the rename.

Nothing checks it, and a missed bump fails silently: clips from before and after
the change carry the same number, so the only way left to tell them apart is by
commit. A change that leaves the output as it was (a rename, a refactor) does
not bump it. The near miss that still counts: a default tuned in
`normalize_options.py` alone, which touches no transform and changes every clip.

## Communication rules

- **Answer questions before doing work.** When the user asks questions or raises concerns, respond to each one. Do not silently go off and do a batch of work instead of engaging with the conversation.
- **Don't assume the next step.** Wait for the user to confirm direction before starting work, especially after a check-in or review.

## Testing principles

- **Test through realistic inputs, not mocked internals.** Feed the real thing through the real function, with only the outside world stubbed. `tests/test_main_funestra_prefill.py` builds its status payload from the key set it reads out of the Main Funestra's own `status_fields`, rather than from a fixture in the shape genaumacher happens to want — so the test fails when the producer's format moves, which is the whole reason to have it.
- **Test each resolution path independently.** If a function has a primary path and a fallback, write separate tests proving each works — and that the fallback is not reached when the primary succeeds. `tests/test_fetch_rife.py` does this for the archive: an intact copy already on disk is reused, and `mock.assert_not_called()`-style stubs prove nothing was downloaded.
- **Mock at the boundary, not in the middle.** Patch the I/O (`normalize_media`'s `ffprobe_video`, `read_frames`, `encode_with_ffmpeg`) and let everything above it run for real, as `tests/test_normalize_pipeline.py` does. Stubbing the intermediate logic tests the stubs.

## Repo-specific gotchas

- The test environment is the project `.venv`, not system Python or Conda.
- `sessions/` and `raw_clips/` are at the project root (not inside `genaumacher/`). They are gitignored runtime data.
- A test that runs an export or the normalize step into `flicks_dir()` writes that flick's metadata sidecar for real. Ask for the `library` fixture, which gives the test a library under tmp; without it the sidecar lands in the library this machine's Haglio settings name.

## Test fixtures must be fabricated, never copied from the real library

Every fixture value that stands in for library data — a video title, a filename,
a performer or studio name, prompt text — must be **invented**. Never paste a
real one out of the media library to make a test feel realistic.

This is not a style note. It is the single thing that has actually leaked private
data into these repos: an agent writing a test reached for a real filename or
performer name because it was handy, and it rode into a public commit. Nothing in
the app's *design* pulls library text into source — the library lives outside
every repo, read at runtime through the git-ignored overlays — so this habit is
the only remaining path for a real name to get committed, and the only thing
stopping it is you following this rule.

Do not lean on the sanitize guard to catch it. `app_support.sanitize` fails
the suite when a **known** blocked term appears in the tracked tree, but a brand-
new performer name it has never seen passes every check and lands. The guard is a
backstop for names already known; it cannot see the next one.

So fabricate fully. Use `Jane Doe`, `Example Studio`, `scene one`, the
`alpha`/`beta`/`gamma` act placeholders the committed `content.example.json`
already uses. The near miss that still counts: taking a real filename and
changing a character or two — it is still that clip, still that performer. Make
it up from scratch, don't lightly edit a real one.

## Judging a branch before it lands

Every checkout carries `launch_preview_branch.vbs`, rendered from its spec in
`pyproject.toml`: it runs that worktree's code on the primary checkout's venv,
copying the primary's `content.local.json` in first, beside any Genaumacher he has
open. Hand him a claunch link to it. A branch that needs a sibling version the
venv does not hold gets a launcher of its own in the worktree's git-ignored
`state/` that also puts checkouts of those versions first on `PYTHONPATH`.

## Landing — GitHub merge queue, not local ff-merge

This repo is public at `github.com/haglio/genaumacher` with a merge-queue ruleset on
`main`, so the global "ff-merge into the primary checkout under
`.git/agent-merge.lock`" flow does NOT apply here:

- **Land through a pull request.** From your worktree: commit, `git fetch origin
  && git rebase origin/main`, `git push -u origin <branch>`, then
  `gh pr create --fill`. Auto-merge arms itself; the queue rebases your PR onto
  `main`, runs the required check, and merges it when green. Don't ff-merge into
  the primary checkout, don't push `main` directly, and never force-push `main`.
- **The `.git/agent-merge.lock` is retired here** — the GitHub queue serializes.
- **The production updater moves the primary checkout; never pull it or install
  into its venv yourself.** `main` advances only on origin (via the queue), and
  app_support's production updater brings the primary checkout and its venv up
  to it, the libraries it pins first, as soon as nothing of his runs from it;
  every launcher here does the same just before it starts Genaumacher. So a change
  reaches him the next time he opens Genaumacher, and worktrees update with
  `git rebase origin/main`.
- **A red required check** (`.github/workflows/merge-gate.yml`) can't land.

Everything else in the global CLAUDE.md — work in a worktree, green tests before
you push, clean handoff — still applies.
