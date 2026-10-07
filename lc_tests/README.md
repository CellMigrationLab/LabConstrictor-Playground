# Tests of the tools for Napari, Fiji and QuPath

Declarations: `src/labconstrictor_playground_lc_tools/`. The tools run in the app's own environment through the LabConstrictor tools worker.

    mkdir -p lc_tests/fixtures/data
    labconstrictor-tools check --module labconstrictor_playground_lc_tools --pythonpath src
    labconstrictor-tools test  --module labconstrictor_playground_lc_tools --pythonpath src --cases lc_tests/cases.json

The cases run every tool once with a normal input, plus the cases that must fail clearly (a device that is not there, no memory) or end the worker (a crash). The speed test of `check_everything` needs PyTorch in the environment.

`stress_hang` has no case here: the case runner has no grace-period kill (the hosts do). It is exercised by the host test suites: after Cancel the host must stop the worker within its grace period and leave no process behind.
