# VerseVAD on macOS

VerseVAD uses the same Python analysis engines, locked dependencies, research
resources, SQLite projects, and local Streamlit interface on Windows and macOS.
The macOS helpers keep their downloaded setup tool, Python runtime, environment,
and cache inside the ignored VerseVAD folder. They do not need Homebrew,
administrator access, or a separately installed Python.

## Compatibility target

- Apple silicon and Intel Macs running macOS 13 Ventura or newer;
- Python 3.12 managed locally by the pinned `uv` setup tool;
- the two most recent versions of Safari and Google Chrome; and
- a normal local checkout whose path may contain spaces.

Streamlit's official browser policy lists the two most recent Safari and Chrome
versions as supported:
<https://docs.streamlit.io/knowledge-base/using-streamlit/supported-browsers>.
Astral documents macOS installation and managed Python support for `uv`:
<https://docs.astral.sh/uv/getting-started/installation/> and
<https://docs.astral.sh/uv/guides/install-python/>.
Its current platform policy gives Apple silicon and Intel macOS Tier 1 support
and supports macOS 13 or newer:
<https://docs.astral.sh/uv/reference/policies/platforms/>.

The first setup needs internet access to download the pinned setup tool, a
compatible Python build, and the locked packages. Ordinary launch and analysis
then run offline.

## Dependency files

VerseVAD intentionally uses `pyproject.toml` plus `uv.lock` instead of a
separate `requirements.txt`. `pyproject.toml` declares the application's direct
dependencies. `uv.lock` pins the complete cross-platform dependency graph,
including compatible macOS and Windows artifacts. Keep both files in the
checkout.

You do not need to run `pip install`, create a virtual environment, install
Homebrew, or install Python first. `bash setup_macos.command` installs the
pinned project-local setup tool, a managed Python 3.12 runtime, the `.venv`,
and every locked Python dependency before it runs the core diagnostics.
Separately licensed research resources are the only manual installation step.

## First setup

1. Clone or download VerseVAD into a normal user-owned folder, such as
   `Documents/VerseVAD`.
2. Open Terminal.
3. Type `cd `, including the trailing space, drag the VerseVAD folder from
   Finder into the Terminal window, and press Return. This safely enters paths
   that contain spaces.
4. Run:

   ```bash
   bash setup_macos.command
   ```

5. Wait for `VerseVAD setup completed successfully`.
6. Install the desired research datasets at the exact paths in
   [resource-installation.md](resource-installation.md). The datasets are not
   bundled or automatically downloaded because each retains its own terms.
7. Start VerseVAD and use **Run self-test** under **Installation Check**.
   Runtime failures and missing or unsupported research resources are reported
   separately.

Setup checks the core application with invented local fixtures, so it can
finish before separately licensed research files are installed. It never
assigns substitute data to a missing resource.

## Update an existing clone

You do not need to delete the Mac installation or reinstall its lexicons and
projects. Close VerseVAD, open the repository in GitHub Desktop, select `main`,
click **Fetch origin**, and then click **Pull origin**. Alternatively, from
Terminal in `~/Documents/VerseVAD`, run:

```bash
git status
git fetch origin
git pull --ff-only origin main
bash setup_macos.command
```

Read `git status` before pulling and do not discard tracked local edits. The
setup helper reuses its local environment and cache, changing packages only
when the locked dependencies require it. Ignored research resources, projects,
exports, and backups remain in place. If `git status` says the folder is not a
Git repository, it was probably downloaded as a ZIP and needs the one-time
migration in [updating.md](updating.md).

## Start and stop

After setup, double-click `start_versevad.command` in Finder. You can also run:

```bash
./start_versevad.command
```

The launcher opens the Mac's default browser at
`http://127.0.0.1:8501`. To use a different supported browser, keep the
launcher open and paste that address into current Safari or Chrome. The
`127.0.0.1` address is accessible only from the same computer.

When finished, close the browser tab and then close the launcher window or
press Control-C in it. One-text results must be downloaded before closing;
corpus projects remain in the ignored local `projects` database.

## Diagnostics

Double-click `diagnose_macos.command`, or run:

```bash
./diagnose_macos.command
```

The full diagnostic reports the application runtime, synthetic calculations,
and every configured research resource. A missing dataset can fail its own
line without making an installed independent module unusable.

## macOS permission and security messages

If Terminal reports `Permission denied`, return to the VerseVAD folder and run:

```bash
chmod u+x setup_macos.command start_versevad.command diagnose_macos.command
```

Then retry the launcher. The setup normally performs this step automatically.

If macOS blocks a downloaded `.command` file, verify that the checkout came
from the canonical VerseVAD repository. Running
`bash setup_macos.command` from Terminal is the deterministic first-run path and
does not require disabling Gatekeeper globally.

If VerseVAD was copied from Windows or moved from another Mac, rerun
`bash setup_macos.command`. It detects an incompatible or stale `.venv` and
rebuilds only that ignored, disposable environment. Research resources,
projects, exports, and source files are not removed.

## Safari and Chrome troubleshooting

- Use a current browser. Streamlit does not promise fixes for unsupported older
  browser versions.
- Keep the launcher window open; the browser page is only the client for the
  local Python process.
- If the page is blank or stale, try a private window or a hard refresh. In
  Chrome on macOS, use Command-Shift-R.
- If the default browser does not open, manually visit
  `http://127.0.0.1:8501` in Safari or Chrome.
- If port 8501 is already in use, close older VerseVAD launcher windows before
  starting another one.
- Preserve the complete Terminal message when reporting a startup failure.

The interface includes explicit Safari-safe text sizing, scrolling, sticky
position fallbacks, narrow-screen wrapping, input contrast, button contrast,
and reduced-motion behavior. Automated tests cover the platform-neutral
launch contracts and responsive CSS. Final release acceptance should still
include a brief run on real Apple hardware in both Safari and Chrome because a
Windows development machine cannot execute Safari or validate macOS
Gatekeeper behavior.

## Real-Mac acceptance checklist

After cloning the finalized commit onto a Mac:

1. Run `bash setup_macos.command` and confirm the core diagnostics pass.
2. Double-click `start_versevad.command` and open all four workspaces in current
   Safari.
3. In **Single Poem**, paste a short invented text, run a small available
   analysis, switch among Classic, Dark, and one color theme, and download one
   CSV or DOCX.
4. Resize the browser from a wide MacBook window to a narrow split-screen
   window. Confirm the header and workspace choices wrap, inputs remain
   readable, tables scroll inside their own region, and the page itself has no
   horizontal scrollbar.
5. Repeat steps 2-4 in current Chrome.
6. Run `diagnose_macos.command`; photograph or copy any `FAIL` line.

This is the only remaining platform-specific acceptance step. It tests the
actual macOS shell, Gatekeeper state, Safari engine, Chrome build, fonts, and
window manager that cannot be reproduced faithfully on Windows.
