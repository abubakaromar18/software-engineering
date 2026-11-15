"""Hypothesis profiles, chosen with HYPOTHESIS_PROFILE=dev|ci|thorough.

dev       fast feedback while editing (default)
ci        more examples, derandomised so a red build is reproducible
thorough  for a nightly run or before a release
"""

import os

from hypothesis import HealthCheck, settings

settings.register_profile("dev", max_examples=100, deadline=None)
settings.register_profile(
    "ci",
    max_examples=500,
    deadline=None,
    derandomize=True,
    print_blob=True,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile("thorough", max_examples=5000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
