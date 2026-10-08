# Documentation map

Diagnostics versus host integration tests.

The [README](../README.md) is the entry point. Detailed material belongs in the sections below. This map records the intended structure; a named page may still need to be created or updated by the implementation maintainers.

| Section | Intended file | Scope |
|---|---|---|
| Overview and first run | `README.md` | Feature tour, installation and scope of a passing result |
| Tools reference | `docs/TOOLS.md` | Inputs, outputs and purpose of each demo/diagnostic/stress tool |
| Diagnostic report | `docs/DIAGNOSTICS.md` | Checks performed, skipped checks, report files, privacy |
| Host test recipes | `docs/HOST_TESTS.md` | Napari, Fiji, QuPath reproducible runs and expected outputs |
| Stress and failure tests | `docs/STRESS_TESTS.md` | Risks, prerequisites, expected failure behavior and recovery |
| Install and troubleshooting | `docs/INSTALL.md` | Installers, device choices, registration, known platforms |

## Maintenance

Never imply that a passing machine diagnostic certifies the hosts. Code owners should keep expected results and platform coverage in sync with tests.

When changing a tool or host behavior, update the relevant section in the same PR. Prefer one tested example to several unverified ones. Mark unsupported behavior explicitly; do not turn planned features into present-tense claims.
