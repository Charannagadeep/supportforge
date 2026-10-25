# Problem (NVIDIA/nvidia-container-toolkit#2163)

**Title:** Containers with NVIDIA_VISIBLE_DEVICES=all fail to start in jit-cdi mode when every GPU is bound to vfio-pci

**Source:** https://github.com/NVIDIA/nvidia-container-toolkit/issues/2163

**Describe the bug**

When every GPU on a node is bound to `vfio-pci` (driver loaded, no GPU bound to it), the `nvidia` runtime in jit-cdi mode fails to create containers with `NVIDIA_VISIBLE_DEVICES=all`:

    failed to create the automatic CDI modifier: failed to generate CDI spec for mode "auto": failed to construct device spec generators: failed to initialize NVML: No supported GPUs were found

This happens with the NVIDIA DRA driver's `PassthroughSupport`: while every GPU is in a KubeVirt VM, GPU Operator operands (gpu-feature-discovery, dcgm-exporter) cannot be recreated on that node.

`nvmllib.DeviceSpecGenerators` (`pkg/nvcdi/lib-nvml.go`) calls `nvmlInit` before handling `all`, and the init fails when no GPU is bound.

**Expected behavior**

`all` with no GPUs available resolves to no devices, as `none` does, and the container starts. I can send a PR.

**Environment**
- nvidia-container-toolkit v1.19.1 (same code on `main`), driver 595.91.07
- Talos v1.14.2, kernel 6.18.54, containerd 2.3.6, Kubernetes v1.37.1
- RTX PRO 6000 Blackwell × 2, GPU Operator v26.7.1, DRA driver v0.5.1, KubeVirt v1.9.0
