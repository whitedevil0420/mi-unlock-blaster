# Changelog

All notable changes to **mi-unlock-blaster** are documented here.

## [1.0.0] — 2026-06-09

### Added
- Initial release by **whitedevil0420**
- 20 simultaneous threads using `threading.Event` barrier
- All threads fire within **<10 ms** of each other
- NTP time sync via Alibaba's `ntp1.aliyun.com` (low-latency from China)
- Auto-targets next midnight in **China Standard Time (GMT+8)**
- Connection pre-warm ~10 seconds before fire time
- Busy-wait final 50 ms for maximum precision
- Clean summary report: spread in ms + per-thread results
- Retry logic for network failures
- CLI entry point: `mi-unlock-blaster`
- `pyproject.toml` packaging
- MIT License
