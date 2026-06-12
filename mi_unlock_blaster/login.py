import os
import json
import time
import base64
import platform
import threading
import webbrowser
import http.server
import socketserver
import hashlib
import sys
from urllib.parse import unquote, urlparse, parse_qs
from dataclasses import dataclass
from typing import Optional
import qrcode

from .config import (
    BASE_URL, console, SERVICELOGINAUTH2_URL, LIST_URL, USERQUOTA_URL,
    SEND_EM_TICKET, SEND_PH_TICKET, VERIFY_EM, VERIFY_PH, LONGPOLLING_URL
)
from .requester import get, post
from .utils import get_uRegion, get_areaConfig

# Embed the captcha.html content directly as a string
CAPTCHA_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>Captcha</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f0f2f5;
      padding: 16px;
    }

    .card {
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,.10);
      padding: clamp(20px, 5vw, 40px);
      width: 100%;
      max-width: 420px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: clamp(14px, 3vw, 22px);
    }

    h2 {
      font-size: clamp(16px, 4vw, 20px);
      color: #333;
      font-weight: 600;
    }

    img {
      width: 100%;
      border-radius: 10px;
      border: 1px solid #e0e0e0;
      display: block;
    }

    .error {
      color: #d32f2f;
      font-size: clamp(13px, 3vw, 15px);
      background: #fdecea;
      padding: 10px 16px;
      border-radius: 8px;
      width: 100%;
      text-align: center;
    }

    input {
      width: 100%;
      padding: clamp(12px, 3vw, 16px);
      font-size: clamp(22px, 6vw, 30px);
      border: 2px solid #e0e0e0;
      border-radius: 10px;
      text-align: center;
      letter-spacing: clamp(4px, 2vw, 8px);
      transition: border-color .2s;
      -webkit-appearance: none;
    }

    input:focus {
      border-color: #1a73e8;
      outline: none;
    }

    button {
      width: 100%;
      padding: clamp(12px, 3vw, 16px);
      font-size: clamp(15px, 4vw, 18px);
      background: #1a73e8;
      color: #fff;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
      transition: background .2s, transform .1s;
      -webkit-tap-highlight-color: transparent;
    }

    button:hover   { background: #1558b0; }
    button:active  { transform: scale(.97); }

    .done {
      font-size: clamp(18px, 5vw, 24px);
      color: #2e7d32;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="card">
    <h2>Captcha Verification</h2>
    <img src="data:image/jpeg;base64,{{B64}}" alt="captcha">
    {{MSG}}
    <input id="code" type="text" placeholder="Enter code" autocomplete="off" autofocus>
    <button onclick="submit()">Verify</button>
  </div>
  <script>
    function submit() {
      var code = document.getElementById('code').value.trim();
      if (!code) return;
      fetch('/submit?code=' + encodeURIComponent(code))
        .then(function(r) { return r.text(); })
        .then(function(t) {
          if (t === 'ok') {
            document.querySelector('.card').innerHTML =
              '<p class="done">✓ Code submitted.<br>Return to terminal.</p>';
          } else {
            window.location.reload();
          }
        });
    }
    document.getElementById('code').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') submit();
    });
  </script>
