import json
from .config import CONFIG_URL, CONFIGURATION_URL, REGION_URL, console
from .requester import session, get

def get_region(auth_cookies):
    for k, v in auth_cookies.items():
        session.cookies.set(k, v)

    try:
        response = get(REGION_URL)
        response_text = json.loads(response.text[11:])
    except Exception as e:
        console.print(f"\n[red]{e}[/]\n")
        return None
    finally:
        session.cookies.clear()

    region = response_text.get("data", {}).get("region")

    if not region and response_text.get('code') != 0:
        console.print(f"\n[red]Failed to get account region | Response: {response_text}[/]\n")
        return None
    elif not region:
        console.print(f"\n[red]Failed to get account region[/]\n")
        return None

    return region


def select_manually():
    _ZONES = ["Singapore", "China", "Russia", "India", "Europe"]
    console.print("\n[white]Select dataCenterZone:[/white]")
    console.print("[white]" + "─" * 40 + "[/white]")
    for i, zone in enumerate(_ZONES, 1):
        console.print(f"  [orange]{i}.[/orange] [white]{zone}[/white]")
    console.print("[white]" + "─" * 40 + "[/white]\n")

    while True:
        choice = console.input(f"[white]Select (1-{len(_ZONES)}): [/white]").strip()

        if not choice.isdigit():
            console.print("[red]Invalid input. Enter a number.[/red]\n")
            continue

        idx = int(choice) - 1
        if 0 <= idx < len(_ZONES):
            Zone = _ZONES[idx]
            console.print(f"\n[green]dataCenterZone selected: {Zone}[/green]\n")
            return Zone

        console.print(f"[red]Out of range. Enter 1–{len(_ZONES)}.[/red]\n")


def get_with_userId(userId):
    try:
        response = get(CONFIGURATION_URL, params={'keys': 'idc'})
        response_text = json.loads(response.text)
    except Exception as e:
        console.print(f"\n[red]{e}[/]\n")
        return None

    idc = response_text["data"]["idc"]

    for name, info in idc.items():
        ranges = [{"min": info["userId.min"], "max": info["userId.max"]}]
        for ext in info.get("extend.idRange", []):
            ranges.append({"min": ext["userId.min"], "max": ext["userId.max"]})
        for r in ranges:
            if r["min"] <= userId <= r["max"]:
                return name

    console.print(f"\n[red]Failed to get dataCenterZone with userId[/]\n")
    return None


def get_with_region(region):
    try:
        response = get(CONFIG_URL, params={'key': 'regionConfig'})
        response_text = json.loads(response.text[11:])
    except Exception as e:
        console.print(f"\n[red]{e}[/]\n")
        return None

    Zone = next(
        (k for k, v in response_text.get("regionConfig", {}).items()
         if v.get("region.codes") and region in v["region.codes"]),
        None
    )

    if Zone is None:
        console.print(f"\n[red]Failed to get dataCenterZone from region account[/]\n")

    return Zone


def get_dataCenterZone(value=None):
    value_str = str(value).strip() if value is not None else ""

    if value_str.isdigit():
        Zone = get_with_userId(int(value_str))
    elif value_str.isalpha():
        Zone = get_with_region(value_str)
    else:
        Zone = select_manually()

    session.cookies.clear()
    return Zone


def get_uRegion():
    try:
        params = {'key': 'uRegion'}
        response = get(CONFIG_URL, params=params)
        response_text = json.loads(response.text[11:])
    except Exception as e:
        console.print(f"\n[red]{e}[/]\n")
        return None

    uRegion = response_text.get("uRegion")

    if not uRegion:
        console.print(f"\n[red]Failed to get uRegion | Response: {response_text}[/]\n")
        return None

    return uRegion


def get_uLocale():
    try:
        params = {'key': 'uLocale'}
        response = get(CONFIG_URL, params=params)
        response_text = json.loads(response.text[11:])
    except Exception as e:
        console.print(f"\n[red]{e}[/]\n")
        return None
    finally:
        session.cookies.clear()

    uLocale = response_text.get("uLocale")

    if not uLocale:
        console.print(f"\n[red]Failed to get uLocale | Response: {response_text}[/]\n")
        return None

    return uLocale


def get_areaConfig(country_code: str) -> dict:
    try:
        params = {'key': 'areaConfig'}
        response = get(CONFIG_URL, params=params)
        response_text = json.loads(response.text[11:])
    except Exception as e:
        console.print(f"\n[red]{e}[/]\n")
        return None

    areas = response_text.get("areaConfig")

    if not areas:
        console.print(f"\n[red]Failed to get areaConfig | Response: {response_text}[/]\n")
        return None

    for letter, countries in areas.items():
        for country in countries:
            if country["B"] == country_code:
                return {
                    "code": country["B"],
                    "name": country["C"],
                    "dial": country["N"]
                }

    return None
