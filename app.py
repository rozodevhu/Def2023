import sqlite3
import json
import uuid
from flask import Flask, jsonify, request
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)
DB_FILE = "database.db"

# ==================== DATABASE INITIALIZATION ====================
def init_db():
    """Builds persistent tables to track client accounts and environments."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                tokens INTEGER DEFAULT 500,
                avatar_data TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_rooms (
                room_id TEXT PRIMARY KEY,
                room_name TEXT,
                room_data TEXT
            )
        ''')
        # Insert a default Administrator testing profile
        cursor.execute('''
            INSERT OR IGNORE INTO players (id, username, display_name, avatar_data)
            VALUES (1, 'LocalAdmin', 'Local Admin Host', '{"Version":4,"SkinColor":1,"HairType":2,"OutfitType":1}')
        ''')
        conn.commit()

init_db()

# Memory pools for tracking multiplayer sync sockets
connected_sockets = {}       # { player_id: socket_connection }
active_room_instances = {}   # { room_id: {"Name": "Lounge", "Players": [id1, id2]} }

# ==================== 1. SECURITY & PROFILE HANDSHAKES ====================

@app.route('/api/config/v2', methods=['GET'])
def get_server_config():
    """Unlocks sandbox items, custom outfits, and custom map structures."""
    return jsonify({
        "App.MinVersion": "20190101",
        "Sandbox.Enabled": True,
        "CustomRooms.CreationEnabled": True,
        "Clubs.Enabled": True,
        "Outfits.Enabled": True,
        "CreatorEconomy.Enabled": True,
        "Photon.AppId": "00000000-0000-0000-0000-000000000000"
    })

@app.route('/api/v1/login', methods=['POST'])
def player_login_gateway():
    return jsonify({
        "Token": "secure_session_token_authorized_unlocked",
        "PlayerId": 1,
        "ScreenName": "LocalAdmin",
        "Status": 0
    })

@app.route('/api/players/v1/<int:player_id>', methods=['GET'])
def fetch_account_profile(player_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, display_name, xp, level FROM players WHERE id = ?", (player_id,))
        row = cursor.fetchone()
        if row:
            return jsonify({"Id": player_id, "ScreenName": row[0], "Username": row[0], "DisplayName": row[1], "RegistrationStatus": 2, "Level": row[3], "XP": row[2]})
    return jsonify({"Result": 1, "Message": "Profile not found"}), 404

# ==================== 2. PERSISTENT ACCESSIBLE AVATARS & INVENTORY ====================

@app.route('/api/avatar/v2', methods=['GET'])
def query_player_avatar():
    p_id = request.args.get("playerId", 1, type=int)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT avatar_data FROM players WHERE id = ?", (p_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
    return '{"Version":4,"SkinColor":0,"HairType":0,"OutfitType":0}'

@app.route('/api/avatar/v2/saved', methods=['POST'])
def preserve_avatar_modifications():
    data = request.json or {}
    p_id = data.get("PlayerId", 1)
    stringified_avatar = json.dumps(data)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET avatar_data = ? WHERE id = ?", (stringified_avatar, p_id))
        conn.commit()
    return jsonify({"Result": 0})

@app.route('/api/playeritems/v1/get', methods=['GET'])
def claim_full_inventory():
    """Instantly unlocks all cosmetic items and gear tools."""
    return jsonify([{"ItemType": 1, "ItemId": item, "Count": 1, "IsEquipped": False} for item in range(1, 3000)])

# ==================== 3. MULTIPLAYER ARCHITECTURE (PHOTON ORCHESTRATION) ====================

@app.route('/api/matchmaking/v4/joinroom', methods=['POST'])
def balance_room_matchmaking():
    """Arranges active clients onto identical target map instances."""
    data = request.json or {}
    room_name = data.get("RoomName", "Lounge")
    p_id = data.get("PlayerId", 1)
    room_hash = str(hash(room_name) & 0xffffffff)
    
    if room_hash not in active_room_instances:
        active_room_instances[room_hash] = {"Name": room_name, "Players": []}
    if p_id not in active_room_instances[room_hash]["Players"]:
        active_room_instances[room_hash]["Players"].append(p_id)
        
    dispatch_websocket_broadcast(room_hash, {
        "EventCode": 102,
        "Data": {"PlayerId": p_id, "Action": "Joined", "Room": room_name}
    }, exclusion_id=p_id)

    return jsonify({
        "Result": 0,
        "Room": {
            "RoomId": int(room_hash),
            "Name": room_name,
            "MaxPlayers": 40,
            "Players": active_room_instances[room_hash]["Players"]
        },
        "PhotonRegion": "USW",
        "PhotonServerAddress": "127.0.0.1:5055",  # Pointing to local Photon Core Relay
        "CustomRoomId": str(uuid.uuid4())
    })

# ==================== 4. MAKER PEN PERSISTENT STORAGE ====================

@app.route('/api/rooms/v2/save', methods=['POST'])
def serialize_makerpen_world():
    data = request.json or {}
    r_id = str(data.get("RoomId", "default_lobby"))
    r_name = data.get("RoomName", "Custom Room")
    r_blob = data.get("Data", "")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO saved_rooms (room_id, room_name, room_data) VALUES (?, ?, ?)", (r_id, r_name, r_blob))
        conn.commit()
    return jsonify({"Result": 0, "Message": "World saved permanently!"})

@app.route('/api/rooms/v2/load', methods=['GET'])
def deserialize_makerpen_world():
    r_id = request.args.get("roomId", "default_lobby")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT room_data FROM saved_rooms WHERE room_id = ?", (r_id,))
        row = cursor.fetchone()
        if row:
            return jsonify({"Data": row[0]})
    return jsonify({"Data": '{"Objects":[],"Variables":[],"CircuitsV2":[]}'})

# ==================== 5. REAL-TIME WEBSOCKETS ====================

@sock.route('/hub/v1/notification')
def master_notification_pipe(ws):
    p_id = None
    try:
        raw_handshake = ws.receive()
        p_id = int(request.args.get("playerId", 1))
        connected_sockets[p_id] = ws
        while True:
            msg = ws.receive()
            if msg is None: break
            ws.send('{"Id":1,"Msg":"HeartbeatReceived"}')
    except Exception:
        pass
    finally:
        if p_id in connected_sockets: del connected_sockets[p_id]

def dispatch_websocket_broadcast(room_key, structure, exclusion_id=None):
    pool = active_room_instances.get(room_key, {}).get("Players", [])
    for client_id in pool:
        if client_id != exclusion_id and client_id in connected_sockets:
            try:
                connected_sockets[client_id].send(json.dumps(structure))
            except Exception:
                pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
