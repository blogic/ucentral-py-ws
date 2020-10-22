#!/usr/bin/env python

import asyncio
import websockets
import json

serial = "00:11:22:33:44:55"
config = {"uuid": "0"}
state = {"uuid": "0", "cfg": 0 }
backend = None

async def config_heartbeat(server):
	uuid = config["uuid"]
	print(f"heartbeat uuid:{json.dumps(uuid)}")
	await server.send(json.dumps({"serial": serial, "uuid": config["uuid"]}))

async def state_heartbeat(server):
	uuid = state["uuid"]
	print(f"state uuid:{uuid}")
	await server.send(json.dumps({"serial": serial, "state": state, "uuid": config["uuid"]}))

async def config_error(server, uuid):
	print(f" error {json.dumps(uuid)}")
	await server.send(json.dumps({"serial": serial, "uuid": config["uuid"], "error": "failed to apply"}))

def config_load():
	global config
	try:
		with open(f".{serial}.cfg") as infile:
			config = json.load(infile)
		state["cfg"] = config["uuid"]
		print(f"loading config for {serial}")
	except:
		print("no config found")

async def config_store(server, data):
	global config
	try:
		with open(f".{serial}.cfg", 'w') as outfile:
			json.dump(data, outfile)
		config = data
		await config_heartbeat(server)
	except:
		await config_error(server, data["uuid"])

async def connect():
	uri = "ws://test:test@localhost:8765"
	async with websockets.connect(uri) as server:
		global backend
		backend = server
		await config_heartbeat(server)

		while True:
			data = await server.recv()
			cmd = json.loads(data)
			if "cfg" in cmd:
				await config_store(server, cmd["cfg"])

async def timer():
	while True:
		await asyncio.sleep(5)
		uuid = state["uuid"]
		cfg = config["uuid"]
		if cfg == uuid or backend is None:
			continue
		state["uuid"] = cfg;
		await state_heartbeat(backend)

config_load()
asyncio.ensure_future(timer())
asyncio.get_event_loop().run_until_complete(connect())
