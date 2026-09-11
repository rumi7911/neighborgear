"""Deterministic safety gates: an agent can propose, but never bypass these."""
from datetime import date, timedelta
from uuid import uuid4


def uid(prefix):
    return f"{prefix}_{uuid4().hex[:12]}"


def event(state, request_id, kind, summary):
    state["events"].append(dict(id=uid("evt"), request_id=request_id, type=kind, summary=summary, created_at=state["session"]["now"]))


def message(state, request, kind, body, recipient=None):
    # Stable domain key makes replay and repeated clock ticks harmless.
    key = f"{request['id']}:{kind}"
    if any(m.get("dedupe_key") == key for m in state["messages"]):
        return
    state["messages"].append(dict(id=uid("msg"), request_id=request["id"], recipient=recipient or request["name"], subject=kind.replace("_", " ").title(), body=body, simulated=True, dedupe_key=key, created_at=state["session"]["now"]))


SPEC_FIELDS = ("equipment_type", "min_height_cm", "max_height_cm", "user_weight_kg", "needed_by", "return_by", "area", "window_start", "window_end")


def new_request(state, request_id, data):
    req = dict(id=request_id, name=data.get("name", "Example neighbour"), text=data.get("text", ""), status="new", missing_fields=[], candidates=[], proposal_version=0, equipment_id=None, driver_id=None, delivery_date=None, cancelled_driver_ids=[], created_at=state["session"]["now"])
    req.update({k: data.get(k) for k in SPEC_FIELDS})
    state["requests"].append(req)
    return req


def match(state, req):
    req["missing_fields"] = [k for k in SPEC_FIELDS if req.get(k) is None or req.get(k) == ""]
    req["proposal_version"] += 1
    req["candidates"] = []
    if req["missing_fields"]:
        req["status"] = "needs_information"
        message(state, req, f"clarification_{req['proposal_version']}", "Please provide: " + ", ".join(req["missing_fields"]))
        return
    if req["min_height_cm"] > req["max_height_cm"]:
        raise ValueError("Minimum handle height must not exceed maximum")
    if req["return_by"] < req["needed_by"]:
        raise ValueError("Return date must be on or after delivery date")
    if req["window_start"] >= req["window_end"]:
        raise ValueError("Delivery window must end after it starts")
    for item in state["equipment"]:
        reasons = []
        if item["type"] != req["equipment_type"]:
            reasons.append("Different equipment type")
        if item["status"] != "available":
            reasons.append(f"Equipment is {item['status']}")
        if not item["inspection_passed"]:
            reasons.append("Safety inspection required")
        if not (item["min_height_cm"] <= req["min_height_cm"] and item["max_height_cm"] >= req["max_height_cm"]):
            reasons.append("Handle height range incompatible")
        if item["max_weight_kg"] < req["user_weight_kg"]:
            reasons.append("Weight capacity exceeded")
        if req["needed_by"] < state["session"]["now"]:
            reasons.append("Delivery deadline has passed")
        req["candidates"].append(dict(equipment_id=item["id"], eligible=not reasons, reasons=reasons))
    req["status"] = "awaiting_approval" if any(c["eligible"] for c in req["candidates"]) else "needs_attention"
    event(state, req["id"], "matched", f"Safety checks found {sum(c['eligible'] for c in req['candidates'])} eligible items; coordinator approval required.")


def schedule(state, req):
    req["driver_id"] = None
    req["delivery_date"] = None
    for driver in sorted(state["drivers"], key=lambda d: d["areas"][0].casefold() != req["area"].casefold()):
        if driver["id"] in req["cancelled_driver_ids"] or req["area"].casefold() not in [a.casefold() for a in driver["areas"]]:
            continue
        if max(req["window_start"], driver["window_start"]) >= min(req["window_end"], driver["window_end"]):
            continue
        used = sum(a["driver_id"] == driver["id"] and a["date"] == req["needed_by"] and a["status"] in ("scheduled", "delivered") for a in state["assignments"])
        if used >= driver["capacity"] or req["needed_by"] < state["session"]["now"]:
            continue
        req.update(driver_id=driver["id"], delivery_date=req["needed_by"], status="delivery_scheduled")
        assignment = dict(id=uid("assignment"), request_id=req["id"], driver_id=driver["id"], date=req["needed_by"], window_start=max(req["window_start"], driver["window_start"]), window_end=min(req["window_end"], driver["window_end"]), status="scheduled")
        state["assignments"].append(assignment)
        message(state, req, f"delivery_{assignment['id']}", f"Sandbox delivery scheduled for {req['needed_by']} with {driver['name']} between {assignment['window_start']} and {assignment['window_end']}.")
        event(state, req["id"], "delivery_scheduled", f"Assigned {driver['name']} within area, time and capacity limits.")
        return
    req["status"] = "needs_attention"
    event(state, req["id"], "transport_unavailable", "Item reserved, but no eligible driver has capacity before the deadline. Coordinator action required.")


