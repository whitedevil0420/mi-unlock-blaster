#!/usr/bin/env python3
"""
mi-unlock-blaster — Xiaomi Bootloader Unlock Multi-Request Tool
Author  : whitedevil0420 (https://github.com/whitedevil0420)
Version : 1.1.0
License : MIT

Fires simultaneous requests at midnight (China Standard Time / GMT+8)
using a threading.Event barrier so all threads release within <10 ms.
"""

import time
import threading
import sys

import ntplib
import pytz
import requests
from datetime import datetime, timedelta, timezone
from requests.adapters import HTTPAdapter

from .config import STATE_URL, APPLY_URL, console
from .community import get_headers, state, apply

# ─── Config ──────────────────────────────────────────────────────────────────
BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║        🔓  MI UNLOCK BLASTER  v1.1.0                    ║
║        Simultaneous Requests — <10ms Sync                ║
║        By: whitedevil0420                                ║
║        github.com/whitedevil0420/mi-unlock-blaster      ║
╚══════════════════════════════════════════════════════════╝
"""

NTP_SERVER  = "ntp1.aliyun.com"   # Alibaba NTP (low-latency from China)

results      = []
results_lock = threading.Lock()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def retry_fn(fn, label=""):
    """Retry a callable forever until it succeeds (no delay)."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            attempt += 1
            if attempt % 5 == 0:
                print(f"  [retry] {label} attempt {attempt}: {exc}")
            time.sleep(0.5)


def ntp_beijing_time():
    """Return current Beijing time (GMT+8) synced via Alibaba NTP."""
    client   = ntplib.NTPClient()
    response = retry_fn(
        lambda: client.request(NTP_SERVER, version=3),
        label="NTP"
    )
    bj_tz = pytz.timezone("Asia/Shanghai")
    bt    = datetime.fromtimestamp(response.tx_time, timezone.utc).astimezone(bj_tz)
    return bt, time.monotonic()


