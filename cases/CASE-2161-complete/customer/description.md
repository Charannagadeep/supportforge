# Problem (NVIDIA/nvidia-container-toolkit#2161)

**Title:** libnvsdm missing from management CDI specs

**Source:** https://github.com/NVIDIA/nvidia-container-toolkit/issues/2161

## Summary

On HGX B200/B300 nodes with 5th-generation NVLink, which use NVSDM instead of NSCQ for NVSwitch telemetry, the management CDI spec doesn't mount `libnvsdm.so.1` or the libraries it depends on into management containers. NVSDM initialization then fails inside DCGM, and NVSwitch metrics are not collected.

## Background

- Earlier generations used `libnvidia-nscq.so.<major>.<minor>.<patch>`. Its filename carries the driver version, so the driver-library discoverer, which matches on the driver version suffix, picked it up.
- B200/B300 uses NVSDM. Its library is `libnvsdm.so.1`, with no driver version in the name, so the version-suffix match never finds it.
- `libnvsdm.so.1` depends on `libibumad.so.3`and `libibmad.so.5`.

## Steps to reproduce

1. HGX B200 node, 5th-gen NVLink, NVIDIA driver installed.
2. Generate the management CDI spec (`management.nvidia.com/gpu`) with the toolkit -- `sudo nvidia-ctk cdi generate --mode management --output /var/run/cdi/management.nvidia.com-gpu.yaml`
3. Launch DCGM container with access to `management.nvidia.com/gpu=all`.

## Expected behavior

DCGM is able to initialize NVSDM and collect NVSwitch metrics.

## Actual behavior

NVSDM initialization fails inside DCGM and NVSwitch metrics are not collected. We see the following logs in the DCGM container:

```
level=INFO msg="Not collecting NvSwitch metrics; no switches to monitor"
```

When enabling debug logs with `nv-hostengine` we see:
```
ERROR [316:316] [[NvSwitch]] NVSDM error: 8 [./modules/nvswitch/DcgmNvsdmManager.cpp:982]
```
