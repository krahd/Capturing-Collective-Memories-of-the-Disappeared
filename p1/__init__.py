"""P1 research architecture primitives.

P1 is intentionally separate from the disposable P0 prototype.  The modules in
this package are research-architecture code whose invariants are directly
measurable for the Computers journal article.
"""

from .contamination import CONDITIONS, run_case, run_suite

__all__ = ["CONDITIONS", "run_case", "run_suite"]
