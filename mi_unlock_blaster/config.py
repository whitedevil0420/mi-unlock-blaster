# config.py - Endpoint configuration and style definitions for Mi Unlock Blaster

# Mi Community endpoints
STATE_URL = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
APPLY_URL = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
INFO_URL = "https://sgp-api.buy.mi.com/bbs/api/global/user/data"

# Xiaomi Account login endpoints
BASE_URL = "https://account.xiaomi.com"
SERVICELOGIN_URL = "https://account.xiaomi.com/pass/serviceLogin"
SERVICELOGINAUTH2_URL = "https://account.xiaomi.com/pass/serviceLoginAuth2"
LIST_URL = "https://account.xiaomi.com/identity/list"
SEND_EM_TICKET = "https://account.xiaomi.com/identity/auth/sendEmailTicket"
SEND_PH_TICKET = "https://account.xiaomi.com/identity/auth/sendPhoneTicket"
VERIFY_EM = "https://account.xiaomi.com/identity/auth/verifyEmail"
VERIFY_PH = "https://account.xiaomi.com/identity/auth/verifyPhone"
USERQUOTA_URL = "https://account.xiaomi.com/identity/pass/sms/userQuota"
REGION_URL = "https://account.xiaomi.com/pass/user/login/region"
CONFIG_URL = "https://account.xiaomi.com/pass2/config"
LONGPOLLING_URL = "https://account.xiaomi.com/longPolling/loginUrl"
CONFIGURATION_URL = "https://api.account.xiaomi.com/pass/configuration"

# Styling / Console
from rich.console import Console
from rich.theme import Theme

c_theme = Theme({
    "orange": "bold #ff6900",
    "green":  "bold #00c853",
    "red":    "bold #d50000",
    "white":  "bold white",
})

console = Console(theme=c_theme)
loader = console.status("", spinner="dots")
