# Data sources

The importer reads the user's installed Path of Building Community data without
executing imported Lua or altering the installation. No game tree sprites are
copied into this repository.

- Export and shared-link formats: [PoB ImportTab](https://github.com/PathOfBuildingCommunity/PathOfBuilding/blob/dev/src/Classes/ImportTab.lua),
  [BuildSiteTools](https://github.com/PathOfBuildingCommunity/PathOfBuilding/blob/dev/src/Modules/BuildSiteTools.lua).
- Base-tree coordinates and orbit conventions: the installed `TreeData` and
  [PassiveTree](https://github.com/PathOfBuildingCommunity/PathOfBuilding/blob/dev/src/Classes/PassiveTree.lua).
- Gem levels and types: installed `Data/Gems.lua` and `Data/Skills`.
- The existing verified Duelist acquisition records retain their individual
  source links in `source/acquisition.json`.
- The all-class offline snapshot in `source/gem-acquisition.json` records
  per-gem source URLs and dates from PoEDB. The quest matrix supplements missing
  vendor rows; individual gem vendor records take precedence. `gem-registry.json`
  stores factual gem identifiers, requirements, colors and variant categories
  extracted from the installed PoB data. No descriptions or game artwork are copied.

Path of Building Community is distributed under its [MIT license](https://github.com/PathOfBuildingCommunity/PathOfBuilding/blob/dev/LICENSE.md).
Path of Exile game data and names belong to Grinding Gear Games. This app is not
affiliated with or endorsed by Grinding Gear Games.

The optional Windows release package bundles local PoB 3.29 tree atlases, class
art and gem/skill metadata for offline use. These assets are not committed to Git.
Python, PyInstaller (with its bootloader exception), Pillow, pythonnet and pywebview
are used under their respective upstream terms.

Vendor prices are factual normal level-1 costs from per-gem PoEDB pages, with URLs
and check dates in `source/gem-costs.json`. Ranger's starting Momentum support is
documented at https://www.poewiki.net/wiki/Momentum_Support .
