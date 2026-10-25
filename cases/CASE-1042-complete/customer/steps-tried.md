# Steps already tried

1. Restarted the serving container twice.
2. Rebooted the host once.
3. Reduced concurrent requests from 8 → 2 (still crashes on startup).
4. Confirmed disk space is available (>400 GB free).

Not tried yet: collecting full nvidia-smi during failure, capturing environment manifest, trying a smaller model.
