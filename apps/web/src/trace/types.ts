// Mirrors contracts/trace-v1.schema.json. Never derive trace payloads from Table.
export type TraceStatus = "running" | "completed" | "error" | "cancelled";
export type TraceSpan = {
  span_id: string;
  parent_span_id: string | null;
  name: string;
  kind: "chain" | "tool" | "llm" | "retriever";
  status: TraceStatus;
  started_at: string;
  ended_at: string | null;
  start_offset_ms: number;
  duration_ms: number | null;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown> | null;
  model: string | null;
  usage: {
    input_tokens: number | null;
    output_tokens: number | null;
    cost_usd: number | null;
  } | null;
  error: { code: string; message: string } | null;
  metadata: Record<string, unknown>;
};
export type TraceRecord = {
  schema_version: 1;
  trace_id: string;
  table_id: string;
  hand: number;
  state_version: number;
  status: TraceStatus;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  langsmith_url: string | null;
  spans: TraceSpan[];
  metadata: Record<string, unknown>;
};
export type TracePage = { items: TraceRecord[]; next_cursor: string | null };
