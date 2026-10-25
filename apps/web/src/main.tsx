import React, { lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./style.css";

const WorkspacePreview =
  import.meta.env.DEV && window.location.pathname === "/dev/workspace"
    ? lazy(() => import("./dev/WorkspacePreview"))
    : null;
const FixturePreview =
  import.meta.env.DEV && window.location.pathname === "/dev/traces"
    ? lazy(() => import("./trace/FixturePreview"))
    : null;

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {WorkspacePreview ? (
      <Suspense fallback={<p>Loading fixture...</p>}>
        <WorkspacePreview />
      </Suspense>
    ) : FixturePreview ? (
      <Suspense fallback={<p>Loading fixture...</p>}>
        <FixturePreview />
      </Suspense>
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
