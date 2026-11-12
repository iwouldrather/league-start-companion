# Working on this app

This folder is the permanent app and Git repository. Apply future updates here.
Preserve `slayer-purchases.json`; it is user state and must never be committed
or replaced by sample data. Do not alter the user's game log for testing.

For guide changes, edit `source/` and run `scripts/build.py`. The root HTML is
the generated runnable guide. Runtime server code is `slayer-companion.py`.
The normal launcher runs `scripts/dev-server.py`, which rebuilds source changes
and restarts runtime changes automatically. Avoid manual builds while a watcher
is rebuilding. A direct HTML edit triggers browser reload but can be overwritten
by the next source build. Make lasting guide changes in `source/`.
PoB import parsing and saved guide generation live in `pob_import.py`. Keep
`builds/` out of Git; it contains user imports. Preserve saved builds and character purchases when changing imports.
The app shell has no bundled guide; the library is the empty state. Only fetch supported build-sharing
URLs, never execute imported code, and flag unverified acquisition/tree data.
Class-aware acquisition lives in `gem_acquisition.py`; bundled gem and source
snapshots are in `source/gem-registry.json` and `source/gem-acquisition.json`.
Use `scripts/update-gem-data.py` for refreshes. Test every current gem against
all seven classes; do not equate Trarthan gems with Divine Font variants or
free quest rewards with vendor stock. Check generated-page syntax after builds.
Use `tests/` for meaningful parser, persistence and HTTP checks.

Keep log processing local and read-only. Do not add game inputs, memory reads,
client modifications or log uploads. Preserve the no-scroll layout at
2560x1300 and 2048x1050. Use a separate port for test servers if the user's
companion is running. Close only agent-started test servers.

Windows packaging uses desktop.py, install_windows.py and scripts/build-windows.py.
Keep build/ and dist/ ignored and never bundle user imports, progress or settings.
Keep resources separate from the installed user-data folder and retain saves on
uninstall. Test installer actions only with an isolated --test target. Unknown
gem prices must be labelled unverified rather than guessed.

Installer UI is source/installer.html and installer_ui.py. Keep the uninstaller
standalone (exclude installer_ui when freezing it). One-file uninstall workers
must start with a reset PyInstaller environment and wait for the bootloader parent,
not just the Python child, before removing the original executable. Preserve
custom install locations and shortcut choices during automatic updates.

Keep the Windows AppUserModelID in windows_identity.py stable and identical for
the running app and its shortcuts. Use versioned icon resources to avoid stale
shell icons. Refresh only existing taskbar links whose target matches this app;
never pin, unpin or reorder the user's taskbar. Test shortcut changes in isolated
folders with mocked shortcut locations.
