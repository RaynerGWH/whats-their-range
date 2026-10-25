import { useEffect, useRef, useState } from "react";
import { API, request } from "../api";
import type { Config, ServerConfig, Table } from "../types";

export function useSession() {
  const [tables, setTables] = useState<Table[]>([]);
  const [selected, setSelected] = useState("");
  const [server, setServer] = useState<ServerConfig | null>(null);
  const [connection, setConnection] = useState("connecting");
  const [error, setError] = useState("");
  const [token, setToken] = useState(() => {
    try {
      return sessionStorage.getItem("wtr-token") || "";
    } catch {
      return "";
    }
  });
  const [replay, setReplay] = useState<Table | null>(null);
  const [frames, setFrames] = useState<Table[]>([]);
  const [historyBusy, setHistoryBusy] = useState(false);
  const selection = useRef(selected);
  const historyRequest = useRef<AbortController | null>(null);
  const generation = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    let socket: WebSocket | undefined;
    let timer: ReturnType<typeof setTimeout>;
    setHistoryBusy(false);
    setConnection("connecting");
    setServer(null);
    setTables([]);
    setReplay(null);
    setFrames([]);
    const connect = async () => {
      try {
        const [conf, initial] = await Promise.all([
          request<ServerConfig>("/config", token, undefined, controller.signal),
          request<Table[]>("/tables", token, undefined, controller.signal),
        ]);
        if (controller.signal.aborted) return;
        setServer(conf);
        setTables(initial);
        setSelected((old) =>
          initial.some((table) => table.id === old)
            ? old
            : initial.at(-1)?.id || "",
        );
        setError("");
        socket = new WebSocket(
          `${(API || window.location.origin).replace(/^http/, "ws")}/api/live`,
        );
        socket.onopen = () => {
          if (!controller.signal.aborted)
            socket?.send(JSON.stringify({ token }));
        };
        socket.onmessage = (event) => {
          if (controller.signal.aborted) return;
          const message = JSON.parse(event.data);
          if (message.type === "tables") {
            setConnection("live");
            setTables(message.tables);
            setSelected((old) => old || message.tables.at(-1)?.id || "");
          }
        };
        socket.onclose = () => {
          if (!controller.signal.aborted) {
            setConnection("reconnecting");
            timer = setTimeout(connect, 2000);
          }
        };
        socket.onerror = () => socket?.close();
      } catch (error) {
        if (!controller.signal.aborted) {
          setConnection("offline");
          setError((error as Error).message);
          timer = setTimeout(connect, 4000);
        }
      }
    };
    void connect();
    return () => {
      controller.abort();
      clearTimeout(timer);
      socket?.close();
    };
  }, [token]);
  const choose = (id: string) => {
    generation.current++;
    historyRequest.current?.abort();
    selection.current = id;
    setSelected(id);
    setReplay(null);
    setFrames([]);
    setHistoryBusy(false);
  };
  useEffect(() => {
    selection.current = selected;
    return () => {
      generation.current++;
      historyRequest.current?.abort();
    };
  }, [selected, token]);
  const live = tables.find((table) => table.id === selected);
  const control = async (action: string, pace?: number) => {
    if (!live) return;
    try {
      await request(`/tables/${encodeURIComponent(live.id)}/control`, token, {
        action,
        pace,
      });
      setError("");
    } catch (error) {
      setError((error as Error).message);
    }
  };
  const create = async (config: Config) => {
    const result = await request<{ id: string }>("/tables", token, config);
    choose(result.id);
    setError("");
  };
  const loadHistory = async (older = false) => {
    if (!live || (older && !frames.length)) return;
    historyRequest.current?.abort();
    const controller = new AbortController();
    historyRequest.current = controller;
    const requestGeneration = generation.current;
    setHistoryBusy(true);
    try {
      const data = await request<Table[]>(
        `/tables/${encodeURIComponent(live.id)}/history${older ? `?before=${frames[0].version}` : ""}`,
        token,
        undefined,
        controller.signal,
      );
      if (controller.signal.aborted || requestGeneration !== generation.current)
        return;
      if (data.some((frame) => frame.id !== live.id))
        throw new Error("Replay response does not match this table.");
      setFrames((old) => (older ? [...data, ...old] : data));
      if (!older && data.length) setReplay(data.at(-1)!);
      if (older && !data.length)
        setError("You have reached the beginning of this session.");
    } catch (error) {
      if (
        !controller.signal.aborted &&
        requestGeneration === generation.current
      )
        setError((error as Error).message);
    } finally {
      if (
        !controller.signal.aborted &&
        requestGeneration === generation.current
      )
        setHistoryBusy(false);
    }
  };
  const saveToken = (value: string) => {
    try {
      sessionStorage.setItem("wtr-token", value);
    } catch {}
    setToken(value);
  };
  return {
    tables,
    selected,
    server,
    connection,
    error,
    setError,
    token,
    saveToken,
    live,
    table: replay || live,
    replay,
    setReplay,
    frames,
    historyBusy,
    choose,
    control,
    create,
    loadHistory,
  };
}
