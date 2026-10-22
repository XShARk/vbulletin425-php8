# vBulletin 4.2.5 → PHP 8 compatibility toolkit

**0.1.0-alpha.1 — experimental; target: PHP 8.4.**

[Documentation française](README.fr.md)

An offline CLI patcher for an independently obtained, licensed vBulletin 4.2.5 copy. It ships original transformation code and SHA-256 fingerprints, **not a vBulletin distribution**. It does not download vendor files or contact any service.

This first version is a foundation for community testing, not a promise that every forum, payment integration or add-on runs on PHP 8. A successful lint or XML test is not a full installation or security audit. See [validation](docs/VALIDATION.md) and [limitations](docs/LIMITATIONS.md).

## Requirements

- Python 3.10+ and PHP CLI 8.1+; use the intended PHP 8.4 binary for application validation.
- A **separate, offline copy** of a licensed vBulletin **4.2.5** installation.
- Independent file **and database** backups. The patcher's backups cover changed files only.
- Keep this utility and all backups/reports outside the forum's public document root.

No Python packages or Composer installation are required. The reference fingerprints cover one official 4.2.5 Suite distribution. Other packaging variants may need additional reviewed profiles.

## Check first — no writes

```sh
python3 vb425_php8.py check --root /srv/forum-copy --php /usr/bin/php8.4 \
  --report /srv/private/php8-check.json
```

The report lists planned changes, missing required files, modified-core conflicts and extra PHP files that are not patched. Vendor download license metadata is normalised narrowly; application code is checked against known fingerprints. An unknown customisation blocks automatic application. There is deliberately no `--force` option.

## Apply to the copy

```sh
python3 vb425_php8.py apply --root /srv/forum-copy --php /usr/bin/php8.4 \
  --backup-dir /srv/private/vb425-backups --report /srv/private/php8-apply.json
```

Every proposed PHP file is linted before the first write. Originals and a manifest are saved in a timestamped backup run. Replacements are atomic per file; handled write failures roll back the files already written. Do not edit the copy concurrently. An interrupted operation can leave a lock; inspect it before removing it, rather than starting another apply.

Run `check` again: a successfully patched, unchanged copy should have an empty `files_to_change` list. The runtime files must remain installed.

## Restore

Use the exact `backup_run` reported by apply:

```sh
python3 vb425_php8.py restore --root /srv/forum-copy \
  --backup-run /srv/private/vb425-backups/RUN-ID
```

Restore checks the backups and current patched hashes before writing. It refuses to overwrite subsequent edits. A prepared backup can recover an interrupted apply when each file still matches either its original or patched hash. Confirm that no process is running before removing an abandoned lock. Restoring files does not restore a database or reverse manual changes.

## What this version changes

- Token-based handling of curly string offsets, bareword array keys and removed `each()` / `create_function()` calls.
- Compatibility helpers for legacy counting, argument order in `implode()`, removed magic-quotes queries and numeric input conversion.
- Narrow core integration for MySQL constants, expected MySQLi error handling, XML callbacks and the internal `XMLParser` name collision.
- Runtime normalisation of existing trusted compiled templates/hook fragments; the template compiler also normalises future output. Database source templates are not rewritten.
- Small stock-core fixes for ambiguous ternaries, an invalid non-loop `continue`, API constants and an implicitly nullable parameter.

The runtime callback helper evaluates trusted administrator-authored code, as the legacy application already does. **Never pass request data to it.** This is compatibility work, not a replacement for vendor security support.

## Database and deployment

Start with a 4.2.5 database. This utility does not perform the official upgrade from an older release, import a dump, change users, alter schema, rewrite content, or change connection encoding. Use the official licensed upgrader separately where necessary.

Review `includes/config.php` yourself: the database driver must be `mysqli` under PHP 8, and the web/CLI extensions and database server must be compatible. Preserve your existing encoding until a separate encoding migration is planned. Credentials and custom configuration are not bundled or rewritten.

Do the full staging checklist in [limitations](docs/LIMITATIONS.md) before any production deployment. The vendor file-integrity checker will report patched files; the patcher does **not** rewrite vendor checksums to hide changes.

## Tests

```sh
python3 -m unittest discover -s tests -v
php tests/runtime.php
```

Set `PHP_BINARY` if `php` is not on PATH. CI runs only original synthetic fixtures; it must not receive a vendor ZIP, license key, real database or private customisations. Private validation can use licensed inputs kept entirely outside this repository.

## Contributing and publication

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [NOTICE](NOTICE). Do not attach licensed source files, SQL dumps, configuration files, cookies, credentials or customer content to issues or pull requests.

Only the utility files belong in a public repository. A release must pass `python3 tools/check_release.py`; the packaging command uses an explicit allowlist. Neither command publishes anything to GitHub.

## Sources

The scope follows the PHP project's [PHP 8.0 incompatible changes](https://www.php.net/manual/en/migration80.incompatible.php) and [PHP 8.4 deprecations](https://www.php.net/manual/en/migration84.deprecated.php). These references describe language changes; they do not certify this tool or vBulletin compatibility.
