# Security Policy

## Supported Versions

This project is under active development. Security fixes are applied to the
current `main` branch and the latest released version, when a release exists.
Older snapshots and forks are not supported.

| Version | Supported |
| --- | --- |
| Current `main` / latest release | Yes |
| Older versions | No |

## Reporting a Vulnerability

Please do **not** publish exploit details, credentials, private data, or a
working proof of concept in a public issue.

Contact the maintainer through the GitHub account
[@ankit02327](https://github.com/ankit02327) and request a private channel for
the report. If GitHub's **Report a vulnerability** option is available in this
repository's Security tab, prefer that private reporting flow.

Include enough information to reproduce and assess the issue:

- the affected version or commit;
- the affected endpoint, component, or file;
- clear reproduction steps;
- the expected and observed behavior;
- the security impact and any known prerequisites;
- a minimal proof of concept when it can be shared safely.

## Response Expectations

The maintainer will acknowledge a received security report as capacity allows,
confirm whether it can be reproduced, and coordinate disclosure after a fix is
available. Please allow time for investigation before publishing details.

## Scope

Reports about authentication, input validation, secret exposure, dependency
vulnerabilities, unsafe file access, command execution, or data leakage are
especially useful. General bugs without security impact should use the normal
issue tracker.
