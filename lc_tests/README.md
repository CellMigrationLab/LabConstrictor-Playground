# Tests of the tools for Napari, Fiji and QuPath

Declarations: `src/labconstrictor_playground_lc_tools/`. The tools run in the app's own environment through the LabConstrictor tools worker.

    mkdir -p lc_tests/fixtures/data
    labconstrictor-tools check --module labconstrictor_playground_lc_tools --pythonpath src
    labconstrictor-tools test  --module labconstrictor_playground_lc_tools --pythonpath src --cases lc_tests/cases.json

The fixtures `settings.json`, `notes.txt`, `measurements.csv`, `square_a.tif` and `square_b.tif` (a 4 x 4 square of 255 in a 32 x 32 image, at rows 4-7, columns 8-11 and rows 14-17, columns 20-23) give the known answers of *Look inside a file*, *Summarise a table*, *Count the pixels above a level*, *Area of the bright region* and *Align the centres of two images*. The cases run every tool once with a normal input, plus the cases that must fail clearly (a device that is not there, a SIMULATED out of memory that raises a labelled `MemoryError` and allocates nothing) or end the worker (a crash). The speed test of `check_everything` needs PyTorch in the environment.

The tools that have no case here are declared on purpose, each with its reason, in `lc_tests/no_case.json` (`{tool_id: reason}`), the single source: `stress_hang` (no grace-period kill in the case runner) and `stress_real_memory` (opt-in, real memory). A tool with no case that is not listed there fails `tests/test_no_case_declaration.py`, and so does a listed tool that has a case. To run the real-memory unit test: `PLAYGROUND_REAL_MEMORY_TEST=1 pytest tests/test_playground.py -k real_memory`.
