# Testing the LabConstrictor bridge with Playground

Playground provides small, reproducible tools for checking whether LabConstrictor can start an application, exchange data with a host and recover from failures.

## Scientific applications

For scientific applications to use after testing the bridge, see the [Toolkit application list](https://github.com/CellMigrationLab/LabConstrictor-Tools#applications), which includes [Guess the Condition](https://github.com/CellMigrationLab/GuessTheCondition). A passing Playground test does not validate another application.

## First: run Feature tour

Open Playground from Fiji, Napari or QuPath and select **Feature tour**. Leave the image input unset to use its built-in example.

Check the returned label image, outlines, points, measurements table and message. Repeat with a different threshold. Compare what each host displays with the declared outputs.

A successful Feature tour establishes that these specific paths worked in that host and installation. It is not a general host certification.

## Second: run Check everything

**Check everything** inspects the installed application runtime and optional compute and network capabilities. It may run a numerical benchmark. Read the individual results rather than treating the overall status as a pass/fail verdict for every feature.

### Device checks

Use **List the devices** to inspect PyTorch devices. Use **Run a small test on a device** to exercise the selected device. A device being listed does not establish that all models or scientific tools will run on it.

### Reports

Keep the report JSON with a bug report when useful. Review reports before sharing: file paths and environment details may identify a machine or user.

## Host integration checklist

For each host, record:

- Host version, operating system and installed Playground version.
- Whether the tool list loads and Feature tour completes.
- Whether labels, points, outlines, tables and messages appear in the expected form.
- Whether optional image inputs, channel selection and selected regions behave as expected.
- Whether a second run replaces the outputs marked for replacement.

Do not mark an unsupported host behavior as a pass.

## Stress and failure tests

Playground also has tools for large images, many points, slow progress, deliberate worker crashes, memory pressure and ignored cancellation.

**Save your work before using stress tools.** They are designed to exercise failure handling, not to process scientific data. Run them separately, record which test was used, and check that the host reports the failure and remains usable.

## Interpreting failures

Distinguish between a tool error, a worker crash, a missing application, an unavailable device and a host presentation problem. Collect the error details and shared LabConstrictor log when reporting a reproducible issue.

## Maintainer checks

Update expected outputs and test cases when tool declarations change. Keep device-specific and operating-system-specific results separate. A successful Linux test is not evidence of Windows or macOS compatibility.
