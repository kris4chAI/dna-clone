import { useEffect, useMemo, useRef, useState } from "react";

// Shared grid, merged from the TAF operator app: per-column filters (text, =exact, !exclude), sort,
// column resize, pagination (100/250/500/1000), long-cell expand and CSV export with a UTF-8 BOM.
// No table library on purpose.
const PAGE_SIZES = [100, 250, 500, 1000];

function cellText(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function compare(a, b) {
  if (a === b) return 0;
  if (a === null || a === undefined || a === "") return 1;
  if (b === null || b === undefined || b === "") return -1;
  const na = Number(a);
  const nb = Number(b);
  if (!Number.isNaN(na) && !Number.isNaN(nb) && String(a).trim() !== "" && String(b).trim() !== "") return na - nb;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

function csvEscape(s) {
  const t = cellText(s);
  return /[",\n\r]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
}

export function downloadCsv(filename, columns, rows) {
  const header = columns.map((c) => csvEscape(c.label || c.key)).join(",");
  const lines = rows.map((r) => columns.map((c) => csvEscape(r[c.key])).join(","));
  const blob = new Blob(["﻿" + [header, ...lines].join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function DataTable({ rows, columns, csvName = "export.csv", rowKey, emptyText = "No rows.", maxCellChars = 160 }) {
  const cols = useMemo(() => {
    if (columns && columns.length) return columns;
    const keys = rows && rows.length ? Object.keys(rows[0]) : [];
    return keys.map((k) => ({ key: k, label: k }));
  }, [columns, rows]);

  const [filters, setFilters] = useState({});
  const [sort, setSort] = useState({ key: null, dir: 1 });
  const [pageSize, setPageSize] = useState(100);
  const [page, setPage] = useState(0);
  const [widths, setWidths] = useState({});
  const [expanded, setExpanded] = useState(null);
  const drag = useRef(null);

  useEffect(() => setPage(0), [filters, sort, pageSize, rows]);

  const filtered = useMemo(() => {
    const active = Object.entries(filters).filter(([, v]) => v && v.trim());
    let out = rows || [];
    if (active.length) {
      out = out.filter((r) =>
        active.every(([k, v]) => {
          const needle = v.trim().toLowerCase();
          const hay = cellText(r[k]).toLowerCase();
          if (needle.startsWith("=")) return hay === needle.slice(1);
          if (needle.startsWith("!")) return !hay.includes(needle.slice(1));
          return hay.includes(needle);
        })
      );
    }
    if (sort.key) {
      out = [...out].sort((a, b) => sort.dir * compare(a[sort.key], b[sort.key]));
    }
    return out;
  }, [rows, filters, sort]);

  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const view = filtered.slice(page * pageSize, page * pageSize + pageSize);

  const onSort = (key) =>
    setSort((s) => (s.key !== key ? { key, dir: 1 } : s.dir === 1 ? { key, dir: -1 } : { key: null, dir: 1 }));

  const startResize = (e, key) => {
    e.preventDefault();
    e.stopPropagation();
    const th = e.target.parentElement;
    drag.current = { key, startX: e.clientX, startW: th.getBoundingClientRect().width };
    const move = (ev) => {
      const d = drag.current;
      if (!d) return;
      setWidths((w) => ({ ...w, [d.key]: Math.max(60, d.startW + ev.clientX - d.startX) }));
    };
    const up = () => {
      drag.current = null;
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  };

  return (
    <div className="dt">
      <div className="dt-bar">
        <span className="muted">
          {filtered.length.toLocaleString()} of {(rows || []).length.toLocaleString()} rows
        </span>
        <span className="spacer" />
        {Object.values(filters).some((v) => v) && (
          <button className="btn ghost small" onClick={() => setFilters({})}>Clear filters</button>
        )}
        <label className="muted">
          Rows/page{" "}
          <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
        <button className="btn ghost small" onClick={() => downloadCsv(csvName, cols, filtered)} disabled={!filtered.length}>
          Export CSV
        </button>
      </div>
      <div className="dt-scroll">
        <table>
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c.key} style={{ width: widths[c.key] || c.width || 150 }} onClick={() => onSort(c.key)} title="Sort">
                  <span>{c.label || c.key}</span>
                  {sort.key === c.key && <span className="sort">{sort.dir === 1 ? " ▲" : " ▼"}</span>}
                  <span className="resize" onMouseDown={(e) => startResize(e, c.key)} onClick={(e) => e.stopPropagation()} />
                </th>
              ))}
            </tr>
            <tr className="filters">
              {cols.map((c) => (
                <th key={c.key}>
                  {c.filterable === false ? null : (
                    <input
                      aria-label={`Filter ${c.label || c.key}`}
                      placeholder="filter"
                      value={filters[c.key] || ""}
                      onChange={(e) => setFilters((f) => ({ ...f, [c.key]: e.target.value }))}
                    />
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.length === 0 && (
              <tr>
                <td colSpan={cols.length} className="empty">{emptyText}</td>
              </tr>
            )}
            {view.map((r, i) => {
              const k = rowKey ? rowKey(r) : i + page * pageSize;
              return (
                <tr key={k}>
                  {cols.map((c) => {
                    if (c.render) return <td key={c.key}>{c.render(r)}</td>;
                    const t = cellText(r[c.key]);
                    const long = t.length > maxCellChars;
                    const cellId = `${k}:${c.key}`;
                    return (
                      <td key={c.key} className={c.mono ? "mono" : undefined}>
                        {long && expanded !== cellId ? (
                          <>
                            {t.slice(0, maxCellChars)}…{" "}
                            <button className="link" onClick={() => setExpanded(cellId)}>more</button>
                          </>
                        ) : (
                          t
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="dt-pager">
          <button className="btn ghost" disabled={page === 0} onClick={() => setPage(0)}>«</button>
          <button className="btn ghost" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>‹</button>
          <span className="muted">Page {page + 1} / {pages}</span>
          <button className="btn ghost" disabled={page >= pages - 1} onClick={() => setPage((p) => p + 1)}>›</button>
          <button className="btn ghost" disabled={page >= pages - 1} onClick={() => setPage(pages - 1)}>»</button>
        </div>
      )}
    </div>
  );
}
