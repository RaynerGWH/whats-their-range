import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import {
  buildTree,
  duration,
  langsmithLink,
  timingBar,
  timingExtent,
  visibleRows,
} from "./layout";
import type { TraceRecord, TraceSpan, TraceStatus } from "./types";
import "./trace.css";

export function Status({ status }: { status: TraceStatus }) {
  return (
    <span className={`trace-status status-${status}`}>
      <i />
      {status}
    </span>
  );
}

function JsonBlock({
  title,
  value,
}: {
  title: string;
  value: Record<string, unknown> | null;
}) {
  return (
    <section className="trace-json">
      <h4>{title}</h4>
      {value === null ? (
        <p className="trace-muted">Not recorded</p>
      ) : (
        <pre tabIndex={0} aria-label={title}>
          {JSON.stringify(value, null, 2)}
        </pre>
      )}
    </section>
  );
}

function SpanDetail({ span }: { span: TraceSpan }) {
  return (
    <section className="span-detail" aria-label="Step details">
      <div className="trace-detail-heading">
        <div>
          <span className="trace-kicker">Step details</span>
          <h3>{span.name}</h3>
        </div>
        <Status status={span.status} />
      </div>
      <dl className="trace-metrics">
        <div>
          <dt>Kind</dt>
          <dd>{span.kind}</dd>
        </div>
        <div>
          <dt>Start offset</dt>
          <dd>{duration(span.start_offset_ms)}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>
            {span.duration_ms === null && span.status === "running"
              ? "Running"
              : duration(span.duration_ms)}
          </dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{span.model ?? "Not recorded"}</dd>
        </div>
        <div>
          <dt>Input tokens</dt>
          <dd>
            {span.usage?.input_tokens?.toLocaleString() ?? "Not recorded"}
          </dd>
        </div>
        <div>
          <dt>Output tokens</dt>
          <dd>
            {span.usage?.output_tokens?.toLocaleString() ?? "Not recorded"}
          </dd>
        </div>
        <div>
          <dt>Cost (USD)</dt>
          <dd>
            {span.usage?.cost_usd == null
              ? "Not recorded"
              : `$${span.usage.cost_usd.toLocaleString("en", { maximumFractionDigits: 8 })}`}
          </dd>
        </div>
      </dl>
      {span.error && (
        <div className="trace-error" role="alert">
          <strong>{span.error.code}</strong>
          <p>{span.error.message}</p>
        </div>
      )}
      <JsonBlock title="Inputs" value={span.inputs} />
      <JsonBlock title="Outputs" value={span.outputs} />
      <details className="trace-identifiers">
        <summary>Identifiers and metadata</summary>
        <dl>
          <dt>Span ID</dt>
          <dd>{span.span_id}</dd>
          <dt>Parent span ID</dt>
          <dd>{span.parent_span_id ?? "Root"}</dd>
          <dt>Started (UTC)</dt>
          <dd>{span.started_at}</dd>
          <dt>Ended (UTC)</dt>
          <dd>{span.ended_at ?? "Not recorded"}</dd>
        </dl>
        <JsonBlock title="Metadata" value={span.metadata} />
      </details>
    </section>
  );
}

