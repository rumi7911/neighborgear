import { useState, type FormEvent } from "react";
import { ArrowRight } from "lucide-react";
import type { Request, Snapshot } from "./types";
import { label, Modal } from "./ui";
export function RequestForm({
  data,
  request,
  onSubmit,
  onClose,
}: {
  data: Snapshot;
  request?: Request;
  onSubmit: (body: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
}) {
  const [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError("");
    const f = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    for (const [k, v] of f.entries())
      if (v !== "")
        body[k] = ["min_height_cm", "max_height_cm", "user_weight_kg"].includes(
          k,
        )
          ? Number(v)
          : v;
    try {
      await onSubmit(body);
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <Modal
      title={request ? "Complete request details" : "New equipment request"}
      onClose={onClose}
    >
      <form onSubmit={submit} className="request-form">
        <p className="muted">
          {request
            ? "Provide the missing details so coordination can continue."
            : "Use fictional details. Paste a request, then add any equipment specifications already supplied by staff."}
        </p>
        {request && (
          <div className="note">
            Needed:{" "}
            {(request.missing_fields || []).map(label).join(", ") ||
              "Review the details below."}
          </div>
        )}
        {!request && (
          <>
            <label>
              Person’s name
              <input
                name="name"
                required
                placeholder="e.g. Margaret Wilson"
                maxLength={100}
              />
            </label>
            <label>
              Incoming request
              <textarea
                name="text"
                rows={3}
                required
                placeholder="Describe the equipment request and timing…"
                maxLength={4000}
              />
            </label>
          </>
        )}
        <div className="form-grid">
          <label>
            Equipment type
            <select
              name="equipment_type"
              defaultValue={request?.equipment_type || ""}
            >
              <option value="">Not yet specified</option>
              <option value="walking_frame">Walking frame</option>
              <option value="rollator">Rollator</option>
            </select>
          </label>
          <label>
            Delivery area
            <select name="area" defaultValue={request?.area || ""}>
              <option value="">Not yet specified</option>
              {[...new Set(data.depots.map((d) => d.area))].map((a) => (
                <option key={a}>{a}</option>
              ))}
            </select>
          </label>
        </div>
        <fieldset>
          <legend>Staff-supplied specifications</legend>
          <p className="field-hint">
            Enter the required handle-height range and user weight. The
            coordinator confirms equipment suitability.
          </p>
          <div className="form-grid three">
            <label>
              Min. height (cm)
              <input
                name="min_height_cm"
                type="number"
                min={30}
                max={150}
                step="any"
                defaultValue={request?.min_height_cm}
              />
            </label>
            <label>
              Max. height (cm)
              <input
                name="max_height_cm"
                type="number"
                min={30}
                max={150}
                step="any"
                defaultValue={request?.max_height_cm}
              />
            </label>
            <label>
              User weight (kg)
              <input
                name="user_weight_kg"
                type="number"
                min={1}
                max={500}
                step="any"
                defaultValue={request?.user_weight_kg}
              />
            </label>
          </div>
        </fieldset>
        <div className="form-grid">
          <label>
            Needed by
            <input
              name="needed_by"
              type="date"
              defaultValue={request?.needed_by}
              min={data.session.now.slice(0, 10)}
            />
          </label>
          <label>
            Return by
            <input
              name="return_by"
              type="date"
              defaultValue={request?.return_by}
              min={data.session.now.slice(0, 10)}
            />
          </label>
          <label>
            Available from
            <input
              name="window_start"
              type="time"
              defaultValue={request?.window_start || ""}
            />
          </label>
          <label>
            Available until
            <input
              name="window_end"
              type="time"
              defaultValue={request?.window_end || ""}
            />
          </label>
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="modal-footer">
          <button type="button" className="button secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="button" disabled={saving}>
            {saving ? "Saving…" : request ? "Update details" : "Create request"}
            <ArrowRight size={16} />
          </button>
        </div>
      </form>
    </Modal>
  );
}
