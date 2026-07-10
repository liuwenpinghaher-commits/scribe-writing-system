---
title: "Blender Mcp"
url: "https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp

# Blender Mcp
Control Blender directly from Hermes via socket connection to the blender-mcp addon. Create 3D objects, materials, animations, and run arbitrary Blender Python (bpy) code. Use when user wants to create or modify anything in Blender.
## Skill metadata[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#skill-metadata "Direct link to Skill metadata")  
|   |   |  
| --- | --- |  
| Source  | Optional — install with `hermes skills install official/creative/blender-mcp`  |  
| Path  | `optional-skills/creative/blender-mcp`  |  
| Version  | `1.0.0`  |  
| Author  | alireza78a  |  
| Platforms  | linux, macos, windows  |  
## Reference: full SKILL.md[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#reference-full-skillmd "Direct link to Reference: full SKILL.md")
info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
# Blender MCP
Control a running Blender instance from Hermes via socket on TCP port 9876.
## Setup (one-time)[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#setup-one-time "Direct link to Setup \(one-time\)")
### 1. Install the Blender addon[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#1-install-the-blender-addon "Direct link to 1. Install the Blender addon")
curl -sL <https://raw.githubusercontent.com/ahujasid/blender-mcp/main/addon.py> -o ~/Desktop/blender_mcp_addon.py
In Blender: Edit > Preferences > Add-ons > Install > select blender_mcp_addon.py Enable "Interface: Blender MCP"
### 2. Start the socket server in Blender[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#2-start-the-socket-server-in-blender "Direct link to 2. Start the socket server in Blender")
Press N in Blender viewport to open sidebar. Find "BlenderMCP" tab and click "Start Server".
### 3. Verify connection[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#3-verify-connection "Direct link to 3. Verify connection")
nc -z -w2 localhost 9876 && echo "OPEN" || echo "CLOSED"
## Protocol[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#protocol "Direct link to Protocol")
Plain UTF-8 JSON over TCP -- no length prefix.
Send: {"type": "<command>", "params": {<kwargs>}} Receive: {"status": "success", "result": <value>} {"status": "error", "message": "<reason>"}
## Available Commands[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#available-commands "Direct link to Available Commands")  
| type  | params  | description  |  
| --- | --- | --- |  
| execute_code  | code (str)  | Run arbitrary bpy Python code  |  
| get_scene_info  | (none)  | List all objects in scene  |  
| get_object_info  | object_name (str)  | Details on a specific object  |  
| get_viewport_screenshot  | (none)  | Screenshot of current viewport  |  
## Python Helper[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#python-helper "Direct link to Python Helper")
Use this inside execute_code tool calls:
import socket, json
def blender_exec(code: str, host="localhost", port=9876, timeout=15): s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) s.connect((host, port)) s.settimeout(timeout) payload = json.dumps({"type": "execute_code", "params": {"code": code}}) s.sendall(payload.encode("utf-8")) buf = b"" while True: try: chunk = s.recv(4096) if not chunk: break buf += chunk try: json.loads(buf.decode("utf-8")) break except json.JSONDecodeError: continue except socket.timeout: break s.close() return json.loads(buf.decode("utf-8"))
## Common bpy Patterns[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#common-bpy-patterns "Direct link to Common bpy Patterns")
### Clear scene[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#clear-scene "Direct link to Clear scene")
bpy.ops.object.select_all(action='SELECT') bpy.ops.object.delete()
### Add mesh objects[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#add-mesh-objects "Direct link to Add mesh objects")
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0)) bpy.ops.mesh.primitive_cube_add(size=2, location=(3, 0, 0)) bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=2, location=(-3, 0, 0))
### Create and assign material[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#create-and-assign-material "Direct link to Create and assign material")
mat = bpy.data.materials.new(name="MyMat") mat.use_nodes = True bsdf = mat.node_tree.nodes.get("Principled BSDF") bsdf.inputs["Base Color"].default_value = (R, G, B, 1.0) bsdf.inputs["Roughness"].default_value = 0.3 bsdf.inputs["Metallic"].default_value = 0.0 obj.data.materials.append(mat)
### Keyframe animation[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#keyframe-animation "Direct link to Keyframe animation")
obj.location = (0, 0, 0) obj.keyframe_insert(data_path="location", frame=1) obj.location = (0, 0, 3) obj.keyframe_insert(data_path="location", frame=60)
### Render to file[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#render-to-file "Direct link to Render to file")
bpy.context.scene.render.filepath = "/tmp/render.png" bpy.context.scene.render.engine = 'CYCLES' bpy.ops.render.render(write_still=True)
## Pitfalls[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-blender-mcp#pitfalls "Direct link to Pitfalls")
  * Must check socket is open before running (nc -z localhost 9876)
  * Addon server must be started inside Blender each session (N-panel > BlenderMCP > Connect)
  * Break complex scenes into multiple smaller execute_code calls to avoid timeouts
  * Render output path must be absolute (/tmp/...) not relative
  * shade_smooth() requires object to be selected and in object mode
