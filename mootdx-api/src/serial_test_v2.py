
import socket
import time
from mootdx.quotes import Quotes

def test_single(ip):
    start = time.time()
    try:
        # Socket check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.connect((ip, 7709))
        sock.close()
        
        # Protocol check
        try:
            client = Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=2.0)
            # Use a verified method from mootdx_handler
            df = client.quotes(symbol=['000001'])
            if df is not None and not df.empty:
                return True, (time.time() - start)*1000
            else:
                return False, "Empty Data"
        except Exception as e:
            return False, f"Protocol Fail: {str(e)}"
    except Exception as e:
        return False, f"Socket Fail: {str(e)}"

# A more focused list around the working prefix 139.* and 175.*
targets = [
    "175.6.5.153", "139.9.51.18", "139.159.239.163", "139.9.133.247",
    "139.9.133.153", "139.9.133.18", "139.9.51.163", "139.159.239.18",
    "116.205.163.254", "116.205.171.132", "116.205.183.150", 
    "121.36.217.200", "121.36.217.201", "121.36.217.202",
    "124.71.187.122", "119.147.212.81", "123.60.84.66"
]

print("Starting refined serial test...")
for ip in targets:
    ok, val = test_single(ip)
    if ok:
        print(f"✅ {ip:15} | {val:7.2f}ms")
    else:
        # print(f"❌ {ip:15} | {val}")
        pass
    time.sleep(0.3)
