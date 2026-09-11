import { useState } from "react";
import { Search, CheckCircle2, CircleMinus } from "lucide-react";
import type { Snapshot } from "./types";
import { date, Status, Empty } from "./ui";
export function EquipmentPage({ data }: { data: Snapshot }) {
  const [search, setSearch] = useState(""),
    [depot, setDepot] = useState(""),
    [status, setStatus] = useState("");
  const items = data.equipment.filter(
    (e) =>
      (!depot || e.depot_id === depot) &&
      (!status || e.status === status) &&
      `${e.name} ${e.id} ${e.type}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <p>Three depots. One shared view.</p>
          <h1>Equipment with more to give.</h1>
        </div>
        <span className="count-label">
          {data.equipment.filter((e) => e.status === "available").length}{" "}
          available / {data.equipment.length} total
        </span>
      </div>
      <div className="table-controls">
        <div className="inline">
          <select
            aria-label="Filter by depot"
            value={depot}
            onChange={(e) => setDepot(e.target.value)}
          >
            <option value="">All depots</option>
            {data.depots.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Filter by availability"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All statuses</option>
            {["available", "reserved", "on_loan", "inspection", "retired"].map(
              (s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ),
            )}
          </select>
        </div>
        <div className="search">
          <Search size={17} />
          <input
            aria-label="Search equipment"
            placeholder="Search equipment"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      <div className="table-panel">
        <table>
          <thead>
            <tr>
              <th>Equipment</th>
              <th>Depot</th>
              <th>Specifications</th>
              <th>Inspection</th>
              <th>Availability</th>
            </tr>
          </thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id}>
                <td>
                  <strong>{e.name}</strong>
                  <small className="record-id">{e.id}</small>
                </td>
                <td>{data.depots.find((d) => d.id === e.depot_id)?.name}</td>
                <td>
                  {e.min_height_cm}–{e.max_height_cm} cm
                  <small>Up to {e.max_weight_kg} kg</small>
                </td>
                <td>
                  <span className="inline">
                    {e.inspection_passed ? (
                      <CheckCircle2 size={16} />
                    ) : (
                      <CircleMinus size={16} />
                    )}{" "}
                    {e.inspection_passed ? "Passed" : "Required"}
                  </span>
                  {e.inspected_at && <small>{date(e.inspected_at)}</small>}
                </td>
                <td>
                  <Status value={e.status} />
                  {e.loan_until && <small>Until {date(e.loan_until)}</small>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!items.length && <Empty>No matching equipment.</Empty>}
      </div>
      <p className="table-caption">
        All specifications and inspection records are fictional demo data.
      </p>
    </>
  );
}
