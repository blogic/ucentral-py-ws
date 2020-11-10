#!/usr/bin/env python

import asyncio
import websockets
import json
import pathlib
import ssl

connected = set()
clients = {}

config = {}

async def cmd_error(client, reply = {"error": "invalid command"}):
	await client.send(json.dumps(reply))

async def serial_load_file(serial):
	with open(f"{config['config_folder']}{serial}") as json_file:
		return json.load(json_file)

async def serial_load(client, cmd):
	serial = cmd["serial"]
	uuid = cmd["uuid"]
	try:
		cfg = await serial_load_file(serial)
		clients[serial] = {"client": client, "serial": serial, "uuid": uuid, "config": cfg,}
		print(f"{serial} config loaded")
	except:
		print(f"{serial} no config found")
		await cmd_error(client, {"error": "unknown serial" })

async def state_store(serial, state):
	try:
		with open(f"{config['state_folder']}{serial}", 'w') as outfile:
			json.dump(state, outfile)
		uuid = state["uuid"]
		print(f"{serial} new state {uuid}")
	except:
		print(f"{serial} failed to store state")

async def capab_store(serial, capab):
	try:
		with open(f"{config['capab_folder']}{serial}", 'w') as outfile:
			json.dump(capab, outfile)
		print(f"{serial} new capabilities")
	except:
		print(f"{serial} failed to store capabilities")

async def server(client, path):
	print (f"connect {client.remote_address[0]}")
	connected.add(client)
	try:
		while True:
			data = await client.recv()
			#print(data)
			cmd = json.loads(data)
			if "serial" in cmd and "uuid" in cmd:
				global clients
				serial = cmd["serial"]
				uuid = cmd["uuid"]
				if serial not in clients:
					await serial_load(client, cmd)
				elif clients[serial]["uuid"] != uuid:
					clients[serial]["uuid"] = uuid
					print(f"{serial} received new config")
				if "active" in cmd:
					active = cmd["active"]
					print(f"{serial} has config {uuid} but is using {active}")
				else:
					print(f"{serial} has config {uuid}")
			if "serial" in cmd and "capab" in cmd:
				await capab_store(cmd["serial"], cmd["capab"])
			if "state" in cmd and "uuid" in cmd["state"]:
				await state_store(cmd["serial"], cmd["state"])
	except Exception as e:
		#print(e)
		connected.remove(client)

	finally:
		if client in connected:
			connected.remove(client)


async def timer():
	while True:
		for serial, client in list(clients.items()):
			if client["client"] not in connected:
				print(f"{serial} disconnected")
				del clients[serial]
				continue
			try:
				client["config"] = await serial_load_file(serial)
			except:
				print(f"{serial} config failed to load")
				continue;
			if client["uuid"] != client["config"]["uuid"]:
				print(f"{serial} sending new config")
				await client["client"].send(json.dumps({"uuid": client["config"]["uuid"], "cfg": client["config"]}))
		await asyncio.sleep(5)

with open(f"usync.cfg") as json_file:
	config = json.load(json_file)
for k in { "ssl_key", "ssl_cert", "bind", "port", "config_folder" }:
	if k not in config:
		print(f"{k} is missing from in the config file")
		exit(-1)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(config["ssl_cert"], config["ssl_key"])

start_server = websockets.serve(server, config["bind"], config["port"],
	ssl=ssl_context,
	create_protocol=websockets.basic_auth_protocol_factory(
		realm="venue", credentials=("test", "test")
	),
)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_until_complete(timer())
asyncio.get_event_loop().run_forever()
