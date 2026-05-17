"""Try MQTT-based command sending to DreameHome device."""
import logging, sys, os, json, ssl
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

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

# Get device info to get MQTT broker info
info = cloud.get_device_info()
if info:
    print(f"Device: {info.get('customName', '?')} online={info.get('online')}", flush=True)
    print(f"Bind domain: {info.get('bindDomain', '?')}", flush=True)
    print(f"UUID: {cloud._uuid}", flush=True)
    
    # MQTT broker info
    bind_domain = info.get("bindDomain", "")
    host_part = bind_domain.split(":")
    mqtt_host = host_part[0]
    mqtt_port = int(host_part[1]) if len(host_part) > 1 else 8883
    
    print(f"MQTT broker: {mqtt_host}:{mqtt_port}", flush=True)
    print(f"MQTT user: {cloud._uuid}", flush=True)
    print(f"MQTT key: {cloud._key[:20]}...", flush=True)
    
    # Topic for this device
    topic_base = f"/status/{did}/{cloud._uid}/{info.get('model', '?')}/{country}/"
    print(f"Status topic: {topic_base}", flush=True)
    
    # Try to set up MQTT from the protocol's own connect method
    import paho.mqtt.client as mqtt
    
    def on_connect(client, userdata, flags, rc):
        print(f"MQTT connected: rc={rc}", flush=True)
        # Subscribe to receive status
        client.subscribe(topic_base)
        print(f"Subscribed to {topic_base}", flush=True)
        
        # Try publishing a command
        # Common DreameHome MQTT command topic patterns:
        cmd_topics = [
            f"/command/{did}/{cloud._uid}/{info.get('model', '?')}/{country}/",
            f"/{did}/{cloud._uid}/{info.get('model', '?')}/command",
            f"/device/{did}/command",
        ]
        
        cmd_msg = json.dumps({
            "id": 100,
            "did": did,
            "method": "action",
            "params": {
                "did": did,
                "siid": 2,
                "aiid": 1,
                "in": [],
            },
        })
        
        for ct in cmd_topics:
            result = client.publish(ct, cmd_msg)
            print(f"Published to {ct}: {result.rc}", flush=True)
    
    def on_message(client, userdata, msg):
        print(f"MQTT message on {msg.topic}: {msg.payload[:200]}", flush=True)
    
    def on_disconnect(client, userdata, rc):
        print(f"MQTT disconnected: rc={rc}", flush=True)
    
    mqttc = mqtt.Client(client_id=f"dreame-mcp-test-{os.urandom(4).hex()}")
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.on_disconnect = on_disconnect
    mqttc.username_pw_set(cloud._uuid, cloud._key)
    mqttc.tls_set(cert_reqs=ssl.CERT_NONE)
    mqttc.tls_insecure_set(True)
    mqttc.connect_timeout = 10
    
    print(f"Connecting to {mqtt_host}:{mqtt_port}...", flush=True)
    mqttc.connect(mqtt_host, mqtt_port, keepalive=60)
    mqttc.loop_start()
    
    # Wait for responses
    import time
    time.sleep(5)
    mqttc.disconnect()
    mqttc.loop_stop()
    print("Done", flush=True)
else:
    print("Failed to get device info", flush=True)