</body>
</html>
"""

@dataclass
class _CaptchaState:
    b64:   str
    error: bool = False
    code:  Optional[str] = None
    done:  bool = False


def _build_html(b64: str, error: bool = False) -> str:
    msg = "<p class='error'>Incorrect code! Try again.</p>" if error else ""
    return CAPTCHA_HTML_TEMPLATE.replace("{{B64}}", b64).replace("{{MSG}}", msg)


def handle_captcha(send_url, response, payload, capt_key):
    try:
        response_text = json.loads(response.text[11:])
        cap_url = BASE_URL + response_text["captchaUrl"]
        state = _CaptchaState(b64=base64.b64encode(get(cap_url).content).decode())

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass

            def do_GET(self):
                if self.path == "/":
                    body = _build_html(state.b64, state.error).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                elif self.path.startswith("/submit"):
                    code = parse_qs(urlparse(self.path).query).get("code", [""])[0]
                    state.code = unquote(code).strip()
                    start = time.time()
                    while state.code is not None and time.time() - start < 10:
                        time.sleep(0.1)
                    result = b"ok" if state.done else b"retry"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(result)

        httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        url = f"http://127.0.0.1:{port}"
        if platform.system() in ("Linux", "Android"):
            os.system(f"xdg-open '{url}' 2>/dev/null")
        else:
            webbrowser.open(url)
        console.print(f"[white]Captcha opened at: [/][orange]{url}[/]")

        while True:
            while state.code is None:
                time.sleep(0.2)

            payload[capt_key] = state.code

            try:
                resp = post(send_url, data=payload)
                resp_text = json.loads(resp.text[11:])
            except Exception as e:
                return {"error": str(e)}

            if resp_text.get("code") == 87001:
                try:
                    state.b64 = base64.b64encode(get(cap_url).content).decode()
                except Exception as e:
                    return {"error": str(e)}
                state.error = True
                state.code  = None
            else:
                state.done = True
                state.code = None
                break

        httpd.shutdown()
        return resp

    except Exception as e:
        return {"error": str(e)}


def send_verification_code(addressType, label):
    if addressType == "EM":
        send_url = SEND_EM_TICKET
    else:
        send_url = SEND_PH_TICKET

    try:
        response = post(send_url)
        response_text = json.loads(response.text[11:])
    except Exception as e:
        return {"error": str(e)}

    if response_text.get("code") == 87001:
        console.print("\nCAPTCHA verification required for sending code!\n", style="orange")
        response = handle_captcha(send_url, response, {"icode": "", "_json": "true"}, "icode")

        if isinstance(response, dict) and "error" in response:
            return response

        response_text = json.loads(response.text[11:])

    if response_text.get("code") == 0:
        console.print(f"\nCode sent to {label} successfully.\n", style="green")
        return {"success": True}

    code = response_text.get("code")
    error_msg = response_text.get("tips", response_text) if code == 70022 else response_text
    return {"error": error_msg}


def verify_code_ticket(addressType, label):
    url = VERIFY_EM if addressType == "EM" else VERIFY_PH

    while True:
        console.print(f"[white]Check your {label} for the code.[/]")
        ticket = console.input("[orange]Enter code (or type 'r' to resend): [/]").strip()

        if not ticket:
            continue

        if ticket == "r":
            return "RESEND"

        try:
            response      = post(url, data={"ticket": ticket, "trust": "true", "_json": "true"})
            response_text = json.loads(response.text[11:])
        except Exception as e:
            return {"error": str(e)}

        if response_text.get("code") == 0:
            return response_text.get("location")

        if response_text.get("code") == 70014:
            console.print("Invalid code provided.", style="red")
            continue

        return {"error": response_text}


def handle_verify(context, auth_data):
    console.print("\n=== 2FA Verification Required ===\n", style="orange")

    try:
        response = get(LIST_URL, params={"sid": auth_data["sid"], "supportedMask": "0", "context": context})
        result_json = json.loads(response.text[11:])
    except Exception as e:
        return {"error": str(e)}

    options = result_json.get("options", [])

    if 8 in options and 4 in options:
        while True:
            console.print("Choose verification method:", style="white")
            console.print("[orange]1[/][white] = Phone (SMS)[/]")
            console.print("[orange]2[/][white] = Email[/]")
            choice = console.input("[white]Enter 1 or 2: [/]").strip()

            if choice in ["1", "2"]:
                break
            console.print("Invalid choice, try again.\n", style="red")

        addressType = "PH" if choice == "1" else "EM"
    elif 4 in options:
        addressType = "PH"
    elif 8 in options:
        addressType = "EM"
    else:
        return {"error": f"No supported verification options found. (Response: {result_json})"}

    label = "Email" if addressType == "EM" else "Phone"

    while True:
        try:
            response_quota = post(USERQUOTA_URL, data={"addressType": addressType, "contentType": "160040", "_json": "true"})
            quota_json     = json.loads(response_quota.text[11:])
        except Exception as e:
            return {"error": str(e)}

        info = quota_json.get("info")
        remaining = int(info) if info is not None else 0
        console.print(f"\n[white]Attempts remaining: [/][{'green' if remaining > 0 else 'red'}]{remaining}[/]")

        if remaining == 0:
            return {"error": f"Sent too many codes to {label}. Try again tomorrow."}

        send_result = send_verification_code(addressType, label)

        if isinstance(send_result, dict) and "error" in send_result:
            err_data = send_result["error"]
            if isinstance(err_data, dict) and err_data.get("code") == 20024:
                wt_seconds = err_data.get("data", {}).get("wt", 60)
                for i in range(int(wt_seconds), 0, -1):
                    print(f"\rPlease wait: {i} before you can try resend again", end="", flush=True)
                    time.sleep(1)
                console.input("\n[white]Press Enter to try resending now... [/]")
                continue

            return send_result

        verify_result = verify_code_ticket(addressType, label)

        if verify_result == "RESEND":
            console.print("\n[orange]Retrying to send the code...[/]\n")
            continue

        if isinstance(verify_result, dict) and "error" in verify_result:
            return verify_result

        break

    try:
        response = get(verify_result, allow_redirects=False)
        location = response.headers.get("Location")
        if not location:
            return {"error": "Missing redirect location"}
        get(location, allow_redirects=False)
        return post(SERVICELOGINAUTH2_URL, data=auth_data)
    except Exception as e:
        return {"error": str(e)}


def password_input():
    pwd = []
    if sys.platform == "win32":
        import msvcrt
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                break
            elif ch == "\b":
                if pwd:
                    pwd.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            else:
                pwd.append(ch)
                sys.stdout.write("*")
                sys.stdout.flush()
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"):
                    break
                elif ch == "\x7f":
                    if pwd:
                        pwd.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                else:
                    pwd.append(ch)
                    sys.stdout.write("*")
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    sys.stdout.write("\n")
    return "".join(pwd)


def get_credentials(dial=""):
    console.print(f"\n[white]Xiaomi Account ID, Email, or Phone {dial}[/]")
    user = console.input("[white]> [/]").strip()
    console.print("[white]Password> [/]", end="")
    pwd_input = password_input().strip()
    pwd = hashlib.md5(pwd_input.encode()).hexdigest().upper()
    return user, pwd


def handle_terminal(auth_data: dict) -> dict:
    uRegion = get_uRegion()
    if uRegion:
        areaConfig = get_areaConfig(uRegion)
        if areaConfig:
            dial = f"(ex> {areaConfig['dial']}XXXXXXXXX)"
        else:
            dial = ""
    else:
        dial = ""

    while True:
        user, pwd = get_credentials(dial)
        auth_data["user"] = user
        auth_data["hash"] = pwd

        try:
            response = post(SERVICELOGINAUTH2_URL, data=auth_data)
            response_text = json.loads(response.text[11:])
        except Exception as e:
            console.print(f"\n[red]{e}[/]\n")
            return None

        if response_text.get("code") == 70016:
            console.print("\nInvalid password or username! Please try again.\n", style="red")
            continue

        if response_text.get("code") == 87001:
            console.print("\nCAPTCHA verification required!\n", style="orange")
            response = handle_captcha(SERVICELOGINAUTH2_URL, response, auth_data, "captCode")

            if isinstance(response, dict) and "error" in response:
                console.print(f"\n[red]{response['error']}[/]\n")
                return None

            response_text = json.loads(response.text[11:])

            if response_text.get("code") == 70016:
                console.print("\nInvalid password or username! Please try again.\n", style="red")
                continue

        break

    if "notificationUrl" in response_text:
        notification_url = response_text["notificationUrl"]
        if any(x in notification_url for x in ["callback", "SetEmail", "BindAppealOrSafePhone"]):
            console.print(f"\n[red]Action required at: {notification_url}[/]\n")
            return None

        context  = parse_qs(urlparse(notification_url).query)["context"][0]
        response = handle_verify(context, auth_data)

        if isinstance(response, dict) and "error" in response:
            console.print(f"\n[red]{response['error']}[/]\n")
            return None

        response_text = json.loads(response.text[11:])

    return response_text


def handle_browser_qr(auth_data: dict, choice: str) -> dict:
    auth_data["_json"] = False

    while True:
        try:
            response = get(LONGPOLLING_URL, params=auth_data)
            response_text = json.loads(response.text[11:])
        except Exception as e:
            console.print(f"\n[red]{e}[/]\n")
            return None

        timeout = response_text["timeout"]
        url = response_text["loginUrl"]
        lp = response_text["lp"]

        if choice == "1":
            if platform.system() in ("Linux", "Android"):
                os.system(f"xdg-open '{url}' 2>/dev/null")
            else:
                webbrowser.open(url)
        elif choice == "3":
            qrTips = response_text["qrTips"]
            console.print(f"\n[white]{qrTips}[/]\n")
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
            qr.add_data(url)
            qr.print_ascii()

        try:
            response = get(lp, timeout=timeout)
        except ConnectionError as e:
            error = str(e)
            if "timed out" in error:
                console.print("\n[red]Request timed out. Please try again.[/]\n")
            elif "Access denied" in error:
                console.print("\n[red]Access denied. Please try again.[/]\n")
            else:
                console.print(f"\n[red]{e}[/]\n")
                return None
            continue

        break

    response_text = json.loads(response.text[11:])
    return response_text
