# Scope and deployment checklist

This is an experimental compatibility utility. The initial profile is fingerprinted against one official vBulletin 4.2.5 Suite release. It is not an official vendor update or a security certification.

## Not automated

- Upgrading a 4.2.3/4.2.4 database to 4.2.5, schema migration or restoration of a database.
- Installing or updating PHP, configuring web servers, mail, certificates or hosting accounts.
- Auditing or patching third-party PHP files, proprietary add-ons or custom core modifications.
- Testing payments, email, SSO, user permissions, authentication, scheduled tasks or uploads for a particular site.
- Eliminating every warning/deprecation or replacing unsupported external services.
- Supplying vendor files or accepting unreviewed variants through a force flag.

The template/hook compatibility path transforms administrator-authored PHP at runtime. This does not make arbitrary plugin code safe, validate its business logic, replace removed mysql_* database APIs in add-ons, or fix every modern PHP TypeError.

## Required staging checks

1. Restore a separate file/database backup and verify that its version is 4.2.5.
2. Run check, inspect all conflicts and extra files, then apply offline with the intended PHP executable.
3. Verify the actual web PHP version/extensions, mysqli settings and original connection encoding.
4. Exercise guest pages, registration/login/logout/password reset, search, posting/editing, private messages, attachment upload/download and AdminCP template saves.
5. Exercise each installed add-on and relevant scheduled task. Test provider integrations in their supported test environment.
6. Review warnings/fatal errors and confirm that no private data is exposed by application errors or logs.
7. Rehearse deployment and rollback with a fresh copy before scheduling maintenance. Preserve new user data if a rollback is needed after writes resume.

An all-green synthetic CI run does not replace these application and database tests. There is no public licensed-source integration fixture in this repository.
