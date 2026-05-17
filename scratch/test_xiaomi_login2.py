"""Test Xiaomi cloud login step 1 + 2."""
import requests, hashlib, json, os
from dotenv import load_dotenv
load_dotenv()

user = os.environ["DREAME_USER"]
pwd = os.environ["DREAME_PASSWORD"]

s = requests.session()
s.cookies.set("sdkVersion", "3.8.6", domain="mi.com")
s.cookies.set("sdkVersion", "3.8.6", domain="xiaomi.com")
s.cookies.set("deviceId", "00000000000000000000000000000000", domain="mi.com")
s.cookies.set("deviceId", "00000000000000000000000000000000", domain="xiaomi.com")
ua = "Android-7.1.1-1.0.0-ONEPLUS A3010-136-00000000 APP/xiaomi.smarthome APPV/62830"

# Step 1
r1 = s.get("https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true",
    headers={"User-Agent": ua})
print(f"Step 1: {r1.status_code}", flush=True)
t1 = r1.text.encode('utf-8', errors='replace').decode('utf-8')
print(f"Response: {t1[:400]}", flush=True)

# Parse _sign
try:
    d1 = json.loads(r1.text.replace("&&&START&&&", ""))
    sign = d1.get("_sign")
    print(f"Sign: {sign}", flush=True)
except Exception as e:
    print(f"Parse error: {e}", flush=True)
    # Try to find _sign manually
    import re
    m = re.search(r'"_sign":"([^"]+)"', r1.text)
    if m:
        sign = m.group(1)
        print(f"Sign (regex): {sign}", flush=True)
    else:
        print("No sign found", flush=True)
        sign = None

# Step 2
data = {
    "user": user,
    "hash": hashlib.md5(pwd.encode()).hexdigest().upper(),
    "callback": "https://sts.api.io.mi.com/sts",
    "sid": "xiaomiio",
    "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
}
if sign:
    data["_sign"] = sign

r2 = s.post("https://account.xiaomi.com/pass/serviceLoginAuth2",
    headers={"User-Agent": ua, "Content-Type": "application/x-www-form-urlencoded"},
    data=data, params={"_json": "true"})
print(f"\nStep 2: {r2.status_code}", flush=True)
t2 = r2.text.encode('utf-8', errors='replace').decode('utf-8')
print(f"Response: {t2[:800]}", flush=True)
