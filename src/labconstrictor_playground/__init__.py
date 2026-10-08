"""LabConstrictor Playground: check an installation (machine, worker, GPU) and try every feature of the tools bridge.

    from labconstrictor_playground import check_everything, make_test_data
"""

__version__ = "0.1.0"

from .checks import check_everything, install_log_probe, write_report
from .data import KINDS, make_test_data

__all__ = ["KINDS", "check_everything", "install_log_probe", "make_test_data", "write_report", "__version__"]
