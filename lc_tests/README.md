# Tests of the tools for Napari, Fiji and QuPath

Declarations: `src/labconstrictor_playground_lc_tools/`. The tools run in the app's own environment through the LabConstrictor tools worker.

    mkdir -p lc_tests/fixtures/data
    labconstrictor-tools check --module labconstrictor_playground_lc_tools --pythonpath src
    labconstrictor-tools test  --module labconstrictor_playground_lc_tools --pythonpath src --cases lc_tests/cases.json

The fixtures `settings.json`, `notes.txt`, `measurements.csv`, `square_a.tif` and `square_b.tif` (a 4 x 4 square of 255 in a 32 x 32 image, at rows 4-7, columns 8-11 and rows 14-17, columns 20-23) give the known answers of *Look inside a file*, *Summarise a table*, *Count the pixels above a level*, *Area of the bright region* and *Align the centres of two images*. The cases run every tool once with a normal input, plus the cases that must fail clearly (a device that is not there, a SIMULATED out of memory that raises a labelled `MemoryError` and allocates nothing) or end the worker (a crash). The speed test of `check_everything` needs PyTorch in the environment.

`stress_hang` has no case here: the case runner has no grace-period kill (the hosts do). It is exercised by the host test suites: after Cancel the host must stop the worker within its grace period and leave no process behind.

`stress_real_memory` (real but bounded memory use, at most 512 MB, in a child process) has no case here on purpose: it is opt-in. Run it by hand from a host, or run its unit test with `PLAYGROUND_REAL_MEMORY_TEST=1 pytest tests/test_playground.py -k real_memory`.
