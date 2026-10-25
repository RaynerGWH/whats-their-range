import React, { lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./style.css";

const FixturePreview =
  import.meta.env.DEV && window.location.pathname === "/dev/traces"
    ? lazy(() => import("./trace/FixturePreview"))
    : null;

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {FixturePreview ? (
      <Suspense fallback={<p>Loading fixture...</p>}>
        <FixturePreview />
      </Suspense>
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
