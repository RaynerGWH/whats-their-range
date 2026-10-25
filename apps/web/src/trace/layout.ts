import type { TraceRecord, TraceSpan } from "./types";

export type SpanNode = { span: TraceSpan; children: SpanNode[] };

// Parent IDs, not input order or names, define nesting. Orphans remain visible.
// Break malformed cycles so a partial or corrupt record cannot hang rendering.
export function buildTree(spans: TraceSpan[]): SpanNode[] {
  const nodes = new Map<string, SpanNode>();
  for (const span of spans)
    if (!nodes.has(span.span_id))
      nodes.set(span.span_id, { span, children: [] });
  const roots: SpanNode[] = [];
  for (const node of nodes.values()) {
    let parent = nodes.get(node.span.parent_span_id || "");
    const seen = new Set([node.span.span_id]);
    let cursor = parent;
    while (cursor) {
      if (seen.has(cursor.span.span_id)) {
        parent = undefined;
        break;
      }
      seen.add(cursor.span.span_id);
      cursor = nodes.get(cursor.span.parent_span_id || "");
    }
    if (parent) parent.children.push(node);
    else roots.push(node);
  }
  const sort = (items: SpanNode[]) => {
    items.sort((a, b) => a.span.start_offset_ms - b.span.start_offset_ms);
    items.forEach((node) => sort(node.children));
  };
  sort(roots);
  return roots;
}

export function visibleRows(
  nodes: SpanNode[],
  collapsed: Set<string>,
  depth = 0,
): { node: SpanNode; depth: number }[] {
  return nodes.flatMap((node) => [
    { node, depth },
    ...(collapsed.has(node.span.span_id)
      ? []
      : visibleRows(node.children, collapsed, depth + 1)),
  ]);
}

// No wall-clock extrapolation: running/null durations have a start marker only.
export function timingExtent(trace: TraceRecord): number {
  return Math.max(
    0,
    trace.duration_ms ?? 0,
    ...trace.spans.map(
      (span) => span.start_offset_ms + (span.duration_ms ?? 0),
    ),
  );
}
export function timingBar(span: TraceSpan, extent: number) {
  const scale = Math.max(1, extent);
  return {
    left: (span.start_offset_ms / scale) * 100,
    width: span.duration_ms === null ? null : (span.duration_ms / scale) * 100,
  };
}
export function duration(value: number | null): string {
  if (value === null) return "Not recorded";
  return value >= 1000
    ? `${(value / 1000).toFixed(2)} s`
    : `${Math.round(value)} ms`;
}
export function langsmithLink(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" &&
      (url.hostname === "smith.langchain.com" ||
        url.hostname.endsWith(".smith.langchain.com")) &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}
