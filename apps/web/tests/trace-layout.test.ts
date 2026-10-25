import { describe, expect, it } from "vitest";
import fixture from "../../../contracts/trace-v1.example.json";
import {
  buildTree,
  duration,
  langsmithLink,
  timingBar,
  timingExtent,
  visibleRows,
} from "../src/trace/layout";
import type { TraceRecord } from "../src/trace/types";

const trace = fixture as TraceRecord;
describe("recorded run layout", () => {
  it("uses parent IDs even when children arrive before their parents", () => {
    const roots = buildTree([...trace.spans].reverse());
    expect(roots).toHaveLength(1);
    expect(roots[0].children.map((node) => node.span.name)).toEqual([
      "retrieve_evidence",
      "assess_hand",
      "choose_action",
    ]);
    expect(roots[0].children[2].children.map((node) => node.span.name)).toEqual(
      ["model_call", "validate_response"],
    );
    expect(visibleRows(roots, new Set([trace.spans[3].span_id]))).toHaveLength(
      4,
    );
  });
  it("keeps partial or cyclic records visible without recursion loops", () => {
    const spans = structuredClone(trace.spans);
    spans[0].parent_span_id = spans[4].span_id;
    spans[1].parent_span_id = "missing-parent";
    expect(visibleRows(buildTree(spans), new Set())).toHaveLength(6);
  });
  it("uses elapsed extent instead of summing overlapping child durations", () => {
    expect(timingExtent(trace)).toBe(1260);
    const assess = timingBar(trace.spans[1], 1260);
    const retrieve = timingBar(trace.spans[2], 1260);
    expect(retrieve.left).toBeLessThan(assess.left);
    expect(retrieve.left + retrieve.width!).toBeGreaterThan(assess.left);
    expect(timingBar(trace.spans[0], 1260).width).toBe(100);
  });
  it("distinguishes missing measurements from measured zero", () => {
    const running = { ...trace.spans[4], duration_ms: null };
    expect(timingBar(running, 1260).width).toBeNull();
    expect(duration(null)).toBe("Not recorded");
    expect(duration(0)).toBe("0 ms");
    expect(timingExtent({ ...trace, spans: [], duration_ms: null })).toBe(0);
    expect(
      timingBar({ ...running, start_offset_ms: 0, duration_ms: 0 }, 0),
    ).toEqual({ left: 0, width: 0 });
  });
  it("only exposes safe authenticated LangSmith destinations", () => {
    expect(
      langsmithLink("https://smith.langchain.com/o/team/projects/p/run"),
    ).toBeTruthy();
    expect(langsmithLink("https://eu.smith.langchain.com/o/team")).toBeTruthy();
    for (const url of [
      null,
      "javascript:alert(1)",
      "https://smith.langchain.com.attacker.example",
      "https://user:secret@smith.langchain.com/run",
      "http://smith.langchain.com/run",
    ])
      expect(langsmithLink(url)).toBeNull();
  });
});
