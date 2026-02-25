# Q-F5 Sentinel

Python framework to audit F5 BIG-IP devices for configuration drift using a declarative desired state.

## Why this project

`Q-F5 Sentinel` demonstrates reconciliation-first network automation:

- Define policy once in YAML (Source of Truth)
- Fetch actual device state (mocked iControl REST JSON response)
- Compare desired vs actual and detect exact drift fields
- Emit telemetry payload for Splunk
- Simulate ServiceNow change-request creation for approval-first remediation

This approach is safer than blind push automation in high-uptime environments because it verifies reality before any remediation action.

## Project structure

- `gold_standard.yaml` - declarative desired state for an F5 virtual server
- `f5_actual_state.json` - simulated live F5 state (contains intentional drift)
- `reconciler.py` - reconciliation engine + Splunk/ServiceNow integration mocks
- `requirements.txt` - Python dependencies

## Desired vs actual example

Desired state (`gold_standard.yaml`) includes:

- Virtual server name
- IP address
- Port `443`
- `TLS1.2`
- Specific SSL profile
- Specific WAF profile

Mock actual state (`f5_actual_state.json`) intentionally changes `ssl_profile` to simulate configuration drift.

## How it works

1. Load desired state from YAML.
2. Load actual state from JSON (mocking F5 API output).
3. Run recursive reconciliation (`compare_states`) to identify:
   - missing keys
   - unexpected keys
   - value mismatches
4. Print a clean drift report (`rich` table when available).
5. Build and log a Splunk telemetry payload.
6. Simulate ServiceNow change request creation when drift is detected.

## Quick start

```bash
cd /Users/angelatierney/Documents/Q-F5-Sentinel
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reconciler.py
```

## Example output

- Drift report table shows the exact path:
  - `virtual_server_root.virtual_server.ssl_profile`
- Splunk payload includes:
  - `drift_detected`
  - `drift_count`
  - `drifts[]`
  - UTC timestamp
- ServiceNow mock POST payload is generated only when drift exists.

## Interview talk track

Keep these sections visible:

1. **Reconciliation Logic** in `reconciler.py` (`compare_states`)
   - "This reconciliation loop ensures the device actually matches security policy."
2. **Source of Truth** in `gold_standard.yaml`
   - "This declarative model scales from 1 to 100+ devices consistently."
3. **ServiceNow trigger** in `reconciler.py` (`open_servicenow_change`)
   - "The script requests human approval before remediation for production safety."

## Extending to production

- Replace `fetch_f5_actual_state()` file read with iControl REST calls via `requests`
- Add auth/token management and secrets handling
- Add CI tests for drift scenarios (match, mismatch, missing keys, extra keys)
- Route telemetry to Splunk HEC endpoint
- Replace ServiceNow mock with real `POST /api/now/table/change_request`

## Skills demonstrated

- Network automation and policy reconciliation
- Python data modeling and recursive comparison
- YAML/JSON interoperability
- Observability/telemetry patterns
- Change-control integration and operational safety