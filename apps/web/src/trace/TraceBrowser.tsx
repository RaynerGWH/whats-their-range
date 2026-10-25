import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { request } from "../api";
import TraceView, { Status } from "./TraceView";
import type { TracePage, TraceRecord } from "./types";

type Props = {
  tableId: string;
  hand: number;
  token: string;
  connection: string;
  decisionTraceId?: string | null;
  decisionHand?: number;
  activeTraceId?: string | null;
};

export default function TraceBrowser({
  tableId,
  hand: currentHand,
  token,
  connection,
  decisionTraceId,
  decisionHand,
  activeTraceId,
}: Props) {
  const [hand, setHand] = useState(
    String(
      activeTraceId
        ? currentHand
        : decisionTraceId
          ? (decisionHand ?? currentHand)
          : currentHand || 1,
    ),
  );
  const [traceId, setTraceId] = useState<string | null>(
    activeTraceId ?? decisionTraceId ?? null,
  );
  const [items, setItems] = useState<TraceRecord[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [pageCursor, setPageCursor] = useState<string | null>(null);
  const [listBusy, setListBusy] = useState(true);
  const [listError, setListError] = useState("");
  const [trace, setTrace] = useState<TraceRecord | null>(null);
  const [traceError, setTraceError] = useState("");
  const [revision, setRevision] = useState(0);
  const validHand = hand === "" || (/^\d+$/.test(hand) && Number(hand) >= 1);
  const path = `/tables/${encodeURIComponent(tableId)}/traces`;

  useEffect(() => {
    const controller = new AbortController();
    if (!validHand) {
      setListBusy(false);
      return;
    }
    setListBusy(true);
    setListError("");
    const query = new URLSearchParams({ limit: "50" });
    if (hand) query.set("hand", hand);
    if (pageCursor) query.set("cursor", pageCursor);
    request<TracePage>(`${path}?${query}`, token, undefined, controller.signal)
      .then((page) => {
        if (controller.signal.aborted) return;
        if (
          page.items.some(
            (item) =>
              item.table_id !== tableId || (hand && item.hand !== Number(hand)),
          )
        )
          throw new Error("Trace response does not match this table and hand.");
        setItems((old) => {
          const merged = new Map(
            (pageCursor ? old : []).map((item) => [item.trace_id, item]),
          );
          page.items.forEach((item) => merged.set(item.trace_id, item));
          return [...merged.values()];
        });
        setCursor(page.next_cursor);
        setTraceId((old) => old ?? page.items[0]?.trace_id ?? null);
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setListError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setListBusy(false);
      });
    return () => controller.abort();
  }, [path, tableId, hand, validHand, token, pageCursor, revision, connection]);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setTrace(null);
    setTraceError("");
    if (!traceId) return () => controller.abort();
    const poll = async () => {
      try {
        const next = await request<TraceRecord>(
          `${path}/${encodeURIComponent(traceId)}`,
          token,
          undefined,
          controller.signal,
        );
        if (controller.signal.aborted) return;
        if (next.trace_id !== traceId || next.table_id !== tableId)
          throw new Error("Trace response does not match this decision.");
        setTrace(next);
        setTraceError("");
        setItems((old) =>
          old.map((item) => (item.trace_id === next.trace_id ? next : item)),
        );
        if (next.status === "running") timer = setTimeout(poll, 2000);
      } catch (error) {
        if (controller.signal.aborted) return;
        setTraceError((error as Error).message);
        timer = setTimeout(poll, 4000);
      }
    };
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [path, tableId, traceId, token, revision, connection]);

  const changeHand = (value: string, selected: string | null = null) => {
    setHand(value);
    setPageCursor(null);
    setCursor(null);
    setItems([]);
    setTrace(null);
    setTraceId(selected);
    setRevision((old) => old + 1);
  };
  return (
    <section
      className="panel trace-explorer"
      id="trace-explorer"
      aria-label="Trace explorer"
    >
      <div className="trace-toolbar">
        <h2>Trace explorer</h2>
        <label>
          Hand
          <input
            type="number"
            min="1"
            step="1"
            placeholder="All"
            value={hand}
            onChange={(event) => changeHand(event.target.value)}
          />
        </label>
        <button className="button secondary" onClick={() => changeHand("")}>
          All hands
        </button>
        <button
          className="button secondary"
          onClick={() => changeHand(String(currentHand || 1))}
        >
          Current hand
        </button>
        {decisionTraceId && (
          <button
            className="button secondary"
            onClick={() =>
              changeHand(String(decisionHand ?? currentHand), decisionTraceId)
            }
          >
            Decision trace
          </button>
        )}
        {activeTraceId && (
          <button
            className="button secondary"
            onClick={() => changeHand(String(currentHand), activeTraceId)}
          >
            Running trace
          </button>
        )}
        <button
          className="button secondary"
          onClick={() => {
            setPageCursor(null);
            setRevision((old) => old + 1);
          }}
          disabled={listBusy}
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>
      {connection !== "live" && (
        <p className="trace-message" role="status">
          Live updates disconnected. Trace requests retry independently.
        </p>
      )}
      {!validHand && (
        <p className="trace-message" role="alert">
          Enter a whole hand number of 1 or more.
        </p>
      )}
      {!decisionTraceId && (
        <p className="trace-legacy">
          This decision has no linked trace. Browse recorded traces by hand.
        </p>
      )}
      {listError && (
        <p className="trace-error" role="alert">
          {listError}{" "}
          <button
            className="text-button"
            onClick={() => setRevision((old) => old + 1)}
          >
            Retry
          </button>
        </p>
      )}
      <div
        className="trace-decisions"
        aria-label="Recorded decisions"
        aria-busy={listBusy}
      >
        {items.map((item) => (
          <button
            key={item.trace_id}
            className={`trace-decision ${traceId === item.trace_id ? "is-selected" : ""}`}
            aria-pressed={traceId === item.trace_id}
            onClick={() => setTraceId(item.trace_id)}
          >
            <strong>
              Hand {item.hand} · State {item.state_version}
            </strong>
            <Status status={item.status} />
          </button>
        ))}
        {listBusy && (
          <p className="trace-message" role="status">
            Loading traces...
          </p>
        )}
        {!listBusy && !listError && validHand && !items.length && (
          <p className="trace-message">
            No traces recorded for this hand selection.
          </p>
        )}
        {cursor && (
          <button
            className="button secondary"
            disabled={listBusy || !!listError}
            onClick={() => setPageCursor(cursor)}
          >
            Load older traces
          </button>
        )}
      </div>
      {traceError && (
        <p className="trace-error" role="alert">
          {traceError} Reconnecting...
        </p>
      )}
      {traceId && !trace && !traceError && (
        <p className="trace-message" role="status">
          Loading decision trace...
        </p>
      )}
      {trace && (
        <>
          <p className="trace-source">
            Table {trace.table_id} · Started {trace.started_at}
            {traceError ? " · Last received data" : ""}
          </p>
          {trace.status !== "running" && !trace.langsmith_url && (
            <p className="trace-message">
              LangSmith link not available. Refresh to check again.
            </p>
          )}
          <TraceView key={trace.trace_id} trace={trace} />
        </>
      )}
    </section>
  );
}
