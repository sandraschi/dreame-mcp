"""Test DreameHome cloud command sending."""
import logging
import sys
import os
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv

load_dotenv()

import dreame_mcp.client as mc

ref_path = Path(os.environ.get("DREAME_REF_PATH", "D:/Dev/repos/tasshack_dreame_vacuum_ref"))
mc._bootstrap_protocol(ref_path)

username = os.environ.get("DREAME_USER", "").strip()
password = os.environ.get("DREAME_PASSWORD", "").strip()
country = os.environ.get("DREAME_COUNTRY", "eu").strip()
did = os.environ.get("DREAME_DID", "2045852486").strip()

cloud = mc._cloud_cls(
    username=username,
    password=password,
    country=country,
    account_type="dreame",
    auth_key=None,
    did=did,
)
ok = cloud.login()
print(f"Cloud login: {ok}", flush=True)

# Decode and show the strings
import base64
import zlib
import json

# DREAME_STRINGS from protocol.py
DREAME_STRINGS = (
    "eJzEve1z2zi2MP5d/RUq93ZnJ3aS+N3pdKe7xs5M4jexkzjpdKd6U5IISYgpUr"
    "RJ2U5n9m+/BwAJgiD1ZsvWzJ0PVS4TARwAB+eD5+Uvz3/8cfblj7OzX87enZ+"
)
DREAME_STRINGS_FULL = (
    "eJzEve1z2ziWMP5d/RUq93ZnJ3aS+N3pdKe7xs5M4jexkzjpdKd6U5IISYgpUr"
    "RJ2U5n9m+/BwAJgiD1ZsvWzJ0PVS4TARwAB+eD5+Uvz3/8cfblj7OzX87enZ+/"
    "e3d2dnZ2fvb27P27s/Pzd2fncEveb19mS5jz/7sUBvnL2W/n78/ffRRXX85+nr"
    "07P3s/P313/Fe3DP0Nnv799/+PBn3Muv9PfP2ftfPpy/W4XHhCv/8cvbn5bw0R"
    "fxj//8+f37ny9+/hywi+frn2dv31282//+fH4R14p///HL2w+Xv3x4f/Hm7B28"
    "ez37+eLDm4v3u+CzuL7/8vYv7+GXL5ef/nLO71l8efdp9sfFr+8/y+d+fvnoX3"
    "4CFD//9fzl7Hfff5z99Gv49p9fwVvvfvXT4sP7y3cfLq7effgBnv3y9uyXi3cfL"
    "j+8/3v4792HX+b03+f/+vnL+8t3by9/v/j16uXfsr4vfv04++MvX868+ybdf/lH"
    "+vNvH8JN+Ob//vL+0+X797+9j/+9+/Dr2/M/fnn76S/w5Jd3H/4S3v/7h7O/jp/n"
    "vOPf3y8+fnkX6P71l48fLz/9Mv/l7N3Lf36cLV78y0+yM/3DP399++ni109vPyz+"
    "9fbDv/zrz3/++u796/lPH998+Pjflz/9y4dP7xY/Pft0+ctPixd/fPcsPvrp3e8/"
    "P3v57uNflh8//fTfdn/++Jff/+u3Z8v/+Glc+b9e/Ty3f9H3/nH5yx/++NMn+/fv"
    "/6+f//T81e+LWf3Hz3/67y8+XD5/AZ+8/P35h/mH5y8+LK7+9ctn9t2bly+nF9+9"
    "/vB+cd3/4z+W//bvf/n+r8uf3r8Z/vqv15/K0L/86/X/PdfH8L+f/vzy/dUf/vvi"
    "xctf3r6fz14N589evP306pfLP/7+9R+zN59efn/18tVsdvWT558+/98/Ta3ZeuY"
)
decoded = json.loads(zlib.decompress(base64.b64decode(DREAME_STRINGS_FULL), zlib.MAX_WBITS | 32))

print(f"\n--- DREAME STRINGS ---", flush=True)
for i, s in enumerate(decoded):
    print(f"  [{i}] = {s!r}", flush=True)

# The API URL structure
api_url = f"https://{country}{decoded[0]}:{decoded[1]}"
print(f"\nAPI URL base: {api_url}", flush=True)

# The login endpoint
login_endpoint = f"{api_url}/{decoded[17]}"
print(f"Login endpoint: {login_endpoint}", flush=True)

# The sendCommand endpoint
host_part = ""
# Try sending directly with a simple python call
import requests

# Build the send command URL
host = ""
endpoint = f"{decoded[37]}{host}/{decoded[27]}/{decoded[38]}"
command_url = f"{api_url}/{endpoint}"
print(f"Command URL: {command_url}", flush=True)

# Try a different approach - maybe we need the host
print(f"\nstrings[9] (host hint): {decoded[9]!r}", flush=True)
print(f"strings[37]: {decoded[37]!r}", flush=True)
print(f"strings[27]: {decoded[27]!r}", flush=True)
print(f"strings[38]: {decoded[38]!r}", flush=True)
