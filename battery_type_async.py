"""One HTTP method, delayed rotation, no database dependency. Python 3.11+."""
import asyncio
import json
import math
import os
import urllib.request
import urllib.error

API = os.environ.get('BATTERY_TYPE_API_URL', 'http://127.0.0.1:53000/api')
KEY = os.environ.get('BATTERY_TYPE_ASYNC_KEY', 'battery8')
DELAY = float(os.environ.get('BATTERY_TYPE_ROTATION_DELAY', '7'))
if not 5 <= DELAY <= 10:
    raise ValueError('Delay must be 5–10 seconds')
tasks = {}

def request_api(path, data=None):
    req = urllib.request.Request(API+path, data=json.dumps(data).encode() if data else None,
        headers={'Content-Type': 'application/json', 'X-Battery-Type-Key': KEY},
        method='PUT' if data else 'GET')
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)

async def rotate(battery_type_id):
    try:
        previous = await asyncio.to_thread(request_api, f'/battery_type/feed?id={battery_type_id}')
        await asyncio.sleep(DELAY)
        result = dict(previousX=previous['rotationX'], previousY=previous['rotationY'],
            rotationX=(previous['rotationX']+math.pi/6) % (2*math.pi),
            rotationY=(previous['rotationY']+math.pi/4) % (2*math.pi))
        await asyncio.to_thread(request_api, f'/battery_type/{battery_type_id}/rotation', result)
        print(json.dumps({'batteryTypeId': battery_type_id, 'result': result}), flush=True)
    except Exception as error:
        print(json.dumps({'batteryTypeId': battery_type_id, 'error': str(error)}), flush=True)
    finally:
        tasks.pop(battery_type_id, None)

async def handle(reader, writer):
    status, body = 400, {'error': 'Invalid request'}
    try:
        head = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 5)
        lines = head.decode('latin1').split('\r\n')
        method, path, _ = lines[0].split(' ')
        headers = dict(line.lower().split(':', 1) for line in lines[1:] if ':' in line)
        length = int(headers.get('content-length', '0'))
        if not 0 < length <= 4096:
            raise ValueError('Body length 1–4096 required')
        payload = json.loads(await asyncio.wait_for(reader.readexactly(length), 5))
        if method != 'POST' or path != '/battery_type/rotation':
            status, body = 404, {'error': 'POST /battery_type/rotation required'}
        elif type(payload.get('batteryTypeId')) is not int or payload['batteryTypeId'] < 1:
            raise ValueError('Positive batteryTypeId required')
        else:
            identity = payload['batteryTypeId']
            # Validate existence before accepting. No next=true, so no recursive job.
            await asyncio.to_thread(request_api, f'/battery_type/feed?id={identity}')
            if identity not in tasks:
                tasks[identity] = asyncio.create_task(rotate(identity))
            status, body = 202, dict(batteryTypeId=identity, delaySeconds=DELAY, status='scheduled')
    except urllib.error.HTTPError as error:
        status, body = error.code, {'error': 'Main API rejected battery_type'}
    except Exception as error:
        body = {'error': str(error)}
    data = json.dumps(body).encode()
    writer.write(f'HTTP/1.1 {status} Response\r\nContent-Type: application/json\r\nContent-Length: {len(data)}\r\nConnection: close\r\n\r\n'.encode()+data)
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle, os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '53002')), limit=8192)
    print('battery_type asyncio :53002', flush=True)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
