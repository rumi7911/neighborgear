import { useCallback, useEffect, useRef, useState } from "react";
import {
  ClipboardList,
  Package,
  Warehouse,
  Users,
  FlaskConical,
  ChevronDown,
  Info,
  Plus,
  RotateCcw,
  Truck,
  Check,
  ArrowRight,
  Leaf,
  X,
  LoaderCircle,
} from "lucide-react";
import { initialize, mutate, snapshot, forgetSession } from "./api";
import type { Snapshot } from "./types";
import { RequestsPage } from "./RequestsPage";
import { EquipmentPage } from "./EquipmentPage";
import { RequestDetail } from "./RequestDetail";
import { RequestForm } from "./RequestForm";
import { date, Modal } from "./ui";
export default function App() {
  const [data, setData] = useState<Snapshot>(),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [page, setPage] = useState("requests"),
    [selected, setSelected] = useState<string>(),
    [form, setForm] = useState<"new" | "clarify">(),
    [demo, setDemo] = useState(false),
    [reset, setReset] = useState(false),
    [judge, setJudge] = useState("");
  const fetching = useRef(false);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [page, selected]);
  const running =
    data?.runs.filter((r) => ["queued", "running"].includes(r.status)).length ||
    0;
  const refresh = useCallback(async () => {
    if (fetching.current) return;
    fetching.current = true;
    try {
      await initialize();
      setData(await snapshot());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      fetching.current = false;
    }
  }, []);
  useEffect(() => {
    void refresh();
    const interval = setInterval(() => void refresh(), running ? 1500 : 5000);
    return () => clearInterval(interval);
  }, [refresh, running]);
  async function action(path: string, body: unknown = {}) {
    setBusy(true);
    setError("");
    try {
      const result = await mutate(path, body);
      await refresh();
      return result;
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setBusy(false);
    }
  }
  const detail = data?.requests.find((r) => r.id === selected);
  if (!data)
    return (
      <div className="loading">
        <div className="brand">
          <span className="brand-mark" />
          NeighborGear
        </div>
        <h1>
          A little coordination.
          <br />A lot of independence.
        </h1>
        {error ? (
          <>
            <p role="alert" className="error">
              {error}
            </p>
            <label>
              Judge access key (if required)
              <input
                value={judge}
                onChange={(e) => setJudge(e.target.value)}
                type="password"
                autoComplete="off"
              />
            </label>
            <button
              className="button"
              onClick={() => {
                if (judge) sessionStorage.setItem("neighborgear.judge", judge);
                setError("");
                void refresh();
              }}
            >
              Try again
              <ArrowRight size={16} />
            </button>
            <button
              className="button secondary"
              onClick={() => {
                forgetSession();
                setError("");
                void refresh();
              }}
            >
              Open a new sandbox
            </button>
          </>
        ) : (
          <p className="inline">
            <LoaderCircle className="spin" size={18} />
            Opening your community workspace…
          </p>
        )}
      </div>
    );
  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <a
          href="#requests"
          className="brand"
          onClick={() => {
            setPage("requests");
            setSelected(undefined);
          }}
        >
          <span className="brand-mark" />
          NeighborGear
        </a>
        <nav aria-label="Main navigation">
          <button
            className={page === "requests" ? "active" : ""}
            onClick={() => {
              setPage("requests");
              setSelected(undefined);
            }}
          >
            <ClipboardList size={20} />
            Requests
          </button>
          <button
            className={page === "equipment" ? "active" : ""}
            onClick={() => {
              setPage("equipment");
              setSelected(undefined);
            }}
          >
            <Package size={20} />
            Equipment
          </button>
        </nav>
        <div className="depot-list">
          <h2>Depots</h2>
          {data.depots.map((d) => (
            <div className="depot" key={d.id}>
              <Warehouse size={24} />
              <div>
                <strong>{d.name}</strong>
                <small>
                  {
                    data.equipment.filter(
                      (e) => e.depot_id === d.id && e.status === "available",
                    ).length
                  }{" "}
                  items available
                </small>
              </div>
            </div>
          ))}
          <div className="fictional">
            <Users size={19} />
            Fictional demo network
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            Workspace <span>/</span>{" "}
            <strong>
              {page === "equipment"
                ? "Equipment"
                : detail
                  ? detail.name
                  : "Requests"}
            </strong>
          </div>
          <button
            className="demo-toggle"
            onClick={() => setDemo(!demo)}
            aria-expanded={demo}
          >
            <FlaskConical size={18} />
            Demo controls
            <ChevronDown size={16} />
          </button>
        </header>
        {demo && (
          <div className="demo-bar">
            <span>
              Scenario date:{" "}
              <strong>
                {date(data.session.now)} {data.session.now.slice(0, 4)}
              </strong>
            </span>
            <button
              className="button secondary small"
              disabled={busy}
              onClick={() => void action("/clock", { days: 1 }).catch(() => {})}
            >
              <Plus size={14} />1 day
            </button>
            <button
              className="button secondary small"
              disabled={busy}
              onClick={() =>
                void action("/clock", { days: 14 }).catch(() => {})
              }
            >
              14 days
            </button>
            <button
              className="button secondary small"
              disabled={busy}
              onClick={() => setReset(true)}
            >
              <RotateCcw size={14} />
              Reset sandbox
            </button>
            <small>Changes affect only your fictional workspace.</small>
          </div>
        )}
        {error && (
          <div className="error global-error" role="alert">
            <span>{error}</span>
            <button
              className="icon-button"
              aria-label="Dismiss error"
              onClick={() => setError("")}
            >
              <X size={16} />
            </button>
          </div>
        )}
        <div className={`workspace-body ${detail ? "detail-layout" : ""}`}>
          <main id="main">
            {data.runs
              .filter(
                (run) =>
                  run.status === "failed" &&
                  (!run.request_id ||
                    !data.requests.some((r) => r.id === run.request_id)),
              )
              .map((run) => (
                <section className="run-error" key={run.id} role="alert">
                  <strong>Coordination could not finish</strong>
                  <p>{run.error}</p>
                  <button
                    className="button secondary small"
                    disabled={busy || running > 0}
                    onClick={() =>
                      void action(`/runs/${run.id}/retry`).catch(() => {})
                    }
                  >
                    Retry this run
                  </button>
                </section>
              ))}
            {selected && !detail && running > 0 && (
              <p className="inline" role="status">
                <LoaderCircle size={18} className="spin" />
                Processing your new request. You can leave this page; progress
                is saved.
              </p>
            )}
            {page === "equipment" ? (
              <EquipmentPage data={data} />
            ) : detail ? (
              <RequestDetail
                key={detail.id}
                data={data}
                request={detail}
                onBack={() => setSelected(undefined)}
                onClarify={() => setForm("clarify")}
                onAction={async (p, b) => {
                  await action(p, b);
                }}
                busy={busy || running > 0}
              />
            ) : (
              <RequestsPage
                data={data}
                onSelect={setSelected}
                onCreate={() => setForm("new")}
              />
            )}
          </main>
          {!detail && (
            <aside className="guide">
              <h2>How it works</h2>
              {[
                {
                  icon: ClipboardList,
                  title: "Request",
                  text: "Someone asks for equipment.",
                },
                {
                  icon: Users,
                  title: "Review",
                  text: "Staff confirm the right match.",
                },
                {
                  icon: Truck,
                  title: "Coordinate",
                  text: "Arrange a pickup or delivery. Handle the changes.",
                },
                {
                  icon: RotateCcw,
                  title: "Return",
                  text: "Items come back, get checked, and help someone else.",
                },
              ].map(({ icon: Icon, title, text }, i) => (
                <div className="guide-step" key={title}>
                  <span>{i + 1}</span>
                  <Icon size={25} />
                  <div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                  </div>
                </div>
              ))}
              <div className="second-life">
                <Leaf size={32} />
                <h3>Built for a second life</h3>
                <p>Quality equipment deserves to keep making life better.</p>
                <span className="life-path">
                  <Package size={26} />
                  <ArrowRight size={17} />
                  <Users size={26} />
                  <ArrowRight size={17} />
                  <RotateCcw size={26} />
                </span>
              </div>
            </aside>
          )}
        </div>
        <footer className="mode-banner">
          <Info size={17} />
          <span>
            <strong>
              {data.session.mode === "simulator"
                ? "Simulation mode"
                : "Live Strands mode"}
            </strong>{" "}
            · Fictional data and simulated messages.
            {data.session.mode === "simulator"
              ? " Live AI requires verified AWS credits."
              : ""}
          </span>
          <span className="run-indicator" aria-live="polite">
            {running > 0 ? (
              <>
                <LoaderCircle className="spin" size={14} />
                {running} coordinating
              </>
            ) : (
              <>
                <Check size={14} />
                Up to date
              </>
            )}
          </span>
        </footer>
      </div>
      {form && (
        <RequestForm
          data={data}
          request={form === "clarify" ? detail : undefined}
          onClose={() => setForm(undefined)}
          onSubmit={async (body) => {
            const result = await action(
              form === "clarify"
                ? `/requests/${detail!.id}/clarify`
                : "/requests",
              body,
            );
            if (result.request_id) {
              setSelected(result.request_id);
              setPage("requests");
            }
          }}
        />
      )}
      {reset && (
        <Modal title="Start a fresh sandbox?" onClose={() => setReset(false)}>
          <div className="review-body">
            <p>
              This replaces your fictional requests and activity with the
              original demo network. Other visitors’ workspaces are unaffected.
            </p>
            <div className="modal-footer">
              <button
                className="button secondary"
                onClick={() => setReset(false)}
              >
                Keep this workspace
              </button>
              <button
                className="button"
                disabled={busy}
                onClick={async () => {
                  try {
                    await action("/reset");
                    setSelected(undefined);
                    setReset(false);
                  } catch {}
                }}
              >
                Reset sandbox
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
