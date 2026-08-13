import sqlite3
import json
import uuid
from flask import Flask, jsonify, request
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)
DB_FILE = "database.db"

# ==================== 🛠️ AUTOMATED COMPREHENSIVE DB SETUP ====================
def init_complete_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Master user profile tracking
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
        # Inventory locker table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                player_id INTEGER,
                item_id INTEGER,
                item_type INTEGER DEFAULT 1,
                PRIMARY KEY (player_id, item_id)
            )
        ''')
        # Save custom map creations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maps (
                map_id TEXT PRIMARY KEY,
                map_data TEXT
            )
        ''')
        
        # Populate initial unlocked developer account
        default_avatar = '{"Version":4,"SkinColor":2,"HairType":3,"OutfitType":12,"Equipment":[]}'
        cursor.execute('''
            INSERT OR IGNORE INTO users (id, username, display_name, avatar_settings)
            VALUES (1, 'LocalHostAdmin', 'Local Host Admin', ?)
        ''', (default_avatar,))
        conn.commit()

init_complete_db()

# RAM pools for live connection tracking
online_sockets = {}
live_lobbies = {}

# ==================== ⌚ 1. WATCH HANDSHAKE & CONFIG ENFORCEMENT ====================

@app.route('/api/config/v2', methods=['GET'])
def pull_watch_features():
    """Forces the Watch Menu UI elements to populate completely."""
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
    return jsonify({
        "Token": "master_unlocked_localhost_session_secret",
        "PlayerId": 1,
        "ScreenName": "LocalHostAdmin",
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

# ==================== 💰 2. TOKENS, STOREFRONT & WATCH PURCHASES ====================

@app.route('/api/currency/v1/wallet', methods=['GET'])
def output_watch_wallet():
    """Feeds token balances directly onto your Watch HUD display interface."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tokens FROM users WHERE id = 1")
        tokens = cursor.fetchone()[0]
    return jsonify([{"CurrencyType": 0, "Balance": tokens}])

@app.route('/api/storefront/v3/giftpackages', methods=['GET'])
def pull_storefront_catalog():
    """Populates items inside the Watch Store selection list menus."""
    mock_catalog = []
    # Loop generates functional visual inventory selections inside the item shop panels
    for i in range(1, 200):
        mock_catalog.append({
            "PackageId": i,
            "AvatarItemId": i,
            "ItemType": 1,
            "Cost": 100,  # Costs 100 Tokens to buy
            "Name": f"Custom Cosmetic Gear #{i}",
            "Description": "Unlocked via local host emulator engine server console."
        })
    return jsonify(mock_catalog)

@app.route('/api/storefront/v3/buy', methods=['POST'])
def execute_watch_purchase():
    """Processes real-time cosmetic acquisition transactions using tokens via your Watch."""
    data = request.json or {}
    item_id = data.get("AvatarItemId", 1)
    cost = data.get("Cost", 100)
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tokens FROM users WHERE id = 1")
        current_tokens = cursor.fetchone()[0]
        
        if current_tokens >= cost:
            new_balance = current_tokens - cost
            # Subtract tokens
            cursor.execute("UPDATE users SET tokens = ? WHERE id = 1", (new_balance,))
            # Grant item permanently to locker inventory
            cursor.execute("INSERT OR IGNORE INTO inventory (player_id, item_id) VALUES (1, ?)", (item_id,))
            conn.commit()
            return jsonify({"Result": 0, "Message": "Purchase successful! Locker updated."})
            
    return jsonify({"Result": 1, "Message": "Insufficient tokens for purchase."})

# ==================== 💇 3. HAIR, CLOTHING & OUTFIT LOCKER SAVES ====================

@app.route('/api/avatar/v2', methods=['GET'])
def retrieve_watch_mirror_avatar():
    """Loads hair, facial adjustments, and matching clothes when viewing mirrors."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT avatar_settings FROM users WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return row[0]
    return '{"Version":4,"SkinColor":1,"HairType":1,"OutfitType":1,"Equipment":[]}'

@app.route('/api/avatar/v2/saved', methods=['POST'])
def save_mirror_customizations():
    """Triggered instantly when modifying your hair, nose, or attire adjustments."""
    data = request.json or {}
    payload_string = json.dumps(data)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET avatar_settings = ? WHERE id = 1", (payload_string,))
        conn.commit()
    return jsonify({"Result": 0})

@app.route('/api/playeritems/v1/get', methods=['GET'])
def compile_locker_items():
    """Combines baseline default styles with items purchased from the shop."""
    unlocked_locker = []
    # Always include baseline choices (hair, simple shirts) automatically
    for item in range(1, 500):
        unlocked_locker.append({"ItemType": 1, "ItemId": item, "Count": 1, "IsEquipped": False})
        
    # Append custom items successfully bought using your local store wallet
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT item_id FROM inventory WHERE player_id = 1")
        purchased_rows = cursor.fetchall()
        for row in purchased_rows:
            unlocked_locker.append({"ItemType": 1, "ItemId": row[0], "Count": 1, "IsEquipped": True})
            
    return jsonify(unlocked_locker)

# ==================== 🌐 4. WATCH ROOM MULTIPLAYER SELECTION ====================

@app.route('/api/matchmaking/v4/joinroom', methods=['POST'])
def select_watch_room():
    """Allows players to jump between environments using the 'Play' screen."""
    data = request.json or {}
    room_title = data.get("RoomName", "Lounge")
    room_hash = str(hash(room_title) & 0xffffffff)
    
    if room_hash not in live_lobbies:
        live_lobbies[room_hash] = {"Name": room_title, "Players": [1]}
        
    return jsonify({
        "Result": 0,
        "Room": {
            "RoomId": int(room_hash),
            "Name": room_title,
            "MaxPlayers": 40,
            "Players": live_lobbies[room_hash]["Players"]
        },
        "PhotonRegion": "USW",
        "PhotonServerAddress": "127.0.0.1:5055",  # Relies on local running loop logic
        "CustomRoomId": str(uuid.uuid4())
    })

# ==================== 💬 5. REAL-TIME WATCH NOTIFICATION SYNC ====================

@sock.route('/hub/v1/notification')
def monitor_watch_socket(ws):
    try:
        handshake = ws.receive()
        online_sockets[1] = ws
        while True:
            packet = ws.receive()
            if packet is None: break
            ws.send('{"Id":1,"Msg":"PingResponseOK"}')
    except Exception: pass
    finally: online_sockets.pop(1, None)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