def apply(state, payload, extracted=None, defer_transport=False):
    op = payload["operation"]
    data = payload.get("data", {})
    if op == "clock":
        state["session"]["now"] = (date.fromisoformat(state["session"]["now"]) + timedelta(days=data["days"])).isoformat()
        for req in state["requests"]:
            if req["status"] == "on_loan" and req["return_by"] <= state["session"]["now"]:
                message(state, req, "return_reminder", f"Your example {req['equipment_type']} was due back on {req['return_by']}. Please arrange its return for inspection.")
            if req["status"] == "delivery_scheduled" and req["delivery_date"] < state["session"]["now"]:
                req["status"] = "needs_attention"
                event(state, req["id"], "delivery_overdue", "Delivery deadline passed without confirmation; item remains reserved.")
        event(state, None, "clock_advanced", f"Sandbox clock advanced to {state['session']['now']}.")
        return
    req = next((r for r in state["requests"] if r["id"] == payload.get("request_id")), None)
    if op == "create":
        if req:
            return
        merged = dict(extracted or {})
        merged.update({k: v for k, v in data.items() if v is not None})
        req = new_request(state, payload["request_id"], merged)
        match(state, req)
        return
    if not req:
        raise ValueError("Request not found")
    if op == "clarify":
        if req["equipment_id"]:
            raise ValueError("Cannot change specifications after reservation")
        req.update({k: v for k, v in data.items() if k in SPEC_FIELDS and v is not None})
        match(state, req)
    elif op == "approve":
        if req["equipment_id"]:
            if req["equipment_id"] == data["equipment_id"]:
                return
            raise ValueError("Request already has a reserved item")
        if data["proposal_version"] != req["proposal_version"] or req["status"] != "awaiting_approval":
            raise ValueError("Proposal is stale or not awaiting approval; clarify to refresh")
        # Recompute inside reservation transaction; a stale snapshot is never authority.
        version = req["proposal_version"]
        match(state, req)
        req["proposal_version"] = version
        if not any(c["equipment_id"] == data["equipment_id"] and c["eligible"] for c in req["candidates"]):
            raise ValueError("Equipment is no longer available or does not meet safety requirements")
        item = next(i for i in state["equipment"] if i["id"] == data["equipment_id"])
        item["status"] = "reserved"
        req.update(equipment_id=item["id"], status="reserved")
        state["approvals"].append(dict(id=uid("approval"), request_id=req["id"], equipment_id=item["id"], proposal_version=version, approved_at=state["session"]["now"]))
        state["reservations"].append(dict(id=uid("reservation"), request_id=req["id"], equipment_id=item["id"], status="active"))
        if not defer_transport:
            schedule(state, req)
    elif op == "event":
        kind = data["type"]
        item = next((i for i in state["equipment"] if i["id"] == req["equipment_id"]), None)
        if kind == "cancel_driver":
            if not data.get("driver_id"):
                raise ValueError("Cancellation must identify the driver being cancelled")
            if req["status"] not in ("delivery_scheduled", "needs_attention") or not req["driver_id"]:
                raise ValueError("No scheduled driver to cancel")
            # Optional driver ID prevents a delayed duplicate cancelling its replacement.
            if data.get("driver_id") and data["driver_id"] != req["driver_id"]:
                return
            req["cancelled_driver_ids"].append(req["driver_id"])
            for a in state["assignments"]:
                if a["request_id"] == req["id"] and a["status"] == "scheduled":
                    a["status"] = "cancelled"
            event(state, req["id"], kind, "Driver cancelled; checking remaining volunteers.")
            req.update(driver_id=None, delivery_date=None, status="reserved")
            if not defer_transport:
                schedule(state, req)
        elif kind == "confirm_delivery":
            if req["status"] == "on_loan":
                return
            if req["status"] != "delivery_scheduled":
                raise ValueError("Delivery must be scheduled before confirmation")
            req["status"] = item["status"] = "on_loan"
            item["loan_until"] = req["return_by"]
            for a in state["assignments"]:
                if a["request_id"] == req["id"] and a["status"] == "scheduled":
                    a["status"] = "delivered"
            for r in state["reservations"]:
                if r["request_id"] == req["id"]:
                    r["status"] = "fulfilled"
            state["loans"].append(dict(id=uid("loan"), request_id=req["id"], equipment_id=item["id"], due_at=req["return_by"], status="active"))
            message(state, req, "delivery_confirmed", "Example delivery confirmed. Please return the aid by " + req["return_by"] + ".")
            event(state, req["id"], kind, "Delivery confirmed and loan recorded.")
        elif kind == "return_equipment":
            if req["status"] in ("inspection", "completed"):
                return
            if req["status"] != "on_loan":
                raise ValueError("Only equipment on loan can be returned")
            req["status"] = item["status"] = "inspection"
            item["inspection_passed"] = False
            item["loan_until"] = None
            for loan in state["loans"]:
                if loan["request_id"] == req["id"]:
                    loan["status"] = "returned"
            event(state, req["id"], kind, "Returned item quarantined pending physical safety inspection.")
        elif kind in ("pass_inspection", "fail_inspection"):
            if req["status"] == "completed":
                return
            if req["status"] != "inspection":
                raise ValueError("Item must be returned and awaiting inspection")
            passed = kind == "pass_inspection"
            item.update(status="available" if passed else "retired", inspection_passed=passed, inspected_at=state["session"]["now"])
            req["status"] = "completed"
            event(state, req["id"], kind, "Inspection passed; returned to available inventory." if passed else "Inspection failed; removed from circulation.")
        else:
            raise ValueError("Unsupported lifecycle event")
    else:
        raise ValueError("Unsupported operation")


