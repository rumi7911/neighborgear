import { useState } from "react";
import {
  Search,
  ArrowUpRight,
  ClipboardList,
  CircleAlert,
  Network,
  Plus,
  CalendarDays,
} from "lucide-react";
import type { Snapshot } from "./types";
import { date, initials, label, Status, Empty } from "./ui";
const attention = new Set([
  "needs_information",
  "awaiting_approval",
  "needs_attention",
]);
export function RequestsPage({
  data,
  onSelect,
  onCreate,
}: {
  data: Snapshot;
  onSelect: (id: string) => void;
  onCreate: () => void;
}) {
  const [filter, setFilter] = useState("All requests"),
    [search, setSearch] = useState("");
  const filtered = data.requests.filter(
    (r) =>
      (filter === "All requests" ||
        (filter === "Needs attention" && attention.has(r.status)) ||
        (filter === "In progress" &&
          ["reserved", "delivery_scheduled", "on_loan", "inspection"].includes(
            r.status,
          ))) &&
      `${r.name} ${r.text} ${r.id}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <p>Keep equipment moving to the people who need it.</p>
          <h1>
            A little coordination.
            <br className="compact-break" /> A lot of independence.
          </h1>
        </div>
        <button className="button" onClick={onCreate}>
          <Plus size={18} />
          New request
        </button>
      </div>
      <div className="metrics">
        <div>
          <span className="metric-icon">
            <ClipboardList />
          </span>
          <div>
            <strong>
              {data.requests.filter((r) => r.status !== "completed").length}
            </strong>
            <span>Open requests</span>
          </div>
        </div>
        <div>
          <span className="metric-icon amber">
            <CircleAlert />
          </span>
          <div>
            <strong>
              {data.requests.filter((r) => attention.has(r.status)).length}
            </strong>
            <span>Need your review</span>
          </div>
        </div>
        <div>
          <span className="metric-icon">
            <Network />
          </span>
          <div>
            <strong>{data.equipment.length}</strong>
            <span>Items in the network</span>
          </div>
        </div>
      </div>
      <div className="table-controls">
        <div className="tabs" aria-label="Request filters">
          {["All requests", "Needs attention", "In progress"].map((t) => (
            <button
              key={t}
              aria-pressed={filter === t}
              className={filter === t ? "selected" : ""}
              onClick={() => setFilter(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="search">
          <Search size={17} />
          <input
            aria-label="Search requests"
            placeholder="Search requests"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      <div className="table-panel">
        <table>
          <thead>
            <tr>
              <th>Person & request</th>
              <th>Needed by</th>
              <th>Depot</th>
              <th>Status</th>
              <th>
                <span className="sr-only">Open request</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, i) => {
              const item = data.equipment.find(
                (e) =>
                  e.id === r.equipment_id ||
                  e.id === r.candidates?.find((c) => c.eligible)?.equipment_id,
              );
              return (
                <tr key={r.id}>
                  <td>
                    <button className="person" onClick={() => onSelect(r.id)}>
                      <span className={`avatar avatar-${i % 4}`}>
                        {initials(r.name)}
                      </span>
                      <span>
                        <strong>{r.name}</strong>
                        <small>{label(r.equipment_type)}</small>
                      </span>
                    </button>
                  </td>
                  <td>
                    <span className="inline">
                      <CalendarDays size={15} />
                      {date(r.needed_by)}
                    </span>
                  </td>
                  <td>
                    {data.depots.find((d) => d.id === item?.depot_id)?.name ||
                      "Finding a match"}
                  </td>
                  <td>
                    <Status value={r.status} />
                  </td>
                  <td>
                    <button
                      className="icon-button"
                      aria-label={`Open ${r.name}'s request`}
                      onClick={() => onSelect(r.id)}
                    >
                      <ArrowUpRight size={18} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!filtered.length && (
          <Empty>
            No requests match this view. Try another filter or create a request.
          </Empty>
        )}
      </div>
      <p className="table-caption">
        {filtered.length} requests · Each item has another chapter ahead.
      </p>
    </>
  );
}
