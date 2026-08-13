import sqlite3
import json
import uuid
from flask import Flask, jsonify, request
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)
DB_FILE = "database.db"

# ==============================================================================
# 🗄️ 1. AUTOMATED UNIFIED DATABASE SCHEMA (2018-2021)
# ==============================================================================

def init_unified_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                xp INTEGER DEFAULT 1200000,
                level INTEGER DEFAULT 50,
                tokens INTEGER DEFAULT 999999,
                avatar_settings TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                player_id INTEGER,
                item_id INTEGER,
                item_type INTEGER DEFAULT 1,
                PRIMARY KEY (player_id, item_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_worlds (
                world_id TEXT PRIMARY KEY,
                world_name TEXT,
                world_data TEXT
            )
        """)

        default_avatar = (
            '{"Version":5,"SkinColor":2,"HairType":3,'
            '"OutfitType":12,"Equipment":[],'
            '"FaceFeatures":{"Mouth":1,"Eyes":1,"Ears":1}}'
        )

        cursor.execute("""
            INSERT OR IGNORE INTO users
            (id, username, display_name, avatar_settings)
            VALUES (1, 'RecRoomAdmin', 'RecRoom Admin', ?)
        """, (default_avatar,))

        conn.commit()


init_unified_db()

online_sockets = {}
live_lobbies = {}

# ==============================================================================
# ⌚ 2. VERSIONLESS CONFIGURATION & LOGIN HANDSHAKES
# ==============================================================================

@app.route("/api/config/v2", methods=["GET"])
def pull_watch_features():
    print(
        f"[CONFIG] Client connected. Agent string: "
        f"{request.headers.get('User-Agent')}"
    )

    return jsonify({
        "App.MinVersion": "0",
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


@app.route("/api/v1/login", methods=["POST"])
def gatekeeper_login():
    print("[LOGIN] Processing startup login handshake...")

    return jsonify({
        "Token": "dev_unified_localhost_session_secret_token_unlocked",
        "PlayerId": 1,
        "ScreenName": "RecRoomAdmin",
        "Status": 0
    })


@app.route("/api/players/v1/<int:player_id>", methods=["GET"])
@app.route("/api/accounts/v1/<int:player_id>", methods=["GET"])
def view_watch_profile(player_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT username, display_name, xp, level
            FROM users
            WHERE id = ?
            """,
            (player_id,)
        )

        row = cursor.fetchone()

        if row:
            return jsonify({
                "Id": player_id,
                "AccountId": player_id,
                "ScreenName": row[0],
                "Username": row[0],
                "DisplayName": row[1],
                "RegistrationStatus": 2,
                "Level": row[3],
                "XP": row[2]
            })

    return jsonify({
        "Id": 1,
        "AccountId": 1,
        "ScreenName": "Player",
        "Username": "Player",
        "DisplayName": "Player",
        "RegistrationStatus": 2,
        "Level": 1,
        "XP": 0
    })


# ==============================================================================
# 💰 3. MULTI-VERSION ECONOMY & WATCH STOREFRONT
# ==============================================================================

@app.route("/api/currency/v1/wallet", methods=["GET"])
def output_watch_wallet():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT tokens FROM users WHERE id = 1"
        )

        row = cursor.fetchone()
        tokens = row[0] if row else 999999

    return jsonify([
        {
            "CurrencyType": 0,
            "Balance": tokens
        }
    ])


@app.route("/api/storefront/v3/giftpackages", methods=["GET"])
@app.route("/api/storefront/v4/packages", methods=["GET"])
def pull_storefront_catalog():
    print(
        "[STORE] Watch storefront clicked. "
        "Populating dynamic catalog items..."
    )

    mock_catalog = []

    for i in range(1, 600):
        mock_catalog.append({
            "PackageId": i,
            "AvatarItemId": i,
            "ItemType": 1,
            "Cost": 100,
            "Name": f"Legacy Cosmetic #{i}",
            "Description":
                "Purchased from your universal local host emulator storefront."
        })

    return jsonify(mock_catalog)


@app.route("/api/storefront/v3/buy", methods=["POST"])
@app.route("/api/storefront/v4/buy", methods=["POST"])
def execute_watch_purchase():
    data = request.json or {}

    item_id = data.get(
        "AvatarItemId",
        data.get("PackageId", 1)
    )

    cost = data.get("Cost", 100)

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT tokens FROM users WHERE id = 1"
        )

        row = cursor.fetchone()
        current_tokens = row[0] if row else 0

        if current_tokens >= cost:
            new_balance = current_tokens - cost

            cursor.execute(
                "UPDATE users SET tokens = ? WHERE id = 1",
                (new_balance,)
            )

            cursor.execute(
                """
                INSERT OR IGNORE INTO inventory
                (player_id, item_id)
                VALUES (1, ?)
                """,
                (item_id,)
            )

            conn.commit()

            return jsonify({
                "Result": 0,
                "Message":
                    "Locker inventory item row written successfully."
            })

    return jsonify({
        "Result": 1,
        "Message": "Insufficient tokens."
    })