def seed(sid, mode="simulator"):
    state = {"session": {"id": sid, "now": "2026-09-05", "mode": mode}, **{k: [] for k in ("depots", "equipment", "drivers", "requests", "messages", "events", "runs", "approvals", "reservations", "assignments", "loans")}}
    for index, area in enumerate(("North", "Central", "South")):
        depot_id = f"depot_{index+1}"
        state["depots"].append(dict(id=depot_id, name=f"{area} Community Depot", area=area, address=f"{index+1} Example Lane, Fictional Borough, UK"))
        for n in range(8):
            state["equipment"].append(dict(id=f"gear_{index*8+n+1:02}", name=f"{area} {'Rollator' if n%2 else 'Walking frame'} {n+1}", type="rollator" if n%2 else "walking_frame", depot_id=depot_id, min_height_cm=75 if n < 6 else 85, max_height_cm=100 if n < 6 else 110, max_weight_kg=150 if n < 4 else 100, status="inspection" if n == 7 else "available", inspection_passed=n != 7, inspected_at="2026-09-01", loan_until=None))
    for n, name in enumerate(("Alex Morgan", "Sam Patel", "Jo Taylor", "Charlie Ellis", "Robin Lee", "Drew Wilson")):
        state["drivers"].append(dict(id=f"driver_{n+1}", name=name + " (example)", capacity=2, areas=[("North", "Central", "South")[n//2], "Central"], window_start="09:00" if n%2 == 0 else "12:00", window_end="17:00"))
    examples = [("Maya", "rollator", "North"), ("Arthur", "walking_frame", "Central"), ("Nora", "rollator", "South"), ("Elliot", "walking_frame", "North"), ("Grace", "rollator", "Central"), ("Theo", "walking_frame", "South")]
    for n, (name, kind, area) in enumerate(examples):
        data = dict(name=name + " (example)", text=f"Example request for a {kind.replace('_', ' ')} in {area}.", equipment_type=kind, min_height_cm=80, max_height_cm=95, user_weight_kg=85, needed_by="2026-09-06", return_by="2026-09-12", area=area, window_start="10:00", window_end="16:00")
        if n == 1:
            data["user_weight_kg"] = None
        if n == 5:
            data["user_weight_kg"] = 180
        req = new_request(state, f"request_{n+1}", data)
        match(state, req)
        if n in (2, 3, 4):
            item_id = next(c["equipment_id"] for c in req["candidates"] if c["eligible"])
            apply(state, dict(operation="approve", request_id=req["id"], data=dict(equipment_id=item_id, proposal_version=req["proposal_version"])))
            if n in (3, 4):
                apply(state, dict(operation="event", request_id=req["id"], data=dict(type="confirm_delivery")))
            if n == 4:
                apply(state, dict(operation="event", request_id=req["id"], data=dict(type="return_equipment")))
    # Refresh proposals after seed reservations so the opening UI is current.
    for req in state["requests"]:
        if not req["equipment_id"]:
            match(state, req)
    event(state, None, "sandbox_created", "Fictional sandbox seeded. All messages are simulated; no communications are sent.")
    return state