def next_midnight(beijing_time: datetime) -> datetime:
    """Return next midnight in Beijing time."""
    return (beijing_time + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


# ─── Worker thread ────────────────────────────────────────────────────────────

def send_request(thread_id: int, session: requests.Session, headers: dict,
                 fire_event: threading.Event,
                 beijing_time: datetime, mono_ref: float):
    """
    Wait for fire_event, then POST the unlock application immediately.
    Records result in the shared `results` list.
    """
    try:
        fire_event.wait()           # ← All threads block here until FIRE

        sent_time = beijing_time + timedelta(seconds=time.monotonic() - mono_ref)

        response = session.post(
            APPLY_URL,
            headers=headers,
            json={"is_retry": True},
            timeout=15
        )
        result   = apply(response)
        resp_ts  = response.json().get("ts", 0)
        srv_str  = ""

        if resp_ts:
            bj_tz  = pytz.timezone("Asia/Shanghai")
            srv_dt = datetime.fromtimestamp(resp_ts, timezone.utc).astimezone(bj_tz)
            srv_str = srv_dt.strftime("%H:%M:%S.%f")

        msg = result.get("message", "No message")

        with results_lock:
            results.append({
                "id":   thread_id,
                "msg":  msg,
                "srv":  srv_str,
                "sent": sent_time.strftime("%H:%M:%S.%f"),
            })

        print(f"  [T{thread_id:02d}] {sent_time.strftime('%H:%M:%S.%f')} → {msg}")
        if srv_str:
            print(f"        Server: {srv_str} (GMT+8)")

    except Exception as exc:
        with results_lock:
            results.append({"id": thread_id, "msg": f"ERR:{exc}", "srv": "", "sent": ""})
        print(f"  [T{thread_id:02d}] ERROR: {exc}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(BANNER)

    # Login / get session headers
    print("[*] Logging in to Mi Community...")
    headers = get_headers()
    if headers is None:
        print("[ERROR] Login failed or cancelled.")
        sys.exit(1)

    # Prompt user for settings
    while True:
        try:
            num_requests = int(input("\nEnter number of parallel requests to send (1-60) [Default: 20]: ") or "20")
            if 1 <= num_requests <= 60:
                break
            print("Please enter a number between 1 and 60.")
        except ValueError:
            print("Invalid input. Please enter a valid integer.")

    while True:
        try:
            ms = int(input("\nEnter delay in ms before 00:00 (GMT+8)\n(e.g., 500 = 0.5s, 1000 = 1s, 1200 = 1.2s) [Default: 500]: ") or "500")
            break
        except ValueError:
            print("Invalid input. Please enter a valid integer.")
    delay = ms / 1000.0

    print(f"\n[Config] {num_requests} threads | {delay}s before midnight | <10ms sync\n")

    while True:
        session = requests.Session()
        # Optimize pool size to avoid threads blocking on connection acquisition
        adapter = HTTPAdapter(pool_connections=num_requests, pool_maxsize=num_requests)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        headers = retry_fn(lambda: get_headers(silent=True), label="headers")

        # Check current unlock status
        raw_status = retry_fn(
            lambda: session.get(STATE_URL, headers=headers, timeout=15),
            label="status"
        )
        status = retry_fn(lambda: state(raw_status), label="state-parse")
        print(f"\n[Status] {status.get('message')}")

        if status.get("code") == 1:
            print("\n✅  Bootloader unlock already applied — nothing more to do!")
            break

        # Sync time via NTP
        print("[*] Syncing time via Alibaba NTP...")
        beijing_time, mono_ref = ntp_beijing_time()

        # Calculate fire target
        midnight = next_midnight(beijing_time)
        target   = midnight - timedelta(seconds=delay)

        print(f"[Target]:  {target.strftime('%H:%M:%S.%f')} (GMT+8)")
        print(f"[Current]: {beijing_time.strftime('%H:%M:%S.%f')} (GMT+8)")
        print(f"[Threads]: {num_requests} ready to fire simultaneously\n")

        # Spawn all threads — they block at fire_event
        fire_event = threading.Event()
        results.clear()
        threads    = []

        for i in range(1, num_requests + 1):
            t = threading.Thread(
                target=send_request,
                args=(i, session, headers, fire_event, beijing_time, mono_ref),
                daemon=True,
            )
            t.start()
            threads.append(t)

        print(f"[Ready] All {num_requests} threads spawned and waiting at barrier...\n")

        # Warm-up: pre-open connection pool ~10 s before fire
        warmed = False
        while True:
            now  = beijing_time + timedelta(seconds=time.monotonic() - mono_ref)
            diff = (target - now).total_seconds()

            if diff <= 0:
                break

            # Warm-up: establish TCP/TLS connection for each thread in the pool
            if not warmed and diff <= 10:
                print(f"[Warm-up] {diff:.3f}s to go — Pre-warming all {num_requests} connections in the pool...")
                for _ in range(num_requests):
                    threading.Thread(
                        target=lambda: session.get(STATE_URL, headers=headers, timeout=15),
                        daemon=True,
                    ).start()
                warmed = True
                print("[Warm-up] Connections pre-warming initiated!")

            if diff > 5:
                time.sleep(min(diff - 5, 30))
            elif diff > 0.05:
                time.sleep(0.005)
            else:
                time.sleep(0.0001)   # busy-wait final 50 ms for precision

        # 🚀 FIRE — release all threads at the same microsecond
        fire_time = beijing_time + timedelta(seconds=time.monotonic() - mono_ref)
        print(f"\n🚀  FIRE! {fire_time.strftime('%H:%M:%S.%f')} (GMT+8)")
        fire_event.set()

        # Wait for all threads to finish
        for t in threads:
            t.join(timeout=30)

        # Summary
        print("\n" + "═" * 58)
        print(f"📊  SUMMARY — {num_requests} Requests:")
        print("═" * 58)

        sent_times = [r["sent"] for r in results if r["sent"]]
        if len(sent_times) >= 2:
            fmt   = "%H:%M:%S.%f"
            t_objs = [datetime.strptime(t, fmt) for t in sent_times]
            spread = (max(t_objs) - min(t_objs)).total_seconds() * 1000
            print(f"⏱   Spread: {spread:.2f} ms across all {len(sent_times)} threads")

        for r in results:
            print(f"  T{r['id']:02d}: {r['msg']}")

        print("═" * 58 + "\n")
        print("⏳  Waiting for next midnight cycle...\n")


if __name__ == "__main__":
    main()