# ==============================================================================
# 💇 4. CLOTHING LOCKER & UNIVERSAL AVATAR STRUCTS
# ==============================================================================

@app.route("/api/avatar/v2", methods=["GET"])
@app.route("/api/avatar/v3", methods=["GET"])
def retrieve_watch_mirror_avatar():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT avatar_settings FROM users WHERE id = 1"
        )

        row = cursor.fetchone()

        if row:
            return row[0]

    return (
        '{"Version":5,"SkinColor":1,"HairType":1,'
        '"OutfitType":1,"Equipment":[]}'
    )


@app.route("/api/avatar/v2/saved", methods=["POST"])
@app.route("/api/avatar/v3/saved", methods=["POST"])
def save_mirror_customizations():
    data = request.json or {}
    payload_string = json.dumps(data)

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET avatar_settings = ?
            WHERE id = 1
            """,
            (payload_string,)
        )

        conn.commit()

    print(
        "[MIRROR] Wardrobe look changes safely written "
        "to the user profile."
    )

    return jsonify({
        "Result": 0
    })


@app.route("/api/playeritems/v1/get", methods=["GET"])
def compile_locker_items():
    unlocked_locker = []

    for item in range(1, 600):
        unlocked_locker.append({
            "ItemType": 1,
            "ItemId": item,
            "Count": 1,
            "IsEquipped": False
        })

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT item_id FROM inventory WHERE player_id = 1"
        )

        purchased_rows = cursor.fetchall()

        for row in purchased_rows:
            unlocked_locker.append({
                "ItemType": 1,
                "ItemId": row[0],
                "Count": 1,
                "IsEquipped": True
            })

    return jsonify(unlocked_locker)


# ==============================================================================
# 🌐 5. MAP INTERCONNECTIONS & MULTI-VERSION ROOM SYSTEM
# ==============================================================================

@app.route("/api/matchmaking/v4/joinroom", methods=["POST"])
@app.route("/api/matchmaking/v5/joinroom", methods=["POST"])
def select_watch_room():
    data = request.json or {}

    room_title = data.get(
        "RoomName",
        "Orientation"
    )

    room_hash = str(
        hash(room_title) & 0xffffffff
    )

    if room_hash not in live_lobbies:
        live_lobbies[room_hash] = {
            "Name": room_title,
            "Players": []
        }

    print(
        f"[ROOM-NAV] Routing player to map layout "
        f"target context: '{room_title}'"
    )

    return jsonify({
        "Result": 0,
        "Room": {
            "RoomId": int(room_hash),
            "Name": room_title,
            "MaxPlayers": 40,
            "Players": live_lobbies[room_hash]["Players"]
        },
        "PhotonRegion": "USW",
        "PhotonServerAddress": "127.0.0.1:5055",
        "CustomRoomId": str(uuid.uuid4())
    })


@app.route("/api/rooms/v2/save", methods=["POST"])
def serialize_makerpen_world():
    data = request.json or {}

    r_id = str(
        data.get("RoomId", "default_lobby")
    )

    r_name = data.get(
        "RoomName",
        "Custom Room"
    )

    r_blob = data.get(
        "Data",
        ""
    )

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO custom_worlds
            (world_id, world_name, world_data)
            VALUES (?, ?, ?)
            """,
            (r_id, r_name, r_blob)
        )

        conn.commit()

    print(
        f"[MAKERPEN] Saved blueprint instance safely: {r_name}"
    )

    return jsonify({
        "Result": 0,
        "Message": "World saved permanently!"
    })


@app.route("/api/rooms/v2/load", methods=["GET"])
def deserialize_makerpen_world():
    r_id = request.args.get(
        "roomId",
        "default_lobby"
    )

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT world_data
            FROM custom_worlds
            WHERE world_id = ?
            """,
            (r_id,)
        )

        row = cursor.fetchone()

        if row:
            return jsonify({
                "Data": row[0]
            })

    return jsonify({
        "Data":
            '{"Objects":[],"Variables":[],"CircuitsV2":[]}'
    })


# ==============================================================================
# 💬 6. WEBSOCKET REAL-TIME WATCH SIGNALS
# ==============================================================================

@sock.route("/hub/v1/notification")
def monitor_watch_socket(ws):
    try:
        ws.receive()

        online_sockets[1] = ws

        while True:
            packet = ws.receive()

            if packet is None:
                break

            ws.send(
                '{"Id":1,"Msg":"PingResponseOK"}'
            )

    except Exception:
        pass

    finally:
        online_sockets.pop(1, None)


# ==============================================================================
# 🚀 7. UNIVERSAL LOCALHOST RUNTIME ENGINE BINDING
# ==============================================================================

if __name__ == "__main__":
    print("----------------------------------------------------------------")
    print(" UNIFIED LOCAL SERVER ACTIVE")
    print(" http://127.0.0.1:20592")
    print("----------------------------------------------------------------")

    app.run(
        host="127.0.0.1",
        port=20592,
        debug=False
    )
