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
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeSwitch, themeKey } from "../src/theme";
import {
  creationPayload,
  decisionFor,
  seatDefaults,
  supports,
  visibleChat,
} from "../src/workspace/data";
import { CreateDialog } from "../src/workspace/Dialogs";
import { DecisionPanel, PokerTable, PublicChat } from "../src/workspace/Panels";
import type { Config, Decision, ServerConfig, Table } from "../src/types";

const config: Config = {
  name: "Test table",
  seed: 1,
  stack_bb: 50,
  hands_per_level: 8,
  payouts: "70/30",
  mode: "heuristic",
  opponents: "pokerth",
  model: "",
  pace: 1.2,
};
const server: ServerConfig = {
  openrouter_configured: true,
  default_model: "test/default",
  tracing: false,
  storage: "sqlite",
  max_tables: 2,
  agent_call_limit: 100,
};
const decision: Decision = {
  action: "check",
  source: "heuristic",
  model: null,
  summary: "Private hero summary",
  uncertainty: "Limited evidence",
  evidence_ids: [],
  evidence: [],
  observation: { hole: ["As", "Js"] },
  latency_ms: 20,
  state_version: 10,
  hand: 1,
  street: "flop",
  event_id: "event-1",
  fallback: null,
  calls: 0,
  usage: {},
};
const table: Table = {
  id: "one",
  config,
  status: "paused",
  phase: "playing",
  version: 10,
  hand: 1,
  street: "flop",
  level: 1,
  small_blind: 5,
  big_blind: 10,
  hands_to_level: 7,
  button: 1,
  actor: 0,
  players: [0, 1].map((seat) => ({
    seat,
    name: `Player ${seat + 1}`,
    stack: 500,
    bet: 0,
    cards: seat === 0 ? ["As", "Js"] : ["Kh", "Qh"],
    active: true,
    eliminated: false,
    position: "BB",
    last_action: "check",
    stats: { actions: 1, raises: 0, calls: 0, folds: 0 },
    prize: 0,
    place: null,
  })),
  board: [],
  pot: 20,
  remaining: 2,
  history: [],
  decision,
  series: [],
  icm: {},
  icm_basis: "Hand start",
  agent_decisions: 1,
};
beforeEach(() => {
  localStorage.clear();
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function () {
      this.setAttribute("open", "");
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value: function () {
      this.removeAttribute("open");
    },
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("theme choice", () => {
  it("follows system until an explicit choice is saved, then survives remount", () => {
    let listener: () => void = () => {};
    const media = {
      matches: true,
      addEventListener: vi.fn((_name, fn) => {
        listener = fn;
      }),
      removeEventListener: vi.fn(),
    };
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => media),
    );
    const view = render(<ThemeSwitch />);
    expect(document.documentElement.dataset.theme).toBe("dark");
    media.matches = false;
    act(() => listener());
    expect(document.documentElement.dataset.theme).toBe("light");
    fireEvent.change(screen.getByRole("combobox", { name: "Theme" }), {
      target: { value: "dark" },
    });
    expect(localStorage.getItem(themeKey)).toBe("dark");
    view.unmount();
    render(<ThemeSwitch />);
    expect(document.documentElement.dataset.theme).toBe("dark");
    fireEvent.change(screen.getByRole("combobox", { name: "Theme" }), {
      target: { value: "system" },
    });
    expect(localStorage.getItem(themeKey)).toBeNull();
    expect(document.documentElement.dataset.theme).toBe("light");
  });
  it("works when storage is blocked", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
      removeItem: () => {
        throw new Error("blocked");
      },
    });
    vi.stubGlobal("matchMedia", () => ({
      matches: false,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
    render(<ThemeSwitch />);
    fireEvent.change(screen.getByRole("combobox", { name: "Theme" }), {
      target: { value: "dark" },
    });
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
describe("capability-aware creation", () => {
  it("preserves the baseline payload and rejects LLM creation without capability", () => {
    expect(supports(server, "llm_tables")).toBe(false);
    expect(
      creationPayload(
        {
          ...config,
          player_count: 4,
          hero_seat: 2,
          seat_configs: seatDefaults(4),
        },
        server,
      ),
    ).toEqual(config);
    expect(() =>
      creationPayload({ ...config, opponents: "llm" }, server),
    ).toThrow("unavailable");
  });
  it("uses free play only, table model defaults, independent overrides and no unsupported chat", () => {
    const capable = { ...server, capabilities: { llm_tables: true } };
    const seats = seatDefaults(4);
    seats[2].model = "test/override";
    seats[1].chat_enabled = false;
    const result = creationPayload(
      { ...config, opponents: "llm", seat_configs: seats, hero_seat: 2 },
      capable,
    );
    expect(result.player_count).toBe(6);
    expect(result.mode).toBe("openrouter");
    expect(result.seat_configs?.[2].model).toBe("test/override");
    expect(
      result.seat_configs?.every(
        (seat) =>
          seat.instruction_profile === "free_play" &&
          seat.harness === "baseline" &&
          !seat.chat_enabled,
      ),
    ).toBe(true);
    expect(() =>
      creationPayload(
        { ...config, opponents: "llm" },
        { ...capable, default_model: "" },
      ),
    ).toThrow("Set a default model");
  });
  it("disables unsupported LLM controls while keeping real PokerTH creation available", () => {
    render(
      <CreateDialog
        server={server}
        count={0}
        onClose={() => {}}
        onCreate={vi.fn()}
      />,
    );
    expect(
      (
        screen.getByRole("option", {
          name: "LLM players (unavailable)",
        }) as HTMLOptionElement
      ).disabled,
    ).toBe(true);
    expect(
      (screen.getByRole("combobox", { name: "Players" }) as HTMLSelectElement)
        .value,
    ).toBe("6");
    expect(screen.getByRole("button", { name: "Create table" })).toBeTruthy();
  });
  it("shows six neutral LLM seats and only supported profiles/harnesses", () => {
    render(
      <CreateDialog
        server={{
          ...server,
          capabilities: { llm_tables: true, public_chat: true },
        }}
        count={0}
        onClose={() => {}}
        onCreate={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByRole("combobox", { name: "Opponents" }), {
      target: { value: "llm" },
    });
    expect(
      (screen.getByRole("combobox", { name: "Players" }) as HTMLSelectElement)
        .value,
    ).toBe("6");
    const profile = screen.getByRole("combobox", {
      name: "Seat 1 instruction profile",
    });
    expect(
      within(profile)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Free play"]);
    expect(
      within(screen.getByRole("combobox", { name: "Seat 1 harness" }))
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Baseline"]);
    fireEvent.change(screen.getByRole("combobox", { name: "Players" }), {
      target: { value: "4" },
    });
    expect(screen.queryByRole("textbox", { name: "Seat 6 model" })).toBeNull();
  });
});
describe("player and public chat boundaries", () => {
  it("never assigns the legacy hero record to another player", () => {
    expect(decisionFor(table, 0)).toEqual(decision);
    expect(decisionFor(table, 1)).toBeNull();
    expect(
      decisionFor({ ...table, config: { ...config, hero_seat: 1 } }, 1),
    ).toBeNull();
    expect(
      decisionFor(
        { ...table, decisions_by_player: { "1": { ...decision, player: 0 } } },
        1,
      ),
    ).toBeNull();
    expect(
      decisionFor(
        { ...table, decisions_by_player: { "1": { ...decision, player: 1 } } },
        1,
      )?.player,
    ).toBe(1);
    expect(decisionFor({ ...table, version: 9 }, 0)).toBeNull();
  });
  it("only displays chat within the snapshot cutoff, ordered by sequence", () => {
    const chat = [
      {
        id: "later",
        sequence: 3,
        player: 1,
        hand: 1,
        state_version: 11,
        text: "future claim",
      },
      {
        id: "two",
        sequence: 2,
        player: 1,
        hand: 1,
        state_version: 10,
        text: "public claim",
      },
      {
        id: "one",
        sequence: 1,
        player: 0,
        hand: 1,
        state_version: 9,
        text: "earlier claim",
      },
    ];
    const snapshot = { ...table, chat, chat_sequence: 2 };
    expect(visibleChat(snapshot).map((message) => message.id)).toEqual([
      "one",
      "two",
    ]);
    render(<PublicChat table={snapshot} server={server} replay />);
    expect(screen.getByText("public claim")).toBeTruthy();
    expect(screen.queryByText("future claim")).toBeNull();
    expect(screen.queryByText("Private hero summary")).toBeNull();
    expect(visibleChat({ ...table, chat })).toEqual([]);
  });
  it("does not imply PokerTH opponents have LLM traces", () => {
    render(
      <DecisionPanel
        table={table}
        seat={1}
        server={server}
        onTrace={vi.fn()}
      />,
    );
    expect(
      screen.getByText("PokerTH does not record LLM decisions."),
    ).toBeTruthy();
    expect(
      (
        screen.getByRole("button", {
          name: "Tools and trace",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(screen.queryByText("Private hero summary")).toBeNull();
  });
  it("shows only the selected player's permitted input and keeps table cards hidden", () => {
    const perSeat = {
      ...table,
      config: { ...config, opponents: "llm" as const },
      decisions_by_player: {
        "1": { ...decision, player: 1, observation: { hole: ["Kh", "Qh"] } },
      },
    };
    render(
      <DecisionPanel
        table={perSeat}
        seat={1}
        server={{ ...server, capabilities: { per_seat_traces: true } }}
        onTrace={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Raw input" }));
    expect(
      screen.getByLabelText("Selected player input").textContent,
    ).toContain("Kh");
    expect(
      screen.getByLabelText("Selected player input").textContent,
    ).not.toContain("As");
    render(
      <PokerTable
        table={perSeat}
        selected={1}
        onSelect={vi.fn()}
        reveal={false}
        setReveal={vi.fn()}
      />,
    );
    expect(screen.getAllByLabelText("Hidden card")).toHaveLength(2);
  });
});
