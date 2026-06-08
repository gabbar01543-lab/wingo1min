from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
import threading
import asyncio
import sys

# Import your background miner
import fetcher

app = Flask(__name__)
# THIS IS THE MAGIC LINE: It allows your HTML file to fetch data without CORS blocks
CORS(app) 

# --- CONFIGURATION ---
if os.path.exists('/var/lib/data'):
    BASE_DIR = '/var/lib/data'
elif os.path.exists('/data'):
    BASE_DIR = '/data'
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, 'my_history_storage.db')

# --- DATABASE SETUP ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- BACKGROUND WORKER ---
def start_background_recorder():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(fetcher.start_recording_engine())

if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    t = threading.Thread(target=start_background_recorder, daemon=True)
    t.start()
    print(">>> DATA RECORDER STARTED <<<")

# --- API ENDPOINT ---
@app.route('/api/get_history', methods=['GET'])
def get_history_api():
    try:
        try:
            page_no = int(request.args.get('pageNo', 1))
            page_size = int(request.args.get('pageSize', 20))
        except:
            page_no = 1
            page_size = 20

        offset = (page_no - 1) * page_size
        conn = get_db_connection()
        
        total_row = conn.execute("SELECT COUNT(*) FROM history").fetchone()
        total_count = total_row[0] if total_row else 0

        cursor = conn.execute(
            "SELECT issue, number, color FROM history ORDER BY issue DESC LIMIT ? OFFSET ?", 
            (page_size, offset)
        )
        rows = cursor.fetchall()
        conn.close()

        data_list = []
        for row in rows:
            data_list.append({
                "issueNumber": row['issue'],
                "number": str(row['number']),
                "color": row['color'],
                "premium": str(row['number']) 
            })

        return jsonify({
            "code": 0,
            "msg": "Success",
            "data": {
                "list": data_list,
                "pageNo": page_no,
                "pageSize": page_size,
                "totalPage": (total_count // page_size) + 1,
                "totalCount": total_count
            }
        })

    except Exception as e:
        return jsonify({"code": 500, "msg": f"Server Error: {str(e)}"})

@app.route('/')
def home():
    conn = get_db_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    except sqlite3.OperationalError:
        count = 0
    finally:
        conn.close()
        
    return f"""
    <body style="font-family:monospace; background:#111; color:#0f0; text-align:center; padding-top:50px;">
        <h1>MR PERFECT DATA WAREHOUSE</h1>
        <h2>RECORDS STORED: {count}</h2>
        <p>API ENDPOINT: <br> 
           <span style="background:#222; padding:5px;">/api/get_history</span>
        </p>
    </body>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
