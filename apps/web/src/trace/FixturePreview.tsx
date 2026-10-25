import { useState } from "react";
import fixture from "../../../../contracts/trace-v1.example.json";
import TraceView from "./TraceView";
import type { TraceRecord } from "./types";

export default function FixturePreview() {
  const [scenario, setScenario] = useState("completed");
  const trace = structuredClone(fixture) as TraceRecord;
  if (
    scenario === "running" ||
    scenario === "error" ||
    scenario === "cancelled"
  ) {
    trace.status = scenario;
    trace.spans = trace.spans.filter(
      (span) => span.name !== "validate_response",
    );
    for (const span of trace.spans.filter((span) =>
      ["decision", "choose_action", "model_call"].includes(span.name),
    )) {
      span.status = scenario;
      span.outputs = null;
      span.usage = null;
      if (scenario === "running") {
        span.duration_ms = null;
        span.ended_at = null;
      }
    }
    if (scenario === "running") {
      trace.duration_ms = null;
      trace.ended_at = null;
    }
    if (scenario === "error")
      trace.spans.at(-1)!.error = {
        code: "fixture_timeout",
        message: "Synthetic provider timeout.",
      };
  }
  if (scenario === "empty") {
    trace.spans = [];
    trace.status = "running";
    trace.duration_ms = null;
    trace.ended_at = null;
  }
  return (
    <main className="trace-preview">
      <header>
        <h1>Trace fixture preview</h1>
        <a className="button secondary" href="/">
          Live tables
        </a>
      </header>
      <p className="fixture-notice">
        Development fixture only. Synthetic data, no gameplay or provider calls.
      </p>
      <section className="panel trace-explorer">
        <div className="trace-toolbar">
          <h2>Trace explorer</h2>
          <label>
            Scenario
            <select
              value={scenario}
              onChange={(event) => setScenario(event.target.value)}
            >
              <option value="completed">Completed</option>
              <option value="running">Running</option>
              <option value="error">Error</option>
              <option value="cancelled">Cancelled</option>
              <option value="empty">No spans</option>
            </select>
          </label>
        </div>
        <TraceView key={scenario} trace={trace} />
      </section>
    </main>
  );
}
