# LabConstrictor Playground

**Test LabConstrictor installations and host integrations.**

Playground has two jobs:

1. **Can this installation run its tools?** Check the machine, application worker, available GPU libraries and a small numerical benchmark.
2. **Does a host handle the tools correctly?** Exercise images, regions, channels, tables, points, outlines, progress and deliberate failure cases from Napari, Fiji or QuPath.

A passing machine check does **not** establish that the Fiji, Napari or QuPath integrations work.

![LabConstrictor Playground](app/logo/logo.png)

## First run: Feature tour

Open Playground from a supported LabConstrictor host and select **Feature tour**.

You can leave the image input unset. Playground makes a small test image, segments its blobs and returns:

- a label image and object outlines;
- points at object centres;
- a measurements table;
- a short message describing the result.

Change the threshold or minimum object size and run again. This exercises the host's controls and result handling without downloading microscopy data. You can also supply your own image, choose a channel where the host supports it, or use a selected region.

**Feature tour is a functional example, not a validated biological segmentation method.**

## Check this installation

Run **Check everything** to inspect the computer and the application's runtime. It reports machine information, writable paths, the worker, GPU utilities and libraries, and—if enabled—a small CPU/GPU numerical benchmark. An optional network check probes package and model download sites.

The result includes a readable summary, a details table and a `report.json` file. A benchmark figure is also written when timing data are available.

A warning or failure should explain what was checked and what to try next. If a probe cannot run, that is not evidence that the missing component works.

The checks are built on the Toolkit's reusable `labconstrictor_tools.diagnostics` module. Playground also looks for installation-log information about CPU/GPU package choices.

### What a passing report means

A passing report is evidence that the **specific checks it ran** succeeded on that machine. It is not a certification of the installation, proof that a scientific tool is accurate, or a full test of all three graphical hosts.

For host integration, use **Feature tour**, the other example tools and the host-specific tests. Include the host name, operating system and application version when reporting an issue.

## Other tools

| Tool | What it exercises |
|---|---|
| **List the devices** | Which PyTorch devices are available to the application |
| **Run a small test on a device** | A dependent device dropdown and actual computation on the selected device |
| **Make test data** | Reproducible files with channels, RGB, labels, time-lapse and points |
| **Stress: a big image** | Large image results and host memory handling |
| **Stress: many points** | Large point layers and tables |
| **Stress: slow run with progress** | Progress display and cooperative cancellation |
| **Stress: crash the worker** | Host recovery after an intentional worker crash |
| **Stress: no memory** | Failure reporting under simulated memory exhaustion |
| **Stress: ignore Cancel** | Whether the host eventually terminates an unresponsive worker |

**Do not use the stress tools on unsaved work.** Some deliberately crash a worker, allocate substantial memory or ignore cancellation. Start with Feature tour and the diagnostics; use stress tests only when checking host behavior.

## Install

Get the installer for your system from [Releases](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases).

Installers target Windows, Linux and Apple Silicon Macs; **Intel Macs are not supported**. Availability of a release does not imply that every GPU or host combination has been tested.

The installer sets up the application's Python environment and registers its tools. An NVIDIA installation may attempt a CUDA-enabled PyTorch build and fall back to CPU packages if installation fails; Playground's installation-log check reports that decision when the log is available.

To use the tools in a graphical host, install the corresponding integration:

- [Napari plugin](https://github.com/CellMigrationLab/napari-labconstrictor)
- [Fiji bridge](https://github.com/CellMigrationLab/LabConstrictor-Fiji)
- [QuPath extension](https://github.com/CellMigrationLab/LabConstrictor-QuPath)

From the application's Python interpreter, you can run the diagnostics without a GUI:

```bash
<install-folder>/bin/python -m labconstrictor_tools run LabConstrictorPlayground check_everything
```

The interpreter path differs on Windows. Use the executable inside the installed Playground environment.

## Report a problem

Start with **Check everything**, then try **Feature tour** in the host where you saw the problem. Include the steps to reproduce it, the operating system, host version and the `report.json` file when filing an issue.

A diagnostic report can contain machine and installation details. **Review it before sharing publicly**, especially paths, usernames or environment information.

For more detail, see [Bridge testing with Playground](docs/TESTING_THE_BRIDGE.md).

## Applications you can try

These are separate scientific applications, not tools bundled with this bridge. Install an application and its LabConstrictor tool registration before expecting it to appear in Fiji, Napari or QuPath.

- [LabConstrictor Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground) — synthetic images, segmentation outputs, installation checks and host integration tests. [Installers](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases).
- [NucleiSky](https://github.com/CellMigrationLab/NucleiSky) — registration of microscopy images using nuclei positions. [Desktop installation](https://github.com/CellMigrationLab/NucleiSky/blob/main/.tools/docs/download_executable.md). Its repository documents Fiji integration; verify the installed version exposes the required tools.
- [VLab4Mic desktop application](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic) — fluorescence microscopy simulations and image comparison. [Installation guide](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic/blob/main/.tools/docs/download_executable.md). Its repository documents Napari and Fiji bridge workflows.
- [CellTracksColab desktop application](https://github.com/CellMigrationLab/CellTracksColab_LabConstrictor) — cell-track analysis. [Desktop installation](https://github.com/CellMigrationLab/CellTracksColab_LabConstrictor/blob/main/.tools/docs/download_executable.md). Check the installed application's declared tools before assuming a particular host workflow is available.
- [Guess the Condition](https://github.com/CellMigrationLab/GuessTheCondition) — blinded classification of microscopy images to test whether experimental conditions can be distinguished across biological repeats. [Desktop installers](https://github.com/CellMigrationLab/GuessTheCondition/releases) and [Colab notebook](https://colab.research.google.com/github/CellMigrationLab/GuessTheCondition/blob/main/notebooks/GuessTheCondition/GuessTheCondition.ipynb). Its repository documents five bridge tools for Napari and Fiji.

**Compatibility is tool- and host-specific.** An application having a desktop installer does not by itself establish that every analysis function is exposed through the bridge. Use `labconstrictor-tools list` to inspect the installed tools.

## For developers

The scientific/test functions live in `src/labconstrictor_playground/`; the declarations exported to hosts live in `src/labconstrictor_playground_lc_tools/`. They use the same typed API as any other LabConstrictor application.

The test cases are in `lc_tests/` and the Python tests in `tests/`. You can validate the declarations with:

```bash
labconstrictor-tools check --module labconstrictor_playground_lc_tools
labconstrictor-tools test --module labconstrictor_playground_lc_tools --cases lc_tests/cases.json
```

The reusable machine and GPU probes are implemented in [LabConstrictor Tools](https://github.com/CellMigrationLab/LabConstrictor-Tools), not duplicated here. Playground adds the installer-specific checks and deliberately difficult example tools.

Built using the [LabConstrictor](https://github.com/CellMigrationLab/LabConstrictor) application template.
