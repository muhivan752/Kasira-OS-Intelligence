# Native HPP correction, 6 October 2026

The POS detail sheet used a cached FutureProvider and raw quantity multiplication.
A sync could populate SQLite while the sheet still showed an older recipe or no
recipe. The synthetic case 0.1 kg of rice at Rp17 per gram plus an optional Rp500
item displayed Rp501.70 instead of Rp1700.00.

The server now sends pull-only `changes.recipe_hpp` snapshots. Costs use the
existing Decimal/unit helper and recipe filters, with total rounded once to two
decimals. Optional/nonpositive rows contribute zero; archived rows or ingredients
are omitted. Unknown or cross-family units leave the total unavailable instead
of showing a partial subtotal. Ingredient-only deltas refresh dependent recipes
without relying on the recipe's timestamp. Brand scope and RLS apply. Snapshots
are additional payload data, excluded from push handling and pagination cursors.
They contain all display data so dependencies may arrive on different pull pages.

SQLite schema 8 adds recipe estimation, ingredient review flags and a snapshot
table. The one-time HPP backfill flag is set only after all pages commit and all
pages support this protocol. Older backends keep the flag pending. No transaction,
raw recipe quantity, physical stock, mode or existing sync idempotency is reset.
A reactive Drift join updates the sheet after sync, recipe replacement, deletion
or selling-price changes. Offline uses the last synced server calculation.

The detail sheet labels estimates, optional ingredients and incomplete HPP,
retains up to eight decimals in quantities, and explains that the selling-price
spread excludes operating expenses. It uses two decimals for money. The content
scrolls together on short screens and enlarged text; close and retry are real
controls. The existing Sefrekuensi palette and bundled Plus Jakarta Sans remain
the design reference. HPP is the single focal point, coral its accent, with
24px between groups and smaller spacing within related amounts. ENERGY 1,
RHYTHM 1, MOTION 1. The only icon closes the sheet; modal motion is platform
navigation feedback. No new image assets, customer claims or invented content.

Validation:

- 13 backend unit tests (HPP snapshots and existing sync cursor tests) passed;
  every alias in `unit_utils.UNIT_ALIASES` is checked.
- Isolated HTTP/PostgreSQL test passed: full pull at limit 10 over 13 recipes;
  ingredient-only delta refreshes all 13; non-superuser RLS and brand/outlet
  isolation; ignored forged snapshot push; invalid-unit total unavailable;
  raw quantity and physical stock unchanged. Only synthetic fixtures, schema-only
  copy from the runtime database. No merchant payload exported to providers.
- 30 Flutter tests passed; one optional merchant diagnostic skipped. They cover
  empty-to-populated reactive cache, live ingredient-only updates, snapshot before
  recipe during pagination, failed continuation/retry/backfill, old-server
  compatibility, replacement/deletion, SQLite v7 upgrade preserving an unsynced
  order, HPP at 320/375/600/768/1024 with 200% text in both themes, close/Escape,
  retry/empty state, and existing sync/onboarding/login regressions.
- Analyzer: zero errors, four pre-existing warnings, no diagnostic in edited files.
  Logs: `/tmp/selaris-hpp-{flutter-final,analyze-final,native-integration}.log`.
- CI now runs the HPP regression tests before building POS and Dapur releases.

## Delivery gate

PASS R-02/R-15/R-16: native strings contain no em dash or generic CTA; close and
retry name their actual actions. No marketing copy added.

PASS R-03/R-32/R-34: ten size/theme widget cases at 200% text show no overflow;
close has a 48px target; Escape closes, retry reloads. Material controls retain
keyboard focus and theme handling; content remains scrollable.

PASS R-17/R-18/R-23/R-24/R-28/R-36/R-38: only synced data in the product; tests
use explicit synthetic fixtures. No statistics, testimonials, images, links or
FAQ introduced.

PASS R-26/R-27/R-35: close, Escape and retry exercised; provider covers pending,
empty, failure, incomplete and success; all required tests passed before release.

PASS R-33: handwritten source edits via patch/heredoc; Drift generated code via
build_runner. No runtime patch script or source-injection feature.

PASS R-01/R-04/R-06/R-07/R-08/R-09/R-10/R-12/R-13/R-14/R-19/R-22: sheet has
no decorative cards, patterns, badges, gradients or illustrations. Close icon
means close. Typography follows the approved Sefrekuensi merchant identity;
platform modal transition is navigation feedback.

PASS R-05/R-11/R-20/R-21/R-29/R-30/R-31/R-37: established product direction,
one HPP focal point, grouped whitespace, a deliberate coral accent, bundled
brand type, neutral surface. Content follows the actual recipe; no template,
new palette or forced theme.

PASS C-1/C-2/C-3/C-4/C-5: every added element explains recipe cost/provenance,
controls work, data originates at the server, and tested states reflow.

PASS R-25: actual modal Material backgrounds checked in all ten size/theme cases;
onSurface, onSurfaceVariant and coral HPP text all reach 4.5:1. Contrast regression
suite (17 tests) passed.

Read-only runtime sync also matched the recipe API and SQLite/native provider
for all 17 recipes on non-archived products. The archived product is hidden by
the provider as intended. Kopi susu is Rp6254.00 and Egg Tart Rp2178.33. No
merchant operational write or provider/LLM call. Fixture stays under `/tmp`.
The optional runtime test is skipped in CI.

Backend deployed by three targeted file copies and restart of the existing
container, after zero pending HPP requests. Hashes match source. Database and
background health are ok; all four services healthy. Runtime migration 112 and
web deployment unchanged. The isolated QA database/network have been removed.

APK publication is pending explicit approval: automatic approval review rejected
the commit/push to main because the fix request was not considered authorization
to publish the complete patch to the shared branch and release CI. No commit,
push or CI dispatch took place. Live APK remains 1.6.31+198. The planned 1.6.32
metadata is at `/tmp/selaris-hpp-native-version-planned.json`; source version.json
still advertises the available 1.6.31 artifacts. After approval, CI must build
this source SHA, preserve Firebase/release signing, pass HPP tests, and publish
verified artifacts before runtime/public metadata is updated.
