# Runbook: NVIDIA Xid / driver faults

## Signals

- `NVRM: Xid` in dmesg
- Sudden GPU reset, ECC errors, fabric manager complaints

## Required extras

- Full `dmesg` excerpt around the event
- Driver version + CUDA version
- Whether the box was thermally throttling

## Next checks

1. Confirm Xid code meaning against NVIDIA debug guidelines.
2. Reproduce with a minimal CUDA sample if safe.
3. Do not jump to hardware RMA until software/driver evidence is packaged.
