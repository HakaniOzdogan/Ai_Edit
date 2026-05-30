import asyncio
import websockets
import json


async def test():
    uri = "ws://localhost:8765/ws"
    print(f"Bağlanıyor: {uri}")
    async with websockets.connect(uri) as ws:
        print("Bağlandı!")

        msg = {"type": "command", "command": "merhaba test", "project_id": "test_001"}
        await ws.send(json.dumps(msg))
        print(f"Gönderildi: {msg}")

        for _ in range(2):
            response = await ws.recv()
            data = json.loads(response)
            print(f"Yanıt: {data}")

        print("Test PASSED")


asyncio.run(test())
