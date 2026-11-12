# League Start Companion

Your permanent local Path of Exile leveling guide and log companion.

## Run

Double-click **Start Slayer Companion.bat**. The guide opens at
http://127.0.0.1:8766/. Keep the companion window open while playing.
Close the previous companion before starting this copy. Refresh an existing
browser tab after restarting. No downloads are needed for future local edits.

The launcher enables live updates. Saving changes in `source/` rebuilds the
guide and reloads the browser automatically, usually within a few seconds.
Changes to `slayer-companion.py` restart the local server automatically.
Reloads preserve your browsing/following mode and current milestone; bought
gems stay in the local save file. Close an open details dialog to let a waiting
update finish. Failed builds keep serving the previous guide and print the
error in the companion window. Changes to the launcher or watcher itself need
a manual restart.

The launcher uses the existing Python bundled with Codex, then falls back to
`py -3`. The server uses Python's standard library; live rebuilding also needs
Pillow, which is present in the bundled Python on this computer.

## Saved purchases

Check the boxes beside gems you have obtained. **My gems** lets you review all
gems or choose the character. Each character has separate saved purchases.
Checks apply across milestones and remove owned gems from live reminders.
They track gem types, not quantity, quality or level.

The app creates **slayer-purchases.json** in this folder. This file is excluded
from Git. Keep it when moving or updating the app. Offline HTML mode uses
separate browser storage; use the companion address for the shared disk save.

## What the log knows

The app receives recorded level-ups and area entries through a local event
stream, with polling as a fallback. Click the status for timestamps, vendor
reminders and upcoming gem use-levels. Clicking a milestone lets you browse
temporarily; auto-follow resumes when you reach the next milestone. **Resume
live** returns immediately. Explicitly pausing in the status dialog stays paused
until you resume. App reloads preserve these settings.

Character identity and level reflect the last level-up event. Character
switches can remain undetected until another level-up. The log does not verify
quests, gem ownership, equipment, passives or Lab completion. Milestones come
from your reviewed PoB imports.

## Buy next

The persistent shopping panel belongs to your character, independently of the
tab you are viewing. It shows missing gems for the planning milestone and the
next milestone with gems still to collect. Completed future gem steps are skipped.
Bought gems leave the list; use **Undo** or **Manage / reset** to change a previous check.
The panel follows the recorded level by default. **Planning from** lets you
choose another point without changing the links or tree on the right.
Long lists show a screen-sized preview and an **All remaining gems** button for the rest.

## Local development

- `slayer-companion.py`: local server, log reader and purchase persistence.
- `source/`: page template, styles, interactions and shared gem data.
- `scripts/build.py`: rebuilds `slayer-leveling-guide.html` from those sources.
- `scripts/dev-server.py`: watches saved changes and manages the local server.
- `tests/`: log parsing, persistence and endpoint tests.

Rebuild with `python scripts/build.py` (requires Pillow; see
`requirements-build.txt`). Run tests with `python -m unittest discover -s tests`.
Shopping planner checks run with `node tests/test_planner.cjs`; follow-mode checks
with `node tests/test_follow.cjs`. Run `node tests/test_frontend.cjs` after rebuilding
to check the JavaScript in the generated page.
The rendered HTML is checked in so running the guide never requires a build.
Edit source files and rebuild when changing the guide.

The default log is configured in `DEFAULT_LOG` in `slayer-companion.py`.
You can override it with `--log`; `--port` changes the local port.

## Privacy and boundaries

The app reads the log without changing it. It listens on 127.0.0.1 only and
serves only the guide, extracted level/area state and your saved gem checks.
It does not expose chat, upload logs, send game inputs, read game memory,
modify the client or connect to game servers.

