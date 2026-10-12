import { Card } from "@/components/common/Card";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useAssetUniverse } from "@/hooks/useAssetUniverse";
import type { AssetClass } from "@/types/api";

const CLASS_LABEL: Record<AssetClass, string> = {
  equity: "Equity",
  government_bond: "Gov. bond",
  gold: "Gold",
};

export function AssetUniverseTable() {
  const { data, isPending, error } = useAssetUniverse();

  return (
    <Card
      title="Investment universe"
      description="Eight portfolio assets in canonical order, with identifiers verified during data acquisition."
    >
      {isPending && <LoadingState label="Loading asset registry…" />}
      {error && <ErrorAlert title="Could not load the asset registry" error={error} />}
      {data && (
        <div className="-mx-5 overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="border-y border-border bg-surface-muted text-xs uppercase tracking-wide text-ink-muted">
              <tr>
                <th scope="col" className="px-5 py-2 font-medium">Asset</th>
                <th scope="col" className="px-3 py-2 font-medium">Class</th>
                <th scope="col" className="px-3 py-2 font-medium">Sector</th>
                <th scope="col" className="px-3 py-2 font-medium">Symbol</th>
                <th scope="col" className="px-5 py-2 font-medium">Identifier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.assets.map((asset) => (
                <tr key={asset.id}>
                  <td className="px-5 py-2.5">
                    <p className="font-medium">{asset.name}</p>
                    <p className="text-xs text-ink-muted">{asset.instrument}</p>
                  </td>
                  <td className="px-3 py-2.5">{CLASS_LABEL[asset.asset_class]}</td>
                  <td className="px-3 py-2.5 text-ink-muted">{asset.sector}</td>
                  <td className="px-3 py-2.5 font-mono text-xs">{asset.symbol ?? "TBD"}</td>
                  <td className="px-5 py-2.5">
                    <StatusBadge tone={asset.verified ? "positive" : "neutral"}>
                      {asset.verified ? "Verified" : "Unverified"}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="px-5 pt-4 text-xs text-ink-muted">
            Benchmark: {data.benchmark.name} ({data.benchmark.symbol ?? "TBD"}) · Risk-free:{" "}
            {data.risk_free.name} ({data.risk_free.source})
          </p>
        </div>
      )}
    </Card>
  );
}
