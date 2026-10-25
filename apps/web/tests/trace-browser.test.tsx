// @vitest-environment jsdom
import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import fixture from "../../../contracts/trace-v1.example.json";
import TraceBrowser from "../src/trace/TraceBrowser";
import TraceView from "../src/trace/TraceView";
import type { TraceRecord } from "../src/trace/types";
const trace = fixture as TraceRecord;
const props = {
  tableId: trace.table_id,
  hand: 3,
  token: "test-control-token",
  connection: "live",
};
const response = (data: unknown) =>
  Promise.resolve(
    new Response(JSON.stringify(data), {
      headers: { "Content-Type": "application/json" },
    }),
  );
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("trace requests and selection", () => {
  it("authenticates requests, paginates opaque cursors, and selects a decision", async () => {
    const older = { ...trace, trace_id: "older", state_version: 10 };
    const fetcher = vi.fn((url: string) => {
      if (url.includes("cursor="))
        return response({ items: [older], next_cursor: null });
      if (url.includes("?"))
        return response({ items: [trace], next_cursor: "opaque/+=" });
      return response(url.endsWith("/older") ? older : trace);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<TraceBrowser {...props} />);
    await screen.findByRole("heading", { name: "Hand 3 · State 12" });
    expect(fetcher.mock.calls[0][0]).toContain("hand=3");
    expect(
      (fetcher.mock.calls as unknown as [string, RequestInit][])[0][1].headers,
    ).toMatchObject({ Authorization: "Bearer test-control-token" });
    fireEvent.click(screen.getByRole("button", { name: "Load older traces" }));
    await screen.findByRole("button", { name: /Hand 3 · State 10/ });
    expect(
      fetcher.mock.calls.some(([url]) =>
        url.includes("cursor=opaque%2F%2B%3D"),
      ),
    ).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /Hand 3 · State 10/ }));
    await screen.findByRole("heading", { name: "Hand 3 · State 10" });
  });
  it("polls running traces, retains data on a disconnect, and stops at completion", async () => {
    vi.useFakeTimers();
    const running = { ...trace, status: "running", duration_ms: null };
    let details = 0;
    const fetcher = vi.fn((url: string) => {
      if (url.includes("?"))
        return response({ items: [running], next_cursor: null });
      details++;
      if (details === 2) return Promise.reject(new Error("Offline"));
      return response(details < 3 ? running : trace);
    });
    vi.stubGlobal("fetch", fetcher);
    const view = render(
      <TraceBrowser {...props} decisionTraceId={trace.trace_id} />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(details).toBe(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(screen.getByText(/Offline.*Reconnecting/)).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Hand 3 · State 12" }),
    ).toBeTruthy();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(screen.queryByText(/Offline.*Reconnecting/)).toBeNull();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(8000);
    });
    expect(details).toBe(3);
    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
  it("manually refreshes a completed trace to discover a delayed LangSmith link", async () => {
    let linked = false;
    const fetcher = vi.fn((url: string) =>
      response(
        url.includes("?")
          ? { items: [trace], next_cursor: null }
          : {
              ...trace,
              langsmith_url: linked
                ? "https://smith.langchain.com/o/test/projects/p/run"
                : null,
            },
      ),
    );
    vi.stubGlobal("fetch", fetcher);
    render(<TraceBrowser {...props} decisionTraceId={trace.trace_id} />);
    await screen.findByText(
      "LangSmith link not available. Refresh to check again.",
    );
    expect(
      screen.queryByRole("link", { name: "Open in LangSmith" }),
    ).toBeNull();
    linked = true;
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await screen.findByRole("link", { name: "Open in LangSmith" });
    expect(
      screen.queryByText(
        "LangSmith link not available. Refresh to check again.",
      ),
    ).toBeNull();
  });
  it("aborts requests on a hand change and ignores late responses", async () => {
    let finishOld!: (value: Response) => void;
    let oldSignal: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, options: RequestInit) => {
        if (url.includes("hand=3")) {
          oldSignal = options.signal!;
          return new Promise<Response>((resolve) => {
            finishOld = resolve;
          });
        }
        return response({ items: [], next_cursor: null });
      }),
    );
    render(<TraceBrowser {...props} />);
    expect(screen.getByText("Loading traces...")).toBeTruthy();
    fireEvent.change(screen.getByRole("spinbutton", { name: "Hand" }), {
      target: { value: "4" },
    });
    await screen.findByText("No traces recorded for this hand selection.");
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => {
      finishOld(
        new Response(JSON.stringify({ items: [trace], next_cursor: null })),
      );
    });
    expect(
      screen.queryByRole("button", { name: /Hand 3 · State 12/ }),
    ).toBeNull();
  });
  it("does not display a late detail response after switching tables", async () => {
    let finishOld!: (value: Response) => void;
    let oldSignal: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, options: RequestInit) => {
        if (url.endsWith(trace.trace_id)) {
          oldSignal = options.signal!;
          return new Promise<Response>((resolve) => {
            finishOld = resolve;
          });
        }
        return response({ items: [], next_cursor: null });
      }),
    );
    const view = render(
      <TraceBrowser key="first" {...props} decisionTraceId={trace.trace_id} />,
    );
    view.rerender(<TraceBrowser key="second" {...props} tableId="second" />);
    await screen.findByText("No traces recorded for this hand selection.");
    await act(async () => {
      finishOld(new Response(JSON.stringify(trace)));
    });
    expect(oldSignal?.aborted).toBe(true);
    expect(
      screen.queryByRole("heading", { name: "Hand 3 · State 12" }),
    ).toBeNull();
  });
  it("shows endpoint failure without substituting the fixture and retries", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response("missing", { status: 404 }))
      .mockImplementation(() => response({ items: [], next_cursor: null }));
    vi.stubGlobal("fetch", fetcher);
    render(<TraceBrowser {...props} />);
    await screen.findByText(/Trace endpoints may be unavailable/);
    expect(screen.queryByRole("region", { name: "Step details" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText("No traces recorded for this hand selection.");
  });
  it("preserves legacy decisions without trace IDs and reports authentication failure safely", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response("secret raw proxy error", { status: 401 }),
        ),
    );
    render(<TraceBrowser {...props} decisionTraceId={undefined} />);
    await screen.findByText(/Access denied. Check Connections./);
    expect(
      screen.getByText(
        "This decision has no linked trace. Browse recorded traces by hand.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText(/secret raw proxy error/)).toBeNull();
    expect(screen.queryByRole("region", { name: "Step details" })).toBeNull();
  });
  it("rejects cross-table detail data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        response(
          url.includes("?")
            ? { items: [], next_cursor: null }
            : { ...trace, table_id: "another-table" },
        ),
      ),
    );
    render(<TraceBrowser {...props} decisionTraceId={trace.trace_id} />);
    await screen.findByText(/Trace response does not match this decision/);
    expect(
      screen.queryByRole("heading", { name: "Hand 3 · State 12" }),
    ).toBeNull();
  });
  it("cancels the running poll when unmounted", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn((url: string) =>
      response(
        url.includes("?")
          ? { items: [], next_cursor: null }
          : { ...trace, status: "running", duration_ms: null },
      ),
    );
    vi.stubGlobal("fetch", fetcher);
    const view = render(
      <TraceBrowser {...props} decisionTraceId={trace.trace_id} />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    view.unmount();
    const count = fetcher.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6000);
    });
    expect(fetcher).toHaveBeenCalledTimes(count);
  });
});

