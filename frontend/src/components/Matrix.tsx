// Generic coloured matrix used for the exposure heatmap and the correlation
// grid. Pure presentation: it receives values and a colour function.

export function Matrix({
  rowLabels,
  colLabels,
  values,
  color,
  format,
  rowHeader = "",
}: {
  rowLabels: string[];
  colLabels: string[];
  values: number[][];
  color: (v: number) => string;
  format: (v: number) => string;
  rowHeader?: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate" style={{ borderSpacing: 2 }}>
        <thead>
          <tr>
            <th className="px-2 py-1 text-left text-[11px] font-medium text-slate-400">
              {rowHeader}
            </th>
            {colLabels.map((c) => (
              <th key={c} className="px-2 py-1 text-center text-[11px] font-medium text-slate-500">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowLabels.map((r, i) => (
            <tr key={r}>
              <td className="whitespace-nowrap px-2 py-1 text-right text-xs font-medium text-slate-600">
                {r}
              </td>
              {values[i].map((v, j) => (
                <td
                  key={j}
                  className="rounded text-center text-[11px] tabular text-slate-700"
                  style={{ backgroundColor: color(v), minWidth: 56, height: 34 }}
                  title={`${r} × ${colLabels[j]}: ${format(v)}`}
                >
                  {format(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
