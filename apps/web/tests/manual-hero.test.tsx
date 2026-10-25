// @vitest-environment jsdom
import React from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HeroControl } from "../src/workspace/HeroControl";
import { PokerTable, DecisionPanel } from "../src/workspace/Panels";
import { applyPreset, readPreset, savePreset } from "../src/workspace/preset";
import { creationPayload, seatDefaults } from "../src/workspace/data";
import type { ServerConfig, Table, Decision } from "../src/types";
const server: ServerConfig = {
  capabilities: { manual_hero: true, public_chat: true, llm_tables: true },
  openrouter_configured: true,
  default_model: "test/model",
  storage: "sqlite",
  tracing: false,
  max_tables: 2,
  agent_call_limit: 100,
};
const table: Table = {
  id: "manual-table",
  version: 10,
  status: "paused",
  phase: "playing",
  hand: 1,
  street: "preflop",
  level: 1,
  small_blind: 5,
  big_blind: 10,
  hands_to_level: 7,
  button: 1,
  actor: 0,
  board: [],
  pot: 15,
  remaining: 6,
  history: [],
  decision: null,
  series: [],
  icm: {},
  icm_basis: "",
  agent_decisions: 0,
  config: {
    name: "Manual test",
    seed: 1,
    stack_bb: 50,
    hands_per_level: 8,
    payouts: "70/30",
    mode: "openrouter",
    opponents: "llm",
    model: "test/model",
    pace: 1.2,
    player_count: 6,
    hero_seat: 0,
    hero_control: "human",
    seat_configs: seatDefaults(6),
  },
  players: seatDefaults(6).map((s) => ({
    seat: s.seat,
    name: s.name,
    stack: 500,
    bet: 0,
    cards: s.seat === 0 ? ["As", "Js"] : ["Kh", "Qh"],
    active: true,
    eliminated: false,
    position: "BB",
    last_action: null,
    stats: { actions: 0, raises: 0, calls: 0, folds: 0 },
    prize: 0,
    place: null,
  })),
  hero_turn: {
    player: 0,
    state_version: 10,
    chat_sequence: 3,
    turn_token: "opaque-token",
    observation: {
      legal: [
        { key: "fold", kind: "fold", amount: 0 },
        { key: "call", kind: "call", amount: 10 },
        { key: "raise:35", kind: "raise", amount: 35 },
      ],
    },
  },
};
const setup = (
  overrides: Partial<React.ComponentProps<typeof HeroControl>> = {},
) => {
  const props = {
    table,
    server,
    connection: "live",
    replay: false,
    onAction: vi.fn(async () => {}),
    onControl: vi.fn(async () => {}),
    onRefresh: vi.fn(async () => {}),
    ...overrides,
  };
  return { ...render(<HeroControl {...props} />), props };
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});
describe("manual hero", () => {
  it("uses the table message limit and rejects multiline text before submission", () => {
    const { props } = setup({
      table: { ...table, config: { ...table.config, llm_limits: { max_message_chars: 4 } } },
      server: { ...server, llm_limits: { max_message_chars: 8 } },
    });
    fireEvent.click(screen.getByRole("button", { name: "Call 10" }));
    const message = screen.getByRole("textbox", { name: "Public message" });
    const submit = screen.getByRole("button", { name: "Submit call" }) as HTMLButtonElement;
    fireEvent.change(message, { target: { value: "12345" } });
    expect(submit.disabled).toBe(true);
    expect(screen.getByRole("alert").textContent).toContain("at most 4 characters");
    fireEvent.submit(submit.closest("form")!);
    expect(props.onAction).not.toHaveBeenCalled();
    fireEvent.change(message, { target: { value: "a\nb" } });
    expect(submit.disabled).toBe(true);
    // Python counts Unicode code points, so four emoji fit a four-character limit.
    fireEvent.change(message, { target: { value: "🙂🙂🙂🙂" } });
    expect(submit.disabled).toBe(false);
    expect(screen.getByText("4 / 4 characters")).toBeTruthy();
  });
  it("labels a free action Check and submits its exact key", async () => {
    const { props } = setup({ table: {
      ...table,
      hero_turn: { ...table.hero_turn!, observation: { legal: [{ key: "check", kind: "call", amount: 0 }] } },
    } });
    expect(screen.queryByRole("button", { name: "Call 0" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Check" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit check" }));
    await waitFor(() => expect(props.onAction).toHaveBeenCalledTimes(1));
    expect(props.onAction.mock.calls[0][0].action).toBe("check");
  });
  it("submits the selected exact legal key, frozen version/token and optional message once", async () => {
    const { props } = setup();
    expect(
      (
        screen.getByRole("button", {
          name: "Submit action",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Raise to 35" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Public message" }), {
      target: { value: "A public claim" },
    });
    const submit = screen.getByRole("button", { name: "Submit raise to 35" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    await waitFor(() => expect(props.onAction).toHaveBeenCalledTimes(1));
    expect(props.onAction.mock.calls[0][0]).toEqual({
      action: "raise:35",
      state_version: 10,
      turn_token: "opaque-token",
      public_message: "A public claim",
    });
    expect(props.onAction.mock.calls[0][1]).toBeInstanceOf(AbortSignal);
    await screen.findByText("Submitted. Waiting for the table to update.");
    expect((submit as HTMLButtonElement).disabled).toBe(true);
  });
  it("allows silence and never retries a rejected action without explicit refresh", async () => {
    const onAction = vi.fn().mockRejectedValue(new Error("Stale turn (409)."));
    const { props } = setup({ onAction });
    fireEvent.click(screen.getByRole("button", { name: "Call 10" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit call" }));
    await screen.findByRole("alert");
    expect(onAction.mock.calls[0][0]).toEqual({
      action: "call",
      state_version: 10,
      turn_token: "opaque-token",
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit call" }));
    expect(onAction).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Refresh turn" }));
    await waitFor(() => expect(props.onRefresh).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    expect(
      (
        screen.getByRole("button", {
          name: "Submit action",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(onAction).toHaveBeenCalledTimes(1);
  });
  it("switches only hero control at the observed version and waits for the authoritative mode", async () => {
    const { props } = setup();
    fireEvent.click(screen.getByRole("button", { name: "LLM" }));
    expect(props.onControl.mock.calls[0][0]).toEqual({
      action: "set_hero_control",
      hero_control: "llm",
      state_version: 10,
    });
    await screen.findByText(
      "Control change requested. Waiting for the table to update.",
    );
    expect(
      screen
        .getByRole("button", { name: "Manual" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
    expect(props.onAction).not.toHaveBeenCalled();
  });
  it.each(["offline", "replay", "capability", "stale", "wrong-seat"])(
    "prevents action with %s state",
    (condition) => {
      const altered = { ...table, hero_turn: { ...table.hero_turn! } };
      if (condition === "stale") altered.hero_turn.state_version = 9;
      if (condition === "wrong-seat") altered.hero_turn.player = 1;
      setup({
        table: altered,
        connection: condition === "offline" ? "offline" : "live",
        replay: condition === "replay",
        server:
          condition === "capability" ? { ...server, capabilities: {} } : server,
      });
      expect(screen.queryByRole("button", { name: "Call 10" })).toBeNull();
    },
  );
  it("aborts the old request and clears action/message when the turn changes", async () => {
    let reject: (error: Error) => void = () => {};
    const onAction = vi.fn(
      () =>
        new Promise((_resolve, fail) => {
          reject = fail;
        }),
    );
    const { props, rerender } = setup({ onAction });
    fireEvent.click(screen.getByRole("button", { name: "Fold" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Public message" }), {
      target: { value: "old text" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit fold" }));
    const signal = onAction.mock.calls[0][1] as AbortSignal;
    rerender(
      <HeroControl
        {...props}
        table={{
          ...table,
          version: 11,
          hero_turn: {
            ...table.hero_turn!,
            state_version: 11,
            turn_token: "next-token",
          },
        }}
      />,
    );
    expect(signal.aborted).toBe(true);
    reject(new Error("Late rejection"));
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    expect(
      (
        screen.getByRole("textbox", {
          name: "Public message",
        }) as HTMLTextAreaElement
      ).value,
    ).toBe("");
    expect(
      (
        screen.getByRole("button", {
          name: "Submit action",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  });
  it("does not submit chat when disabled", async () => {
    const { props } = setup({
      server: { ...server, capabilities: { manual_hero: true } },
    });
    expect(
      (
        screen.getByRole("textbox", {
          name: "Public message",
        }) as HTMLTextAreaElement
      ).disabled,
    ).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Fold" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit fold" }));
    await waitFor(() => expect(props.onAction).toHaveBeenCalledTimes(1));
    expect(props.onAction.mock.calls[0][0]).not.toHaveProperty(
      "public_message",
    );
  });
});
it("requires explicit inspection to expose opponent cards, even if reveal was set", () => {
  const props = {
    table,
    selected: 1,
    onSelect: vi.fn(),
    reveal: true,
    setReveal: vi.fn(),
  };
  const { rerender } = render(<PokerTable {...props} />);
  expect(screen.getAllByLabelText("Hidden card")).toHaveLength(10);
  expect(
    screen.queryByRole("button", { name: "Hide opponent cards" }),
  ).toBeNull();
  rerender(<PokerTable {...props} inspection />);
  expect(screen.queryAllByLabelText("Hidden card")).toHaveLength(0);
});
it("human decisions do not invent or display model reasoning/execution", () => {
  const decision = {
    source: "human",
    action: "call",
    player: 0,
    state_version: 10,
    summary: "must not display",
    observation: { private: "ignored" },
    trace_id: "not-a-model",
  } as unknown as Decision;
  render(
    <DecisionPanel
      table={{ ...table, decision }}
      seat={0}
      server={server}
      onTrace={vi.fn()}
    />,
  );
  expect(screen.getByText("Source: human. No model execution.")).toBeTruthy();
  expect(screen.queryByText("must not display")).toBeNull();
  expect(
    (
      screen.getByRole("button", {
        name: "Tools and trace",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
});
it("reuses one saved neutral preset for five opponents without altering the hero", () => {
  const preset = {
    model: "test/stable",
    instruction_profile: "free_play" as const,
    harness: "baseline" as const,
    chat_enabled: false,
  };
  savePreset(preset);
  expect(readPreset()).toEqual(preset);
  const seats = seatDefaults(6);
  const result = applyPreset(seats, 2, readPreset()!);
  expect(result[2]).toEqual(seats[2]);
  expect(result.filter((s) => s.model === "test/stable")).toHaveLength(5);
  const payload = creationPayload(
    { ...table.config, player_count: undefined, seat_configs: result },
    server,
  );
  expect(payload.player_count).toBe(6);
  expect(payload.hero_control).toBe("human");
  expect(() =>
    creationPayload(table.config, {
      ...server,
      capabilities: { llm_tables: true },
    }),
  ).toThrow("Choose LLM control explicitly");
});

import App from "../src/App";
const session = {
  tables: [table],
  table,
  live: table,
  server: {
    ...server,
    capabilities: { ...server.capabilities, per_seat_traces: true },
  },
  selected: table.id,
  connection: "live",
  error: "",
  token: "",
  replay: null,
  frames: [],
  historyBusy: false,
  choose: vi.fn(),
  control: vi.fn(),
  create: vi.fn(),
  loadHistory: vi.fn(),
  refresh: vi.fn(),
  setError: vi.fn(),
  setReplay: vi.fn(),
  saveToken: vi.fn(),
};
vi.mock("../src/workspace/useSession", () => ({ useSession: () => session }));
vi.mock("../src/trace/TraceBrowser", () => ({
  default: ({ player }: { player: number }) => (
    <div>Private trace seat {player}</div>
  ),
}));
it("requires explicit spectator inspection before mounting opponent records and trace requests", () => {
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  render(<App />);
  fireEvent.click(
    screen.getByRole("button", { name: "Inspect Player 2, seat 2" }),
  );
  expect(screen.queryByRole("heading", { name: "Player decision" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Tools and trace" })).toBeNull();
  expect(screen.getAllByLabelText("Hidden card")).toHaveLength(10);
  fireEvent.click(screen.getByRole("button", { name: "Spectator inspection" }));
  fireEvent.click(screen.getByRole("button", { name: "Tools and trace" }));
  expect(screen.getByText("Private trace seat 1")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Play", exact: true }));
  expect(screen.queryByText("Private trace seat 1")).toBeNull();
  expect(screen.queryByRole("heading", { name: "Player decision" })).toBeNull();
});
