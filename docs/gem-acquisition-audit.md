# Gem acquisition audit — 12 November 2026

Reviewed all **823 catalog gems/effects across seven classes (5,761 combinations)**.
Refetched all **466 ordinary-gem acquisition pages** with no fetch failures, and
cross-checked the complete class-by-class quest vendor matrix.

Corrected **179 class/gem routes across 94 gems** compared with v0.9.3. This
includes missing earlier purchases, incorrect NPC/act combinations, and the
universal Faster Casting unlock from the official 3.29 patch notes.

The refresh now merges class-specific vendor evidence for every ordinary gem,
not just gems without any vendor entry. Explicit Siosa entries are preserved;
quest rewards are not converted into purchases. Existing saved guides refresh
acquisition data automatically without replacing purchases or tree allocations.

## Limits

This is a source-data audit, not an in-game purchase test of every gem.
Per-gem pages and the vendor matrix can disagree or lag the current patch.
Official patch corrections take precedence where identified. Special variants
are checked for exclusion from campaign vendors; their exact league/drop sources
were not independently reverified. Seven entries have no campaign vendor and
retain explicit special-acquisition guidance: Block Chance Reduction, Dark
Bargain, Detonate Mines, Elemental Penetration, Item Quantity, Portal, Quickstep.

## Evidence and reproduction

- https://poedb.tw/us/Quest and each gem page linked in the snapshot
- https://www.pathofexile.com/forum/view-thread/3985332
- `gem-acquisition-audit.json` records every changed route and summary counts.
- Refresh: `python scripts/update-gem-data.py --refresh`
- Validate/export: `python scripts/audit-gem-data.py`

The export contains the resolved earliest route for every gem/class, its use
level, source link, and any acquisition warning.
