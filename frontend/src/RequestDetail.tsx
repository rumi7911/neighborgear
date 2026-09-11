import { useState } from "react";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  CalendarDays,
  Truck,
  RotateCcw,
  ShieldCheck,
  XCircle,
  MessageSquare,
  AlertCircle,
  ChevronDown,
  ArrowRight,
} from "lucide-react";
import type { Request, Snapshot } from "./types";
import { date, initials, label, Modal, Status, Empty } from "./ui";
export function RequestDetail({
  data,
  request: r,
  onBack,
  onClarify,
  onAction,
  busy,
}: {
  data: Snapshot;
  request: Request;
  onBack: () => void;
  onClarify: () => void;
  onAction: (path: string, body: unknown) => Promise<void>;
  busy: boolean;
}) {
  const [candidate, setCandidate] = useState<string>(),
    [approved, setApproved] = useState(false),
    [reviewError, setReviewError] = useState("");
  const selected = data.equipment.find((e) => e.id === candidate),
    item = data.equipment.find((e) => e.id === r.equipment_id),
    driver = data.drivers.find((d) => d.id === r.driver_id);
  const events = data.events.filter((e) => e.request_id === r.id),
    messages = data.messages.filter((m) => m.request_id === r.id),
    runs = data.runs.filter((run) => run.request_id === r.id);
  const act = (type: string) =>
    onAction(`/requests/${r.id}/events`, {
      type,
      ...(type === "cancel_driver" ? { driver_id: r.driver_id } : {}),
    }).catch(() => {});
  return (
    <>
      <button className="back" onClick={onBack}>
        <ArrowLeft size={16} />
        All requests
      </button>
      <div className="detail-heading">
        <span className="avatar large">{initials(r.name)}</span>
        <div>
          <h1>{r.name}</h1>
          <p>
            {label(r.equipment_type)} <span className="separator">/</span>{" "}
            {r.area || "Area needed"}
          </p>
        </div>
        <Status value={r.status} />
      </div>
      <div className="detail-grid">
        <div className="detail-main">
          <section className="panel">
            <div className="section-heading">
              <h2>The request</h2>
              <span className="record-id">{r.id.slice(0, 12)}</span>
            </div>
            <blockquote>{r.text}</blockquote>
            <div className="spec-grid">
              <div>
                <small>Needed by</small>
                <strong>{date(r.needed_by)}</strong>
              </div>
              <div>
                <small>Return by</small>
                <strong>{date(r.return_by)}</strong>
              </div>
              <div>
                <small>Handle height</small>
                <strong>
                  {r.min_height_cm && r.max_height_cm
                    ? `${r.min_height_cm}–${r.max_height_cm} cm`
                    : "Details needed"}
                </strong>
              </div>
              <div>
                <small>User weight</small>
                <strong>
                  {r.user_weight_kg
                    ? `${r.user_weight_kg} kg`
                    : "Details needed"}
                </strong>
              </div>
              <div>
                <small>Delivery window</small>
                <strong>
                  {r.window_start || "—"}–{r.window_end || "—"}
                </strong>
              </div>
            </div>
            {r.status === "needs_information" && (
              <div className="attention-box">
                <AlertCircle size={20} />
                <div>
                  <strong>A few details will help us find a match.</strong>
                  <p>{r.missing_fields.map(label).join(", ")}</p>
                  <button className="button small" onClick={onClarify}>
                    Add missing details
                    <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </section>
          {r.candidates?.length > 0 && (
            <section className="panel">
              <div className="section-heading">
                <div>
                  <h2>Matches across the network</h2>
                  <p className="muted">
                    Proposal snapshot from the last review. Availability is
                    rechecked before reservation.
                  </p>
                </div>
                <span className="count-label">
                  {r.candidates.filter((c) => c.eligible).length} eligible
                </span>
              </div>
              <div className="candidate-list">
                {r.candidates
                  .filter((c) => c.eligible)
                  .map((c) => {
                    const e = data.equipment.find(
                      (item) => item.id === c.equipment_id,
                    );
                    return (
                      e && (
                        <div className="candidate" key={e.id}>
                          <div className="candidate-icon">
                            <CheckCircle2 size={22} />
                          </div>
                          <div>
                            <h3>{e.name}</h3>
                            <p>
                              {
                                data.depots.find((d) => d.id === e.depot_id)
                                  ?.name
                              }{" "}
                              · {e.min_height_cm}–{e.max_height_cm} cm ·{" "}
                              {e.max_weight_kg} kg max.
                            </p>
                            <small>
                              {e.id} ·{" "}
                              {e.inspection_passed
                                ? "Inspection passed"
                                : "Inspection required"}
                            </small>
                            {c.reasons.map((reason) => (
                              <small key={reason}>{reason}</small>
                            ))}
                          </div>
                          {r.status === "awaiting_approval" && (
                            <button
                              className="button secondary small"
                              disabled={busy}
                              onClick={() => {
                                setCandidate(e.id);
                                setApproved(false);
                                setReviewError("");
                              }}
                            >
                              Review match
                            </button>
                          )}
                          {r.equipment_id === e.id && (
                            <Status value={e.status} />
                          )}
                        </div>
                      )
                    );
                  })}
              </div>
              <details className="excluded">
                <summary>
                  <ChevronDown size={16} />
                  {r.candidates.filter((c) => !c.eligible).length} items
                  excluded from this match
                </summary>
                {r.candidates
                  .filter((c) => !c.eligible)
                  .map((c) => (
                    <div key={c.equipment_id}>
                      <XCircle size={16} />
                      <p>
                        <strong>
                          {data.equipment.find((e) => e.id === c.equipment_id)
                            ?.name || c.equipment_id}
                        </strong>
                        <small>{c.reasons.join(" · ")}</small>
                      </p>
                    </div>
                  ))}
              </details>
            </section>
          )}
          {item && (
            <section className="panel">
              <div className="section-heading">
                <h2>Loan & delivery</h2>
                <Truck size={20} />
              </div>
              <div className="spec-grid">
                <div>
                  <small>Reserved equipment</small>
                  <strong>{item.name}</strong>
                </div>
                <div>
                  <small>Assigned driver</small>
                  <strong>{driver?.name || "Awaiting assignment"}</strong>
                </div>
                <div>
                  <small>Delivery date</small>
                  <strong>{date(r.delivery_date)}</strong>
                </div>
              </div>
              <div className="actions">
                {r.status === "delivery_scheduled" && (
                  <>
                    <button
                      className="button small"
                      disabled={busy}
                      onClick={() => act("confirm_delivery")}
                    >
                      <Check size={16} />
                      Confirm delivery
                    </button>
                    <button
                      className="button secondary small"
                      disabled={busy}
                      onClick={() => act("cancel_driver")}
                    >
                      Simulate driver cancellation
                    </button>
                  </>
                )}
                {r.status === "on_loan" && (
                  <button
                    className="button small"
                    disabled={busy}
                    onClick={() => act("return_equipment")}
                  >
                    <RotateCcw size={16} />
                    Record return
                  </button>
                )}
                {r.status === "inspection" && (
                  <>
                    <button
                      className="button small"
                      disabled={busy}
                      onClick={() => act("pass_inspection")}
                    >
                      <ShieldCheck size={16} />
                      Record inspection pass
                    </button>
                    <button
                      className="button secondary small"
                      disabled={busy}
                      onClick={() => act("fail_inspection")}
                    >
                      Record inspection failure
                    </button>
                  </>
                )}
                {r.status === "completed" && (
                  <p className="inline">
                    <CheckCircle2 size={18} />
                    {item.status === "available"
                      ? "Ready to help someone else."
                      : "Item retired from circulation."}
                  </p>
                )}
              </div>
              <p className="field-hint">
                Demo controls record fictional operational confirmations.
              </p>
            </section>
          )}
          {r.status === "needs_attention" && (
            <div className="attention-box">
              <AlertCircle size={20} />
              <div>
                <strong>This request needs a coordinator.</strong>
                <p>
                  {r.equipment_id
                    ? `Can staff arrange alternative transport to ${r.area} by ${date(r.needed_by)}, within ${r.window_start}–${r.window_end}? No eligible volunteer is available. The item remains reserved; no external transport has been booked.`
                    : "Can staff verify the supplied specifications or source equipment outside this network? No current item meets all constraints. Do not relax specifications without staff review."}
                </p>
                {!r.equipment_id && (
                  <button
                    className="button secondary small"
                    disabled={busy}
                    onClick={onClarify}
                  >
                    Review supplied details
                  </button>
                )}
              </div>
            </div>
          )}
          <section className="panel">
            <div className="section-heading">
              <h2>Correspondence</h2>
              <MessageSquare size={19} />
            </div>
            <p className="muted">
              Simulated outbox · No messages are sent externally.
            </p>
            {messages.length ? (
              messages.map((m) => (
                <details className="message" key={m.id}>
                  <summary>
                    <strong>{m.subject}</strong>
                    <small>To {m.recipient}</small>
                  </summary>
                  <p>{m.body}</p>
                </details>
              ))
            ) : (
              <Empty>
                Updates will appear here as coordination progresses.
              </Empty>
            )}
          </section>
        </div>
        <aside className="activity-panel">
          <h2>Activity</h2>
          <p className="muted">A record of what happened.</p>
          {runs
            .filter((run) => run.status === "failed")
            .map((run) => (
              <div className="run-error" key={run.id}>
                <AlertCircle size={18} />
                <strong>Coordination paused</strong>
                <p>{run.error}</p>
                <button
                  className="button secondary small"
                  disabled={busy}
                  onClick={() =>
                    void onAction(`/runs/${run.id}/retry`, {}).catch(() => {})
                  }
                >
                  Retry this run
                </button>
              </div>
            ))}
          {runs.some((run) => ["queued", "running"].includes(run.status)) && (
            <div className="processing">
              <span className="pulse" />
              Coordinating this request…
            </div>
          )}
          <ol className="timeline">
            {[...events].reverse().map((e) => (
              <li key={e.id}>
                <span className="timeline-dot" />
                <div>
                  <strong>{label(e.type)}</strong>
                  <p>{e.summary}</p>
                  <time>
                    {new Date(e.created_at).toLocaleString("en-GB", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </time>
                </div>
              </li>
            ))}
          </ol>
          {!events.length && (
            <Empty>Activity appears when this request is processed.</Empty>
          )}
        </aside>
      </div>
      {selected && (
        <Modal
          title="Review equipment suitability"
          onClose={() => setCandidate(undefined)}
        >
          <div className="review-body">
            <h3>{selected.name}</h3>
            <p>{data.depots.find((d) => d.id === selected.depot_id)?.name}</p>
            <div className="spec-grid">
              <div>
                <small>Height range</small>
                <strong>
                  {selected.min_height_cm}–{selected.max_height_cm} cm
                </strong>
              </div>
              <div>
                <small>Maximum weight</small>
                <strong>{selected.max_weight_kg} kg</strong>
              </div>
            </div>
            <p>
              The match meets the recorded specifications. Confirm the staff
              review to reserve this item for {r.name}.
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={approved}
                onChange={(e) => setApproved(e.target.checked)}
              />
              I have reviewed this fictional match and confirm suitability.
            </label>
            {reviewError && (
              <p className="error" role="alert">
                {reviewError}
              </p>
            )}
            <div className="modal-footer">
              <button
                className="button secondary"
                onClick={() => setCandidate(undefined)}
              >
                Back
              </button>
              <button
                className="button"
                disabled={!approved || busy}
                onClick={async () => {
                  try {
                    await onAction(`/requests/${r.id}/approve`, {
                      equipment_id: selected.id,
                      proposal_version: r.proposal_version,
                    });
                    setCandidate(undefined);
                  } catch (e) {
                    setReviewError((e as Error).message);
                  }
                }}
              >
                Approve & reserve
                <Check size={16} />
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
