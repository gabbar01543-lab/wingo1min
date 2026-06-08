import aiohttp
import asyncio
import sqlite3
import os
import sys
from datetime import datetime

# --- CONFIGURATION ---
if os.path.exists('/var/lib/data'):
    BASE_DIR = '/var/lib/data'
elif os.path.exists('/data'):
    BASE_DIR = '/data'
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, 'my_history_storage.db')
EXTERNAL_API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
MAX_RECORDS = 2000

# --- DATABASE INIT ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS history (
                        issue TEXT PRIMARY KEY, 
                        number INTEGER, 
                        color TEXT, 
                        created_at TIMESTAMP
                    )''')
        conn.commit()

# --- FETCHING LOGIC ---
async def fetch_external_page(session, page_no):
    try:
        params = { "pageSize": 20, "pageNo": page_no, "typeId": 1 }
        async with session.get(EXTERNAL_API_URL, params=params, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                return data.get('data', {}).get('list', [])
    except Exception as e:
        print(f"[MR PERFECT MINER] Error fetching page {page_no}: {e}")
    return []

async def save_to_db(items):
    if not items: return
    new_count = 0
    
    with sqlite3.connect(DB_PATH) as conn:
        for item in items:
            try:
                iss = str(item.get('issueNumber'))
                num = int(item.get('number'))
                col = item.get('color', '')
                
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO history (issue, number, color, created_at) VALUES (?, ?, ?, ?)",
                    (iss, num, col, datetime.now())
                )
                if cursor.rowcount > 0: 
                    new_count += 1
            except Exception:
                pass
        
        if new_count > 0:
            try:
                cursor = conn.execute(f'''
                    DELETE FROM history 
                    WHERE issue NOT IN (
                        SELECT issue FROM history 
                        ORDER BY issue DESC 
                        LIMIT {MAX_RECORDS}
                    )
                ''')
                deleted = cursor.rowcount
                if deleted > 0:
                    print(f"[CLEANUP] Pruned {deleted} old records. Hard limit maintained at {MAX_RECORDS}.")
            except Exception as e:
                print(f"[CLEANUP ERROR] {e}")

        conn.commit()
    
    if new_count > 0:
        print(f"[MR PERFECT MINER] Saved {new_count} new records.")

# --- MAIN LOOP ---
async def start_recording_engine():
    print(">>> MR PERFECT DATA MINER INITIALIZED <<<")
    init_db()
    
    async with aiohttp.ClientSession() as session:
        print(">>> STARTING FAST BACKFILL...")
        for p in range(1, 51): 
            items = await fetch_external_page(session, p)
            await save_to_db(items)
            await asyncio.sleep(0.5) 
        print(">>> BACKFILL COMPLETE. SWITCHING TO LIVE SYNC. <<<")

        while True:
            items = await fetch_external_page(session, 1)
            await save_to_db(items)
            await asyncio.sleep(5)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(start_recording_engine())