describe("step details", () => {
  it("selects nested spans, collapses branches, and preserves missing cost", () => {
    render(<TraceView trace={trace} />);
    fireEvent.click(
      screen.getByRole("button", { name: "model_call llm · completed" }),
    );
    const detail = within(screen.getByRole("region", { name: "Step details" }));
    expect(detail.getByText("fixture/model")).toBeTruthy();
    expect(detail.getByText("100")).toBeTruthy();
    expect(detail.getByText("Not recorded")).toBeTruthy();
    expect(detail.getByLabelText("Inputs").textContent).toContain(
      "Synthetic development fixture only.",
    );
    expect(
      screen.queryByRole("link", { name: "Open in LangSmith" }),
    ).toBeNull();
    fireEvent.click(
      screen.getByRole("button", { name: "Collapse choose_action" }),
    );
    expect(
      screen.queryByRole("button", { name: "model_call llm · completed" }),
    ).toBeNull();
    fireEvent.click(
      screen.getByRole("button", { name: "Expand choose_action" }),
    );
    expect(
      screen
        .getByRole("button", { name: "model_call llm · completed" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
  });
  it("renders only recorded error spans and a safe LangSmith link", async () => {
    const failed = structuredClone(trace);
    failed.langsmith_url = "https://smith.langchain.com/o/test/projects/p/run";
    failed.spans = failed.spans.slice(0, 1);
    failed.spans[0].status = "error";
    failed.spans[0].error = {
      code: "deadline",
      message: "Model deadline reached.",
    };
    render(<TraceView trace={failed} />);
    expect(screen.getByRole("alert").textContent).toContain(
      "Model deadline reached.",
    );
    expect(
      screen.queryByRole("button", { name: /validate_response/ }),
    ).toBeNull();
    expect(
      screen
        .getByRole("link", { name: "Open in LangSmith" })
        .getAttribute("rel"),
    ).toBe("noopener noreferrer");
  });
});

describe("seat-attributed traces", () => {
  it("adds the player filter and rejects another seat's private trace", async () => {
    const fetcher = vi.fn((url: string) =>
      response(
        url.includes("?")
          ? { items: [], next_cursor: null }
          : { ...trace, metadata: { player: 1 } },
      ),
    );
    vi.stubGlobal("fetch", fetcher);
    render(
      <TraceBrowser {...props} player={2} decisionTraceId={trace.trace_id} />,
    );
    await screen.findByText(/Trace response does not match this decision/);
    expect(fetcher.mock.calls.some(([url]) => url.includes("player=2"))).toBe(
      true,
    );
    expect(screen.queryByRole("region", { name: "Step details" })).toBeNull();
  });
  it("accepts legacy unattributed traces only for seat zero", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        response(
          url.includes("?") ? { items: [trace], next_cursor: null } : trace,
        ),
      ),
    );
    render(<TraceBrowser {...props} player={0} />);
    await screen.findByRole("heading", { name: "Hand 3 · State 12" });
  });
});
