export type Equipment = {
  id: string;
  name: string;
  type: string;
  depot_id: string;
  min_height_cm: number;
  max_height_cm: number;
  max_weight_kg: number;
  status: string;
  inspection_passed: boolean;
  inspected_at?: string;
  loan_until?: string;
};
export type Request = {
  id: string;
  name: string;
  text: string;
  equipment_type?: string;
  min_height_cm?: number;
  max_height_cm?: number;
  user_weight_kg?: number;
  needed_by?: string;
  return_by?: string;
  area?: string;
  window_start?: string;
  window_end?: string;
  status: string;
  missing_fields: string[];
  candidates: { equipment_id: string; eligible: boolean; reasons: string[] }[];
  proposal_version: number;
  equipment_id?: string;
  driver_id?: string;
  delivery_date?: string;
  cancelled_driver_ids: string[];
  created_at: string;
};
export type Snapshot = {
  session: { id: string; now: string; mode: string };
  depots: { id: string; name: string; area: string; address: string }[];
  equipment: Equipment[];
  drivers: {
    id: string;
    name: string;
    capacity: number;
    areas: string[];
    window_start: string;
    window_end: string;
  }[];
  requests: Request[];
  messages: {
    id: string;
    request_id: string;
    recipient: string;
    subject: string;
    body: string;
    created_at: string;
    simulated: boolean;
  }[];
  events: {
    id: string;
    request_id?: string;
    type: string;
    summary: string;
    created_at: string;
  }[];
  runs: {
    id: string;
    request_id?: string;
    status: string;
    error?: string;
    created_at: string;
  }[];
};
export type Mutation = {
  run_id?: string;
  request_id?: string;
  event_id?: string;
};