export default function TraceView({ trace }: { trace: TraceRecord }) {
  const [selected, setSelected] = useState(trace.trace_id);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const container = useRef<HTMLDivElement>(null);
  const tree = useMemo(() => buildTree(trace.spans), [trace.spans]);
  const rows = visibleRows(tree, collapsed);
  const extent = timingExtent(trace);
  const span =
    trace.spans.find((item) => item.span_id === selected) ?? trace.spans[0];
  const link = langsmithLink(trace.langsmith_url);
  useEffect(() => {
    if (!container.current || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries)
          if (entry.isIntersecting) {
            entry.target.classList.add("trace-revealed");
            observer.unobserve(entry.target);
          }
      },
      { threshold: 0.05 },
    );
    container.current
      .querySelectorAll(".trace-summary, .trace-runs, .span-detail")
      .forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);
  const toggle = (id: string) =>
    setCollapsed((old) => {
      const next = new Set(old);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  return (
    <div className="trace-view" ref={container}>
      <div className="trace-summary">
        <div>
          <span className="trace-kicker">Decision trace</span>
          <h3>
            Hand {trace.hand} <span>· State {trace.state_version}</span>
          </h3>
          <code>{trace.trace_id}</code>
        </div>
        <div className="trace-total">
          <span>Total elapsed</span>
          <strong>
            {trace.duration_ms === null && trace.status === "running"
              ? "Running"
              : duration(trace.duration_ms)}
          </strong>
          <Status status={trace.status} />
        </div>
        {link && (
          <a
            className="button secondary"
            href={link}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open in LangSmith <ExternalLink size={13} />
          </a>
        )}
      </div>
      <div className="trace-content">
        <section className="trace-runs" aria-label="Run tree and timing">
          <div className="trace-run-heading">
            <h3>Run tree</h3>
            <span>Timing from root start</span>
          </div>
          <div className="trace-axis">
            <span>Span</span>
            <div>
              <span>0 ms</span>
              <span>
                {!trace.spans.length && trace.duration_ms === null
                  ? "Not recorded"
                  : duration(extent)}
              </span>
            </div>
          </div>
          <div className="trace-rows">
            {rows.map(({ node, depth }) => {
              const bar = timingBar(node.span, extent);
              return (
                <div
                  className={`trace-row ${span?.span_id === node.span.span_id ? "is-selected" : ""}`}
                  key={node.span.span_id}
                >
                  <div
                    className="trace-row-name"
                    style={{ paddingLeft: `${8 + Math.min(depth, 8) * 14}px` }}
                  >
                    {node.children.length > 0 ? (
                      <button
                        className="trace-expand"
                        aria-label={`${collapsed.has(node.span.span_id) ? "Expand" : "Collapse"} ${node.span.name}`}
                        aria-expanded={!collapsed.has(node.span.span_id)}
                        onClick={() => toggle(node.span.span_id)}
                      >
                        {collapsed.has(node.span.span_id) ? (
                          <ChevronRight size={14} />
                        ) : (
                          <ChevronDown size={14} />
                        )}
                      </button>
                    ) : (
                      <span className="trace-leaf" />
                    )}
                    <button
                      className="trace-select"
                      aria-label={`${node.span.name} ${node.span.kind} · ${node.span.status}`}
                      aria-pressed={span?.span_id === node.span.span_id}
                      onClick={() => setSelected(node.span.span_id)}
                    >
                      <strong>{node.span.name}</strong>
                      <span>
                        {node.span.kind} · {node.span.status}
                      </span>
                    </button>
                  </div>
                  <button
                    className="trace-timing"
                    aria-label={`${node.span.name} timing: start ${duration(node.span.start_offset_ms)}, duration ${duration(node.span.duration_ms)}`}
                    onClick={() => setSelected(node.span.span_id)}
                  >
                    <span
                      className={`trace-bar kind-${node.span.kind} status-${node.span.status} ${bar.width === null ? "unmeasured" : ""}`}
                      style={{
                        left: `${bar.left}%`,
                        width: bar.width === null ? "2px" : `${bar.width}%`,
                      }}
                    />
                    <span className="trace-bar-label">
                      {node.span.duration_ms === null &&
                      node.span.status === "running"
                        ? "Running"
                        : duration(node.span.duration_ms)}
                    </span>
                  </button>
                </div>
              );
            })}
          </div>
          {!trace.spans.length && (
            <p className="trace-message">No spans recorded yet.</p>
          )}
          <p className="trace-caption">
            Child durations may overlap. Unmeasured spans show a start marker.
          </p>
        </section>
        {span && <SpanDetail span={span} />}
      </div>
    </div>
  );
}
