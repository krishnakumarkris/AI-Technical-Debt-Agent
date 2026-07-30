"""
All the "magic numbers" used by the debt rules live here, in one place,
so they're easy to tune without hunting through rule code.

These defaults follow commonly cited values from Object-Oriented Metrics
literature (Lanza & Marinescu, Fowler's "Refactoring") - not hard laws,
just sensible starting points for a v1.
"""

# --- Method-level ---
LONG_METHOD_LINES = 30          # method body longer than this -> flag
LONG_PARAMETER_LIST = 4         # more than this many parameters -> flag

# --- Class-level ---
GOD_CLASS_METHODS = 20          # more methods than this -> candidate god class
GOD_CLASS_FIELDS = 15           # more fields than this -> candidate god class
LARGE_CLASS_LINES = 300         # total lines in class -> flag

# --- Coupling (from graph_builder metrics) ---
HIGH_EFFERENT_COUPLING = 10     # depends on more than this many other classes
HIGH_AFFERENT_COUPLING = 15     # more than this many other classes depend on it

# --- Inheritance ---
DEEP_INHERITANCE = 3            # depth-of-inheritance-tree greater than this -> flag

# --- Duplicate code ---
MIN_DUPLICATE_LINES = 4         # ignore trivial 1-3 line methods (getters/setters)

# --- Severity weights, used to compute the overall debt score ---
SEVERITY_WEIGHTS = {
    "low": 1,
    "medium": 3,
    "high": 6,
    "critical": 10,
}
