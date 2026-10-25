# CASE-1042 — Customer report

**Account:** Contoso Robotics  
**Product:** Dell Pro Max / GB10 lab node running local model serving  
**Opened:** 2026-10-25 08:14 PT  
**Severity:** Sev-2 (blocked demo rehearsal)

## Symptom

Our model-serving app keeps crashing when we load the production model. Error looks like a GPU memory problem but we are not sure. Happens within ~30–90 seconds of starting the server. Restarting does not help.

## Impact

Cannot run internal demo for leadership. No production customer traffic on this box.
