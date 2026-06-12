import re
import json
from urllib.request import urlopen
from .auth import get_passtoken, get_service
from .config import STATE_URL, APPLY_URL, INFO_URL

VERSION_NAME = None
VERSION_CODE = None

def get_version():
    try:
        url = "https://play.google.com/store/apps/details?id=com.mi.global.bbs&hl=en&gl=us"
        dom = urlopen(url).read().decode("UTF-8")

        for match in re.finditer(r"AF_initDataCallback[\s\S]*?</script", dom):
            if re.search(r"(ds:5)'", match.group()):
                value_match = re.search(r"data:([\s\S]*?), sideChannel: {}}\);<\/", match.group())
                if value_match:
                    v_name = json.loads(value_match.group(1))[1][2][140][0][0][0]
                    major, minor, patch = v_name.split(".")
                    v_code = int(major) * 100000 + int(minor) * 100 + int(patch)
                    return v_name, v_code
    except:
        pass

    return "5.4.11", 500411


def get_headers(silent=False):
    sid = '18n_bbs_global'
    params = {"sid": sid}
    
    if silent:
        passToken = get_passtoken(params, silent=True)
    else:
        passToken = get_passtoken(params)

    if passToken is None:
        return None

    service = get_service(passToken, params)
    if service is None:
        return None
        
    token = service['cookies']['new_bbs_serviceToken']
    device_id = service['servicedata']['deviceId']

    global VERSION_NAME, VERSION_CODE
    
    if VERSION_NAME is None or VERSION_CODE is None:
        print("\nFetching latest version from Google Play...")
        VERSION_NAME, VERSION_CODE = get_version()
        print(f"Version resolved: '{VERSION_NAME}' (code: {VERSION_CODE})")

    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'content-type': "application/json; charset=utf-8",
        'Cookie': f"new_bbs_serviceToken={token};versionCode={VERSION_CODE};versionName={VERSION_NAME};deviceId={device_id};"
    }

    return headers


def check_code_response(code, default_msg):
    error_map = {
        100001: "Parameter error",
        100002: "CSRF token validation failed",
        100003: "Operation failed",
        100004: "Login required",
        100005: "Hit keyword topic block",
        100008: "Error code 100008",
        100009: "You have been banned from posting content",
        100010: "No edit permission",
        100011: "Username already taken",
        100012: "Username already modified once",
        100013: "No add permission",
        700001: "Delete account wait",
        700002: "Delete data done",
        700003: "Delete account done",
        1010020006: "Direct message user blocked"
    }
    return error_map.get(code, default_msg)


def info(response):
    response_json = response.json()
    code = response_json.get('code')
    if code != 0:
        return {"code": -1, "message": check_code_response(code, response_json.get('msg'))}

    data = response_json.get("data")
    return data


def state(response):
    response_json = response.json()
    code = response_json.get('code')
    if code != 0:
        return {"code": -1, "message": check_code_response(code, response_json.get('msg'))}

    data = response_json.get("data")
    is_pass = data.get("is_pass")
    button_state = data.get("button_state")
    deadline_format = data.get("deadline_format", "")

    if is_pass == 1:
        message = f"You have been granted access to unlock until Beijing time {deadline_format} (mm/dd/yyyy)"
        return {"code": 1, "message": message, "response_json": response_json}
    else:
        if button_state == 1:
            message = "Apply for unlocking"
            return {"code": 2, "message": message, "response_json": response_json}
        elif button_state == 2:
            message = f"Account Error Please try again after {deadline_format} (mm/dd)"
            return {"code": 3, "message": message, "response_json": response_json}
        else:
            message = "Account must be registered over 30 days"
            return {"code": 4, "message": message, "response_json": response_json}


def apply(response):
    response_json = response.json()
    code = response_json.get('code')
    if code != 0:
        return {"code": -1, "message": check_code_response(code, response_json.get('msg'))}

    data = response_json.get("data")
    apply_result = data.get("apply_result")
    deadline_format = data.get("deadline_format", "")

    if apply_result == 1:
        message = "Application Successful"
        return {"code": 1, "message": message}
    elif apply_result in (2, 4):
        message = f"Account Error Please try again after {deadline_format} (mm/dd)"
        return {"code": 2, "message": message}
    elif apply_result == 3:
        if deadline_format:
            parts = deadline_format.split(' ', 1)
            d_date = parts[0]
            d_time = parts[1] if len(parts) > 1 else "00:00"
        else:
            d_date, d_time = "", "00:00"
        message = f"Application quota limit reached,please try again after {d_date} (mm/dd) {d_time} (GMT+8)"
        return {"code": 3, "message": message}
    elif apply_result == 5:
        message = "Sorry, application failed Please try again later"
        return {"code": 4, "message": message}
    elif apply_result == 6:
        message = "Please try again in a minute"
        return {"code": 5, "message": message}
    elif apply_result == 7:
        message = "Please try again later"
        return {"code": 6, "message": message}
