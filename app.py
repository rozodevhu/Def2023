import sqlite3
import json
import uuid
from flask import Flask, jsonify, request
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)
DB_FILE = "database.db"

# ==================== 🛠️ AUTOMATED DATA ARCHITECTURE SETUP ====================
def init_complete_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Profiles tracking levels, tokens, and visual parameters
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                xp INTEGER DEFAULT 150000,
                level INTEGER DEFAULT 50,
                tokens INTEGER DEFAULT 999999,
                avatar_settings TEXT
            )
        ''')
        # Permanent purchase transaction storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                player_id INTEGER,
                item_id INTEGER,
                item_type INTEGER DEFAULT 1,
                PRIMARY KEY (player_id, item_id)
            )
        ''')
        # Custom Maker Pen room string storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_worlds (
                world_id TEXT PRIMARY KEY,
                world_name TEXT,
                world_data TEXT
            )
        ''')
        
        # Default Developer Profile
        default_avatar = '{"Version":4,"SkinColor":2,"HairType":3,"OutfitType":12,"Equipment":[]}'
        cursor.execute('''
            INSERT OR IGNORE INTO users (id, username, display_name, avatar_settings)
            VALUES (1, 'RecRoomAdmin', 'RecRoom Admin', ?)
        ''', (default_avatar,))
        conn.commit()

init_complete_db()

# Synchronized session memory arrays
online_sockets = {}
live_lobbies = {}

# ==================== ⌚ 1. MASTER WATCH INTERFACE HANDSHAKES ====================

@app.route('/api/config/v2', methods=['GET'])
def pull_watch_features():
    """Unlocks storefront loops, challenge feeds, and custom creations on the Watch."""
    return jsonify({
        "App.MinVersion": "20190101",
        "Sandbox.Enabled": True,
        "CustomRooms.CreationEnabled": True,
        "Clubs.Enabled": True,
        "Outfits.Enabled": True,
        "CreatorEconomy.Enabled": True,
        "Gifting.Enabled": True,
        "Store.Enabled": True,
        "Watch.DefaultTab": 0,
        "Photon.AppId": "00000000-0000-0000-0000-000000000000"
    })

@app.route('/api/v1/login', methods=['POST'])
def gatekeeper_login():
    """Handles immediate authentication when the user signs in."""
    return jsonify({
        "Token": "secure_unlocked_localhost_session_secret_token",
        "PlayerId": 1,
        "ScreenName": "RecRoomAdmin",
        "Status": 0
    })

@app.route('/api/players/v1/<int:player_id>', methods=['GET'])
def view_watch_profile(player_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, display_name, xp, level FROM users WHERE id = ?", (player_id,))
        row = cursor.fetchone()
        if row:
            return jsonify({
                "Id": player_id, "ScreenName": row[0], "Username": row[0],
                "DisplayName": row[1], "RegistrationStatus": 2, "Level": row[3], "XP": row[2]
            })
    return jsonify({"Id": 1, "ScreenName": "Guest", "Username": "Guest", "DisplayName": "Guest", "RegistrationStatus": 2, "Level": 1, "XP": 0})

# ==================== 💰 2. UNLIMITED TOKENS & ITEM SHOP PURCHASING ====================

@app.route('/api/currency/v1/wallet', methods=['GET'])
def output_watch_wallet():
    """Feeds dynamic token balance tracking straight onto the Watch display."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tokens FROM users WHERE id = 1")
        row = cursor.fetchone()
        tokens = row[0] if row else 999999
    return jsonify([{"CurrencyType": 0, "Balance": tokens}])

@app.route('/api/storefront/v3/giftpackages', methods=['GET'])
def pull_storefront_catalog():
    """Dynamically populates every cosmetic selection row in the Store tab."""
    mock_catalog = []
    # Loop generates 500 working cosmetic items inside the Watch's physical listing interface
    for i in range(1, 500):
        mock_catalog.append({
            "PackageId": i,
            "AvatarItemId": i,
            "ItemType": 1,
            "Cost": 250,  # Each item costs 250 tokens
            "Name": f"Cosmetic Gear Pro #{i}",
            "Description": "Unlocked via custom repository engine patch configurations."
        })
    return jsonify(mock_catalog)

@app.route('/api/storefront/v3/buy', methods=['POST'])
def execute_watch_purchase():
    """Handles real-time item collection balance tracking when you click 'Buy'."""
    data = request.json or {}
    item_id = data.get("AvatarItemId", 1)
    cost = data.get("Cost", 250)
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tokens FROM users WHERE id = 1")
        row = cursor.fetchone()
        current_tokens = row[0] if row else 0
        
        if current_tokens >= cost:
            new_balance = current_tokens - cost
            cursor.execute("UPDATE users SET tokens = ? WHERE id = 1", (new_balance,))
            cursor.execute("INSERT OR IGNORE INTO inventory (player_id, item_id) VALUES (1, ?)", (item_id,))
            conn.commit()
            return jsonify({"Result": 0, "Message": "Locker registry updated successfully!"})
            
    return jsonify({"Result": 1, "Message": "Insufficient balance allocation."})

# ==================== 💇 3. MIRROR CONFIGURATION, HAIR, & OUTFIT LOCKERS ====================

@app.route('/api/avatar/v2', methods=['GET'])
def retrieve_watch_mirror_avatar():
    """Loads your configured cosmetic models instantly when standing at the mirror."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT avatar_settings FROM users WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return row[0]
    return '{"Version":4,"SkinColor":1,"HairType":1,"OutfitType":1,"Equipment":[]}'

@app.route('/api/avatar/v2/saved', methods=['POST'])
def save_mirror_customizations():
    """Triggered instantly when updating hair, faces, skin, or clothes styles."""
    data = request.json or {}
    payload_string = json.dumps(data)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET avatar_settings = ? WHERE id = 1", (payload_string,))
        conn.commit()
    return jsonify({"Result": 0})

@app.route('/api/playeritems/v1/get', methods=['GET'])
def compile_locker_items():
    """Merges base structural patterns with items purchased from the storefront."""
    unlocked_locker = []
    # Generates baseline clothing selections automatically
    for item in range(1, 400):
        unlocked_locker.append({"ItemType": 1, "ItemId": item, "Count": 1, "IsEquipped": False})
        
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT item_id FROM inventory WHERE player_id = 1")
        purchased_rows = cursor.fetchall()
        for row in purchased_rows:
            unlocked_locker.append({"ItemType": 1, "ItemId": row[0], "Count": 1, "IsEquipped": True})
            
    return jsonify(unlocked_locker)

# ==================== 🌐 4. ROOM ROUTING ENGINE ====================

@app.route('/api/matchmaking/v4/joinroom', methods=['POST'])
def select_watch_room():
    """Allows movement between maps (Orientation, Paintball, Lounge) via the Watch UI."""
    data = request.json or {}
    room_title = data.get("RoomName", "Orientation")
    room_hash = str(hash(room_title) & 0xffffffff)
    
    if room_hash not in live_lobbies:
        live_lobbies[room_hash] = {"Name": room_title, "Players": []}
        
    return jsonify({
        "Result": 0,
        "Room": {
            "RoomId": int(room_hash),
            "Name": room_title,
            "MaxPlayers": 40,
            "Players": live_lobbies[room_hash]["Players"]
        },
        "PhotonRegion": "USW",
        "PhotonServerAddress": "127.0.0.1:5055",  # Pointing straight to a local Photon loop
        "CustomRoomId": str(uuid.uuid4())
    })

# ==================== 💬 5. REAL-TIME SIGNAL SYNCHRONIZATION ====================

@sock.route('/hub/v1/notification')
def monitor_watch_socket(ws):
    try:
        ws.receive()
        online_sockets[1] = ws
        while True:
            packet = ws.receive()
            if packet is None: break
            ws.send('{"Id":1,"Msg":"PingResponseOK"}')
    except Exception: pass
    finally: online_sockets.pop(1, None)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
