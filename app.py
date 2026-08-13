```python
import sqlite3
import json
import uuid
from flask import Flask, jsonify, request
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)
DB_FILE = "database.db"

# ==============================================================================
# 🗄️ 1. AUTOMATED SQLITE STORAGE INITIALIZATION
# ==============================================================================
def init_complete_db():
    """Builds the local database structures required to save profiles and items."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # User Profiles (XP, Levels, Tokens, Avatar Styles)
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

        # Purchased Closet Inventory (Locker)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                player_id INTEGER,
                item_id INTEGER,
                item_type INTEGER DEFAULT 1,
                PRIMARY KEY (player_id, item_id)
            )
        ''')

        # Maker Pen Custom Saved Worlds
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_worlds (
                world_id TEXT PRIMARY KEY,
                world_name TEXT,
                world_data TEXT
            )
        ''')

        # Populate Default Unlocked Admin Account Row
        default_avatar = '{"Version":4,"SkinColor":2,"HairType":3,"OutfitType":12,"Equipment":[]}'
        cursor.execute('''
            INSERT OR IGNORE INTO users (id, username, display_name, avatar_settings)
            VALUES (1, 'RecRoomAdmin', 'RecRoom Admin', ?)
        ''', (default_avatar,))
        conn.commit()

init_complete_db()

# RAM pools for active connection management
online_sockets = {}
live_lobbies = {}

# ==============================================================================
# ⌚ 2. MASTER WATCH INTERFACE & CONFIGURATION HANDSHAKES
# ==============================================================================

@app.route('/api/config/v2', methods=['GET'])
def pull_watch_features():
    """Forces the in-game Watch Menu interfaces, store tabs, and sandbox to unlock."""
    print("[CONFIG] Game client requested config profile. Sending unlock states...")
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
    """Auto-authenticates the local client profile session immediately upon launch."""
    print("[LOGIN] Authentication requested. Granting access to player account #1...")
    return jsonify({
        "Token": "secure_unlocked_localhost_session_secret_token",
        "PlayerId": 1,
        "ScreenName": "RecRoomAdmin",
        "Status": 0
    })

@app.route('/api/players/v1/<int:player_id>', methods=['GET'])
def view_watch_profile(player_id):
    """Pulls administrative level statistics to display inside your Watch HUD panel."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, display_name, xp, level FROM users WHERE id = ?", (player_id,))
        row = cursor.fetchone()
        if row:
            return jsonify({
                "Id": player_id,
                "ScreenName": row[0],
                "Username": row[0],
                "DisplayName": row[1],
                "RegistrationStatus": 2,
                "Level": row[3],
                "XP": row[2]
            })
    return jsonify({"Id": 1, "ScreenName": "Guest", "Username": "Guest", "DisplayName": "Guest", "RegistrationStatus": 2, "Level": 1, "XP": 0})

# ==============================================================================
# 💰 3. TOKENS, ECONOMY ENGINE, & WATCH STOREFRONT
# ==============================================================================

@app.route('/api/currency/v1/wallet', methods=['GET'])
def output_watch_wallet():
    """Feeds dynamic token balance loops straight onto the Watch display."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tokens FROM users WHERE id = 1")
        row = cursor.fetchone()
        tokens = row[0] if row else 999999
    return jsonify([{"CurrencyType": 0, "Balance": tokens}])

@app.route('/api/storefront/v3/giftpackages', methods=['GET'])
def pull_storefront_catalog():
    """Populates every selectable item listing inside your Watch item shop interface."""
    mock_catalog = []
    # Generates 500 working clothing/hair choices to select and buy in the UI
    for i in range(1, 500):
        mock_catalog.append({
            "PackageId": i,
            "AvatarItemId": i,
            "ItemType": 1,
            "Cost": 250,  # Each item costs 250 Tokens
            "Name": f"Cosmetic Gear Pro #{i}",
            "Description": "Purchased from your custom local host emulator storefront."
        })
    return jsonify(mock_catalog)

@app.route('/api/storefront/v3/buy', methods=['POST'])
def execute_watch_purchase():
    """Processes asset purchases from the watch, tracking balances in your database."""
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
            print(f"[STORE] Bought Item #{item_id}. Remaining balance: {new_balance} Tokens.")
            return jsonify({"Result": 0, "Message": "Locker registry updated successfully!"})

    return jsonify({"Result": 1, "Message": "Insufficient balance allocation."})

# ==============================================================================
# 💇 4. MIRROR CONFIGURATION, HAIR, & PERSONAL ATTENDANCE LOOKS
# ==============================================================================

@app.route('/api/avatar/v2', methods=['GET'])
def retrieve_watch_mirror_avatar():
    """Loads hair modifications and body selections instantly when standing at mirrors."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT avatar_settings FROM users WHERE id = 1")
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
    return '{"Version":4,"SkinColor":1,"HairType":1,"OutfitType":1,"Equipment":[]}'

@app.route('/api/avatar/v2/saved', methods=['POST'])
def save_mirror_customizations():
    """Triggered instantly when modifying hair, face shapes, or clothes in your mirror."""
    data = request.json or {}
    payload_string = json.dumps(data)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET avatar_settings = ? WHERE id = 1", (payload_string,))
        conn.commit()
    print("[MIRROR] Avatar customization layout modifications updated inside SQLite row.")
    return jsonify({"Result": 0})

@app.route('/api/playeritems/v1/get', methods=['GET'])
def compile_locker_items():
    """Merges baseline clothing files with items you purchase from the store."""
    unlocked_locker = []
    # Generates thousands of default wardrobe structures automatically
    for item in range(1, 400):
        unlocked_locker.append({"ItemType": 1, "ItemId": item, "Count": 1, "IsEquipped": False})

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT item_id FROM inventory WHERE player_id = 1")
        purchased_rows = cursor.fetchall()
        for row in purchased_rows:
            unlocked_locker.append({"ItemType": 1, "ItemId": row[0], "Count": 1, "IsEquipped": True})

    return jsonify(unlocked_locker)

# ==============================================================================
# 🌐 5. MAP INTERCONNECTIONS & MAKER PEN SAVE ARCHITECTURES
# ==============================================================================

@app.route('/api/matchmaking/v4/joinroom', methods=['POST'])
def select_watch_room():
    """Directs clients to load specific maps (Orientation, Paintball, Lounge) via the Watch UI."""
    data = request.json or {}
    room_title = data.get("RoomName", "Orientation")
    room_hash = str(hash(room_title) & 0xffffffff)

    if room_hash not in live_lobbies:
        live_lobbies[room_hash] = {"Name": room_title, "Players": []}

    print(f"[ROOM] Navigating map path layout to: {room_title}. Redirecting to local Photon link...")
    return jsonify({
        "Result": 0,
        "Room": {
            "RoomId": int(room_hash),
            "Name": room_title,
            "MaxPlayers": 40,
            "Players": live_lobbies[room_hash]["Players"]
        },
        "PhotonRegion": "USW",
        "PhotonServerAddress": "127.0.0.1:5055",  # Pointing to local Photon Controls layout loop
        "CustomRoomId": str(uuid.uuid4())
    })

@app.route('/api/rooms/v2/save', methods=['POST'])
def serialize_makerpen_world():
    """Saves custom world map data arrays made with your Maker Pen."""
    data = request.json or {}
    r_id = str(data.get("RoomId", "default_lobby"))
    r_name = data.get("RoomName", "Custom Room")
    r_blob = data.get("Data", "")

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO custom_worlds (world_id, world_name, world_data) VALUES (?, ?, ?)",
            (r_id, r_name, r_blob)
        )
        conn.commit()

    print(f"[MAKERPEN] Custom world room blueprint '{r_name}' written to your database database file successfully!")
    return jsonify({"Result": 0, "Message": "World saved permanently!"})

@app.route('/api/rooms/v2/load', methods=['GET'])
def deserialize_makerpen_world():
    """Loads previously saved custom rooms back into the game."""
    r_id = request.args.get("roomId", "default_lobby")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT world_data FROM custom_worlds WHERE world_id = ?", (r_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return jsonify({"Data": row[0]})
    return jsonify({"Data": '{"Objects":[],"Variables":[],"CircuitsV2":[]}'})

# ==============================================================================
# 💬 6. REAL-TIME INTER-CLIENT SIGNAL NOTIFICATION SYNC
# ==============================================================================

@sock.route('/hub/v1/notification')
def monitor_watch_socket(ws):
    """Handles continuous, real-time background connections for incoming server notifications."""
    try:
        ws.receive()
        online_sockets[1] = ws
        while True:
            packet = ws.receive()
            if packet is None:
                break
            ws.send('{"Id":1,"Msg":"PingResponseOK"}')
    except Exception:
        pass
    finally:
        online_sockets.pop(1, None)

# ==============================================================================
# 🚀 7. MACHINE INTERFACE EXECUTION BINDING
# ==============================================================================

if __name__ == '__main__':
    print("---------------------------------------------------------")
    print(" UNLOCKED EMULATOR SERVER ACTIVE ON http://localhost:20592")
    print("---------------------------------------------------------")
    app.run(host='127.0.0.1', port=20592, debug=False)
```

