import type { SeatConfig } from "../types";
export const presetKey = "wtr-neutral-opponents-v1";
export type OpponentPreset = Pick<
  SeatConfig,
  "model" | "instruction_profile" | "harness" | "chat_enabled"
> & { seats?: SeatConfig[] };
export function readPreset(): OpponentPreset | null {
  try {
    const value = JSON.parse(localStorage.getItem(presetKey) || "null");
    return value &&
      typeof value.model === "string" &&
      typeof value.chat_enabled === "boolean"
      ? {
          model: value.model,
          chat_enabled: value.chat_enabled,
          instruction_profile: "free_play",
          harness: "baseline",
          ...(Array.isArray(value.seats)
            ? {
                seats: value.seats
                  .filter(
                    (seat: SeatConfig) =>
                      Number.isInteger(seat.seat) &&
                      typeof seat.model === "string" &&
                      typeof seat.name === "string" &&
                      typeof seat.chat_enabled === "boolean",
                  )
                  .map((seat: SeatConfig) => ({
                    ...seat,
                    instruction_profile: "free_play",
                    harness: "baseline",
                  })),
              }
            : {}),
        }
      : null;
  } catch {
    return null;
  }
}
export function applyPreset(
  seats: SeatConfig[],
  hero: number,
  preset: OpponentPreset,
): SeatConfig[] {
  const { seats: overrides, ...common } = preset;
  return seats.map((seat) =>
    seat.seat === hero
      ? seat
      : {
          ...seat,
          ...common,
          ...overrides?.find((item) => item.seat === seat.seat),
        },
  );
}
export function savePreset(preset: OpponentPreset) {
  localStorage.setItem(presetKey, JSON.stringify(preset));
}
