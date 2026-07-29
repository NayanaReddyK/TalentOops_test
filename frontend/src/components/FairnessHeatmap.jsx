import React, { useEffect, useState } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Scale, AlertTriangle } from 'lucide-react';

/* ── colour helpers ───────────────────────────────────────────────────── */

function getHeatmapColor(mean) {
  const t = Math.max(0, Math.min(1, (mean - 1) / 2));
  const r = Math.round(6 + (168 - 6) * t);
  const g = Math.round(182 + (85 - 182) * t);
  const b = Math.round(212 + (247 - 212) * t);
  return `rgba(${r}, ${g}, ${b}, 0.8)`;
}

/* ── custom scatter cell ──────────────────────────────────────────────── */

const CustomShape = ({ cx, cy, payload }) => {
  if (payload.suppressed) {
    return (
      <g>
        <rect x={cx - 30} y={cy - 20} width={60} height={40}
              fill="rgba(255,255,255,0.03)" rx={6}
              stroke="rgba(255,255,255,0.06)" />
        <text x={cx} y={cy} dy={4} textAnchor="middle"
              fill="rgba(255,255,255,0.25)" fontSize={11}
              fontFamily="'JetBrains Mono', monospace">
          n &lt; k
        </text>
      </g>
    );
  }

  const fill = getHeatmapColor(payload.mean_difficulty);

  return (
    <g>
      <rect x={cx - 30} y={cy - 20} width={60} height={40}
            fill={fill} rx={6} />
      <text x={cx} y={cy} dy={4} textAnchor="middle"
            fill="#fff" fontSize={13} fontWeight="600">
        {payload.mean_difficulty.toFixed(2)}
      </text>
    </g>
  );
};

/* ── custom tooltip ───────────────────────────────────────────────────── */

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;

  return (
    <div className="rounded-lg border border-white/10 bg-[#0a0a0f]/95 px-3 py-2.5 text-sm shadow-lg backdrop-blur-sm">
      <p className="mb-1 text-white/50">
        {d.dimension} · {d.value}
      </p>
      {d.suppressed ? (
        <p className="text-white/30 text-xs">Suppressed (n &lt; k)</p>
      ) : (
        <>
          <p className="font-semibold text-white">
            Difficulty: {d.mean_difficulty.toFixed(2)}
          </p>
          <p className="mt-0.5 text-xs text-white/40 font-mono">
            n = {d.n}
          </p>
        </>
      )}
    </div>
  );
};

/* ── main component ───────────────────────────────────────────────────── */

export default function FairnessHeatmap({ roleId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';
    fetch(`${apiBase}/fairness/heatmap?role_id=${encodeURIComponent(roleId)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e) => setError(e.message));
  }, [roleId]);

  /* ── error state ──────────────────────────────────────────────────── */
  if (error) {
    return (
      <div className="card flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <Scale size={28} className="text-rose-400/60" />
        <p className="text-sm text-white/50">
          Unable to load fairness data
        </p>
        <p className="text-xs text-white/30 font-mono">{error}</p>
      </div>
    );
  }

  /* ── loading state ────────────────────────────────────────────────── */
  if (!data) {
    return (
      <div className="card flex h-full items-center justify-center gap-3 p-8 text-sm text-white/30 font-mono">
        <div className="h-2 w-2 animate-pulse rounded-full bg-purple-400" />
        Aggregating telemetry…
      </div>
    );
  }

  /* ── empty state ──────────────────────────────────────────────────── */
  if (!data.cells || data.cells.length === 0) {
    return (
      <div className="card flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03]">
          <Scale size={22} className="text-purple-400/70" />
        </div>
        <div>
          <p className="text-sm text-white/60">No demographic data available yet</p>
          <p className="mt-1 text-xs text-white/30">
            Fairness analysis requires completed interviews.
          </p>
        </div>
      </div>
    );
  }

  /* ── prepare chart data ───────────────────────────────────────────── */
  const dimensions = [...new Set(data.cells.map((c) => c.dimension))];
  const cohorts = [...new Set(data.cells.map((c) => c.value))];

  const chartData = data.cells.map((c) => ({
    ...c,
    x: cohorts.indexOf(c.value),
    y: dimensions.indexOf(c.dimension),
    z: c.suppressed ? 0 : c.mean_difficulty,
  }));

  return (
    <div className="card flex h-full flex-col overflow-hidden">
      {/* ── header ────────────────────────────────────────────────────── */}
      <div className="card-header">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/[0.06] bg-white/[0.03] text-purple-400">
            <Scale size={18} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white/90">
              Fairness Analysis
            </h3>
            <p className="text-[11px] text-white/35">
              K-anonymized cohort comparison
            </p>
          </div>
        </div>
      </div>

      {/* ── body ──────────────────────────────────────────────────────── */}
      <div className="card-body flex flex-1 flex-col overflow-hidden">
        {/* drift alerts */}
        {data.drift_alerts?.length > 0 && (
          <div className="mb-5 rounded-lg border border-amber-400/15 bg-amber-400/[0.04] px-4 py-3">
            <div className="mb-1.5 flex items-center gap-2 text-xs font-medium text-amber-400">
              <AlertTriangle size={14} />
              Drift Detected
            </div>
            <div className="space-y-1">
              {data.drift_alerts.map((a, i) => (
                <p key={i} className="text-xs text-white/45">
                  <span className="font-medium text-white/70">
                    {a.dimension}={a.value}
                  </span>
                  {' · '}
                  Mean {a.mean_difficulty.toFixed(2)} vs baseline{' '}
                  {a.overall_mean.toFixed(2)}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* scatter heatmap */}
        <div className="min-h-[250px] flex-1">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 60 }}>
              <XAxis
                type="number" dataKey="x" name="Cohort"
                domain={[0, cohorts.length - 1]}
                tickFormatter={(v) => cohorts[v]}
                tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 12 }}
                axisLine={false} tickLine={false}
              />
              <YAxis
                type="number" dataKey="y" name="Dimension"
                domain={[0, dimensions.length - 1]}
                tickFormatter={(v) => dimensions[v]}
                tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 12 }}
                axisLine={false} tickLine={false}
              />
              <ZAxis dataKey="z" range={[0, 100]} />
              <Tooltip
                cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.08)' }}
                content={<CustomTooltip />}
              />
              <Scatter data={chartData} shape={<CustomShape />} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* legend */}
        <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-4 text-xs text-white/35">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-sm" style={{ background: getHeatmapColor(1) }} />
            <span>Easier</span>
            <div className="ml-3 h-3 w-3 rounded-sm" style={{ background: getHeatmapColor(3) }} />
            <span>Harder</span>
          </div>
          <div>
            Baseline:{' '}
            <span className="font-mono text-white/60">
              {data.overall_mean.toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