[GGG third-party policy](https://www.pathofexile.com/developer/docs#policy).
This product is not affiliated with or endorsed by Grinding Gear Games.

The source is kept in the private GitHub repository league-start-companion.
Character progress and saved imports are excluded from Git.

## PoB importer (feature/pob-importer)

Open **Builds / Import PoB** in the top bar. Paste an `https://pobb.in/…` share
link, a PoB export code, or PoB XML. Review the included skill sets, starting
levels, passive trees and equipment sets, then choose **Generate & open guide**.
Saved imports appear in the same dialog. There is no bundled build. Opening the
app selects the most recently created saved guide; **All saved builds** opens
the library home. With no saved builds, the home screen offers your first import.

The review proposes exact title matches (or a shared set when only one exists).
Ambiguous tree matches must be chosen explicitly. Levels must increase; exclude
same-level alternatives or generate them as separate guides. Level-100 variants
are initially unchecked in builds with multiple sets. A single endgame setup
generates one reference page; it does not invent leveling steps.

PoE 1 exports are supported. Build data and drafts are saved under `builds/`,
excluded from Git. Owned gems remain separate in `slayer-purchases.json` and
carry across guides for the same character. Importing a code does not upload it;
importing a link downloads only its public export from pobb.in.

Tree geometry and gem requirements are read from the installed PoB Community
data. Override `POB_DATA_DIR` if it is installed elsewhere. Missing tree versions
are flagged. The tree uses native PoE node icons and frames from the installed
PoB assets, with clickable stats and selected mastery descriptions. Changes is
the default: blue nodes are new, gold nodes remain, red nodes were removed. Full
shows the current allocation. Ascendancy has its own compact node diagram.
Game artwork belongs to Grinding Gear Games; tree data/assets are sourced through
[Path of Building Community](https://github.com/PathOfBuildingCommunity/PathOfBuilding). Cluster expansions and Timeless transformations
are not reconstructed, and no damage calculation is performed. Long socket lists
remain accessible through their panel rather than being silently discarded.

The importer supports all seven PoE 1 base classes and all 821 gem variants in
the bundled PoB registry. Item-granted skills resolve from the installed PoB
effect records and stay out of gem purchase lists. Names, gem IDs, skill IDs
and variant IDs are resolved without confusing active Barrage with Barrage Support.

The offline acquisition snapshot covers early class vendors, starting gems,
free quest rewards, Siosa and Lilly. Click a gem to see alternative sources and
extra unlock requirements. Transfigured, Trarthan, Vaal, awakened and exceptional
gems are classified separately; they are not treated as campaign purchases. Entries
without a campaign source are labelled special acquisition rather than assigned
an invented vendor. Unknown future gems remain visible and flagged.

The snapshot uses normal PoE 1 campaign rules, not PoE 2 or Ruthless vendor rules.
Use `python scripts/update-gem-data.py` to refresh data. It caches individual
PoEDB gem records; `--refresh` downloads them again. The current snapshot and gem
registry are checked into Git, so normal imports work offline after pasting a
code. Saved guides receive updated acquisition data when reopened without
changing their reviewed milestones, trees, equipment or purchases.

Unlabelled milestones receive editable level estimates using PoB’s allocated-point
and campaign quest-reward heuristic. Class starting nodes and ascendancy points
are excluded. Build labels take precedence. Quest rewards, bandit choices and
bonus points can change the actual character level; estimates are not exact
unlock levels. Duplicate or missing levels highlight the row to fix.

## Progress and build management

Use **Undo** at the bottom of Buy next to reverse the last saved gem change.
**My gems** (or **Manage / reset**) lets you uncheck individual gems or choose
**Reset all gem progress…** for the selected character across every guide.
Reset asks you to confirm in the panel and can itself be undone. The last 30
changes per character are saved locally, including across app restarts. Other
characters and recorded game levels are unaffected. The offline HTML stores its
own progress and undo history in the browser.

Under **Builds / Import PoB**, use **Rename** to edit an imported guide's name or
**Remove** to take it out of the library. Removed guides can be restored from
**Recently removed**; their files are kept in `builds/removed/`. Removing the open
guide returns to the build library. Gem progress stays with the character.

The passive-tree Changes view keeps the complete previous/current allocation in
view: retained nodes are gold, additions blue and removals red. Mouse-wheel zoom
follows the cursor; drag to pan and use **Reset** to fit the tree again. The enlarged
tree popup also supports wheel zoom. Popups close when clicking their backdrop.
Gem-row hover covers the checkbox and details area with a subtle blue highlight.
The layout is checked at 1080p, 1440p, ultrawide and 4K screen sizes.

## Installed Windows app

The release installer creates a standalone Windows 10/11 x64 app, a Start menu
shortcut and an Apps & features uninstall entry. Python and Codex are not needed.
Microsoft Edge WebView2 Runtime is required:
https://developer.microsoft.com/en-us/microsoft-edge/webview2/

Builds, progress and settings live under `%LOCALAPPDATA%/LeagueStartCompanion`,
separately from installed binaries, and are retained on uninstall. **App settings**
lets you choose the read-only Client.txt, open that folder, or copy existing
companion saves. Copying skips existing destination files and leaves the source
folder untouched.

The release bundles PoB 3.29 tree assets and gem/skill metadata for offline use.
Other tree versions need matching installed PoB data; missing versions are flagged.
Game artwork and generated binaries are excluded from Git. The installer is unsigned.

Build on Windows with `pip install -r requirements-desktop.txt`, then
`python scripts/build-windows.py`. Output goes to `dist/`. Source development
continues to support the existing launcher.

### Updates

From version 0.5.0, the installed app checks public GitHub releases at startup and
every four hours. Newer stable Windows installers download in the background and
are checked against GitHub's SHA256 digest and asset size. A top-bar button appears
when ready: **Restart to update**. The installer waits for the app to exit, updates
the same location, and reopens it. It never closes the app without that click.
Builds, progress and settings stay in the separate data folder. No GitHub sign-in
or token is needed. App settings also offers **Check for updates** to retry offline
or failed checks, and **Install downloaded update…** as a manual fallback.
Older installations need to run the 0.5.0 installer once to gain automatic updates.

Release maintainers: build the Windows installer, publish a public GitHub release
tagged `v<VERSION>` matching `app_version.py`, and attach the setup executable and
its SHA256 checksum. Publish only after uploads finish; the app requires GitHub's
asset digest before accepting an update. Drafts and prereleases are ignored.
Never include user data or credentials in release assets. Checks use Windows'
verified TLS and only allow GitHub release hosts; downloaded files are rechecked
before launch. Checksums do not replace Windows publisher signing; setup remains unsigned.

## Siosa prices and early Momentum

Siosa options show normal level-1 vendor costs in the shopping list and gem details.
`source/gem-costs.json` records each price's source and check time; refresh it with
`scripts/update-gem-prices.ps1`. Unavailable prices say **Cost not verified**, never
zero/free. There are 396 verified entries; Arctic Armour has no verified price in
this snapshot, while removed Earthbreaker is marked legacy rather than sold by Siosa.

When Momentum is enabled in a first setup starting at level 1 for a non-Ranger,
the guide offers an optional Ranger mule via the starting chest and shared stash
in the same league/mode. Ranger builds retain their own direct starting route.

## Independent passive checkpoints

The passive tree has its own previous/next arrows and checkpoint picker. It follows
the selected guide step until you choose a tree checkpoint, then keeps that preview
while gems, equipment and ascendancy stay on the guide step. **Match guide** resumes
following. The preview is remembered per saved build in the browser/app profile.
Changes still compare the selected tree with its preceding PoB checkpoint; notables,
masteries, node details and the enlarged tree use that same selection. These controls
are also available in the scrolling layout on smaller windows.
