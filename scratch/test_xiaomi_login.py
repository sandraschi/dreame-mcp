"""Test Xiaomi cloud login directly."""
import requests, hashlib, json, os
from dotenv import load_dotenv
load_dotenv()

user = os.environ["DREAME_USER"]
pwd = os.environ["DREAME_PASSWORD"]
print(f"User: {user}")

s = requests.session()
s.cookies.set("sdkVersion", "3.8.6", domain="mi.com")
s.cookies.set("sdkVersion", "3.8.6", domain="xiaomi.com")

# Step 1: get _sign
r1 = s.get("https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true",
    headers={"User-Agent": "Android-7.1.1-1.0.0-ONEPLUS A3010-136-00000000 APP/xiaomi.smarthome APPV/62830"})
print(f"Step 1 status: {r1.status_code}")
print(f"Step 1 text (first 500): {r1.text[:500]}")
