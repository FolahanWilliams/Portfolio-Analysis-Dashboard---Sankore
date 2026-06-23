// Generic coloured matrix used for the exposure heatmap and the correlation
// grid. Pure presentation: it receives values and a colour function.

export function Matrix({
  rowLabels,
  colLabels,
  values,
  color,
  format,
  rowHeader = "",
  cellSize = 56,
}: {
  rowLabels: string[];
  colLabels: string[];
  values: number[][];
  color: (v: number) => string;
  format: (v: number) => string;
  rowHeader?: string;
  cellSize?: number;
}) {
  const dense = cellSize < 48;
  return (
    <div className="overflow-x-auto">
      <table className="border-separate" style={{ borderSpacing: 2 }}>
        <thead>
          <tr>
            <th className="px-1 py-1 text-left text-[11px] font-medium text-slate-400">
              {rowHeader}
            </th>
            {colLabels.map((c) => (
              <th key={c} className="px-1 py-1 text-center text-[10px] font-medium text-slate-500">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowLabels.map((r, i) => (
            <tr key={r}>
              <td className="whitespace-nowrap px-1 py-1 text-right text-[11px] font-medium text-slate-600">
                {r}
              </td>
              {values[i].map((v, j) => (
                <td
                  key={j}
                  className={`rounded text-center tabular text-slate-700 ${dense ? "text-[9px]" : "text-[11px]"}`}
                  style={{ backgroundColor: color(v), minWidth: cellSize, width: cellSize, height: dense ? 26 : 34 }}
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
