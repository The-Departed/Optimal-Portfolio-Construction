"""Run the Monte Carlo portfolio simulation and persist every portfolio. From backend/:

    uv run python -m scripts.run_simulation [--n-portfolios 50000] [--seed 42]

Writes data/processed/simulations/mc_n<N>_seed<S>.csv.gz and .json.
Exit codes: 0 = success, 1 = invalid inputs, data unavailable or a failed check.
"""

import argparse
import sys

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.portfolio import SimulationRequest
from app.services import simulation_service


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Monte Carlo long-only portfolio simulation")
    parser.add_argument("--n-portfolios", type=int, default=settings.monte_carlo_simulations)
    parser.add_argument("--seed", type=int, default=settings.random_seed)
    args = parser.parse_args(argv)
    try:
        request = SimulationRequest(n_portfolios=args.n_portfolios, seed=args.seed)
        response = simulation_service.to_response(simulation_service.run(settings, request), 100)
    except ValidationError as exc:
        print(f"Invalid parameters: {exc}", file=sys.stderr)
        return 1
    except AppError as exc:
        print(f"Simulation unavailable: {exc.message}", file=sys.stderr)
        return 1
    print(f"{response.simulation_id}: {response.n_portfolios:,} portfolios, seed {response.seed}")
    print(
        f"R_f {response.inputs.risk_free_rate:.2%}; "
        f"sample {response.inputs.sample_start} .. {response.inputs.sample_end}"
    )
    for c in response.candidates:
        print(
            f"{c.label:<15} #{c.portfolio_id:<7} return {c.expected_return:.2%}  "
            f"vol {c.volatility:.2%}  "
            f"Sharpe {c.sharpe_ratio:.3f}  "
            + " ".join(f"{w.asset_id}={w.weight:.1%}" for w in c.weights)
        )
    print(f"Frontier approximation: {len(response.frontier.portfolio_ids)} sampled portfolios")
    for check in response.checks:
        print(f"[{check.status:4}] {check.name}: {check.detail}")
    print("Outputs:", *response.output_files.values(), sep="\n  ")
    print(f"SIMULATION STATUS: {response.status}")
    return 1 if response.status == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
