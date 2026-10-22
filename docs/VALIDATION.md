# Validation of 0.1.0-alpha.1

## Reproducible without a vendor license

- Python unit tests use only original synthetic PHP examples and temporary filesystem fixtures.
- Runtime tests verify pointer advancement, empty/scalar/recursive counting, implode argument orders, numeric handling, closure reference arguments and fragment normalisation.
- CLI tests cover read-only planning, apply/repeat/restore, unknown-core refusal, backup location restrictions, simulated write failure, restore refusal after edits and mutation locks.
- Symlink checks run where the test operating system permits creating symlinks.

Initial execution: Windows/PHP 8.4.25 (one symlink test skipped by the operating system), and Linux/PHP 8.4.27 (symlink test supported). The helper suite contains 13 checks. The repository's GitHub Actions workflow is prepared; no GitHub-hosted run is claimed.

## Private licensed-input validation

Performed with PHP CLI 8.4 on an independently supplied official 4.2.5 Suite archive, outside the public project:

- Reference inventory: **1,120 PHP files**.
- Planned application: **386 existing PHP files changed**, plus two original helper files.
- PHP lint on each proposed write before application.
- A second check finds no further changes.
- Restore is checked byte for byte against the original inputs.
- Loading the patched core classes and parsing a synthetic XML document tests the internal XMLParser conflict and callback signatures without connecting to a database.

This does not claim a completed fresh forum installation, HTTP test suite, database upgrade, validation of every bundled application path, or compatibility with all add-ons. Inputs, full diffs, backups and private validation reports are not part of a public release. The results above are a bounded alpha baseline, not a production-readiness badge.
