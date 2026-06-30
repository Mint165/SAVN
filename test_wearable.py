import asyncio
import struct
import time
import math
import websockets

# Format: uint32 timestamp_ms, 5x float (ppg_clean, ppg_raw, ax, ay, az)
_FMT = "<Iffff f"
_SIZE = struct.calcsize(_FMT)
_BATCH = 10

async def send_mock_data():
    uri = "ws://127.0.0.1:8000/ws/wearable"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            # Send device ID
            await ws.send("SIMULATOR_01")
            print("Connected! Sending mock data...")
            
            start_time = time.time()
            t = 0.0
            
            while True:
                batch_data = bytearray()
                for _ in range(_BATCH):
                    ts_ms = int((time.time() - start_time) * 1000)
                    
                    # Generate somewhat realistic signals
                    ppg_clean = math.sin(t * 5) * 0.8  # 5 rad/s ~ 0.8 Hz pulse
                    ppg_raw = ppg_clean + (math.sin(t * 50) * 0.2) # Add noise
                    
                    ax = math.sin(t) * 0.5
                    ay = math.cos(t) * 0.5
                    az = 1.0 + math.sin(t * 2) * 0.1 # Gravity + small oscillation
                    
                    packed = struct.unpack("24B", struct.pack(_FMT, ts_ms, ppg_clean, ppg_raw, ax, ay, az))
                    batch_data.extend(packed)
                    
                    t += 0.02 # 20ms per sample -> 50Hz
                
                await ws.send(bytes(batch_data))
                await asyncio.sleep(0.2) # Send batch every 200ms
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(send_mock_data())
