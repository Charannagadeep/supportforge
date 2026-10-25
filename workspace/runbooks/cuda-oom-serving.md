# Runbook: CUDA OOM / model-serving crash

## Signals

- Log lines: `CUDA out of memory`, `torch.cuda.OutOfMemoryError`, `nvidia-smi` near 100% memory
- Process exit after large model load or batch spike

## Typical evidence needed

- `nvidia-smi` at/near failure
- Serving config (max model len, gpu memory utilization, tensor parallel)
- Exact model id and quantization

## Next checks (local)

1. Confirm GPU memory vs model footprint.
2. Check for competing processes on the GPU.
3. Verify batch size / concurrent sequences.
4. Confirm driver/CUDA match the framework wheel.

## Do not

- Blame “bad GPU” without Xid / ECC / nvidia-smi evidence.
