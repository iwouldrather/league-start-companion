# Development

The [README](../README.md) covers installing and using the Windows app.
Read [AGENTS.md](../AGENTS.md) before changing the project.

## Run from source

Use Python 3.12 on Windows:

```powershell
python -m pip install -r requirements-desktop.txt
python scripts/dev-server.py
```

The development server watches source changes and reloads the guide. Stop it
before manually rebuilding with `python scripts/build.py`.

Edit files in `source/`; `slayer-leveling-guide.html` is generated. The local server
is `slayer-companion.py`, PoB importing is in `pob_import.py`, gem acquisition data
is managed by `gem_acquisition.py`, and tree rendering is in `poe_tree.py`.

## Checks

```powershell
python -m unittest discover -s tests
node tests/test_frontend.cjs
node tests/test_planner.cjs
node tests/test_follow.cjs
node tests/test_character_bar.cjs
node tests/test_tree_navigation.cjs
node tests/test_tree_zoom.cjs
node tests/test_acquisition_ui.cjs
```

Use isolated data folders and ports for manual tests. Never overwrite saved
builds, gem progress or the player's game log.

## Windows releases

Packaging requires local Path of Building Community data containing the tree
version used by `scripts/build-windows.py`. Set `POB_DATA_DIR` if needed.

```powershell
python scripts/build-windows.py
```

The installer is written to `dist/LeagueStartCompanion-Setup.exe`. Installer UI is
in `source/installer.html` and `installer_ui.py`; operations are in
`install_windows.py`. Regenerate the original icon's ICO and PNG with
`python scripts/build-icon.py` after changing its design.

For releases, increment `app_version.py`, build and verify setup, then create a
GitHub release tagged `v<VERSION>`. Upload the installer and its SHA256 checksum
before publishing. Automatic updates accept newer stable releases only, and
verify the installer against GitHub's asset digest and size before launch.

Keep user imports, saves, settings, credentials, caches and generated installers
out of Git. Game assets are bundled into the Windows package, not committed as
standalone source assets. The README screenshot is a rendered example using
an isolated demonstration character.
