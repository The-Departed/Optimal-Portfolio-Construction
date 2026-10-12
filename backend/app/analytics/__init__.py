"""Pure financial calculations (NumPy / pandas / SciPy / statsmodels).

Modules are added in the phase that implements them, not as empty stubs:

- ``conventions``, ``returns``, ``statistics``,
  ``covariance``, ``risk_free``                     Phase 3
- ``capm``                                          Phase 4
- ``portfolio_metrics``, ``monte_carlo``,
  ``efficient_frontier``                            Phase 5
- ``optimization``                                  Phase 6

Rules: functions here are side-effect free, take arrays/frames ordered by
``app.domain.assets.ASSET_IDS`` and never perform I/O or HTTP concerns.
"""

ANALYTICS_VERSION = "3.0.0"
