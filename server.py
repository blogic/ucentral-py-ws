#!/usr/bin/env python
# WS server example

import asyncio
import websockets
import json

connected = set()
clients = {}

async def cmd_error(client, reply = {"error": "invalid command"}):
	await client.send(json.dumps(reply))

async def config_load_file(serial):
	with open(f"configs/{serial}") as json_file:
		return json.load(json_file)

async def config_load(client, cmd):
	serial = cmd["serial"]
	uuid = cmd["uuid"]
	try:
		cfg = await config_load_file(serial)
		clients[serial] = {"client": client, "serial": serial, "uuid": uuid, "config": cfg,}
		print(f"{serial} config loaded")
	except:
		await cmd_error(client, {"error": "unknown serial" })

async def state_store(serial, state):
	try:
		with open(f".{serial}.state", 'w') as outfile:
			json.dump(state, outfile)
		clients[serial]["state"] = state
		uuid = state["uuid"]
		print(f"{serial} new state {uuid}")
	except:
		print(f"{serial} failed to store state")

async def server(client, path):
	print (f"connect {client.remote_address[0]}")
	connected.add(client)
	try:
		while True:
			data = await client.recv()
			print(data)
			cmd = json.loads(data)
			if "serial" in cmd and "uuid" in cmd:
				global clients
				serial = cmd["serial"]
				uuid = cmd["uuid"]
				if serial not in clients:
					await config_load(client, cmd)
				elif clients[serial]["uuid"] != uuid:
					clients[serial]["uuid"] = uuid
					print(f"{serial} received new config")
				if "state" in cmd and "uuid" in cmd["state"]:
					await state_store(serial, cmd["state"])
				else:
					print(f"{serial} has config {uuid}")
	except Exception as e:
		print(e)
		print (f"error {client.remote_address[0]}")
		connected.remove(client)

	finally:
		print (f"disconnect {client.remote_address[0]}")
		if client in connected:
			connected.remove(client)


async def timer():
	while True:
		for serial, client in list(clients.items()):
			if client["client"] not in connected:
				del clients[serial]
				continue
			try:
				client["config"] = await config_load_file(serial)
			except:
				print(f"{serial} config failed to load")
				continue;
			if client["uuid"] != client["config"]["uuid"]:
				print(f"{serial} sending new config")
				await client["client"].send(json.dumps({"cfg": client["config"]}))
		await asyncio.sleep(5)

start_server = websockets.serve(server, "localhost", 8765,
	create_protocol=websockets.basic_auth_protocol_factory(
		realm="venue", credentials=("test", "test")
	),
)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_until_complete(timer())
asyncio.get_event_loop().run_forever()
