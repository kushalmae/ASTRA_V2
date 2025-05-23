from fastapi import FastAPI, Query
from pydantic import BaseModel
from queue import Queue, Empty
import threading
import logging
import atexit
from config import config
from database import get_db_connection, initialize_db

logging.basicConfig(level=logging.INFO)
app = FastAPI()
write_queue = Queue()
db_path = config["db_path"]
shutdown_event = threading.Event()

def get_connection():
    conn = get_db_connection(db_path)
    return conn

class Metric(BaseModel):
    scid: str
    time: str
    metric: str
    value: float
    threshold: float

@app.post("/log_metric")
async def log_metric(data: Metric):
    write_queue.put(data.dict())
    return {"status": "queued"}

@app.get("/metrics")
def get_metrics(metric: str = Query(None), limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    if metric:
        cursor.execute("SELECT scid, time, metric, value, threshold FROM metrics WHERE metric=? ORDER BY id DESC LIMIT ?", (metric, limit))
    else:
        cursor.execute("SELECT scid, time, metric, value, threshold FROM metrics ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{"scid": r[0], "time": r[1], "metric": r[2], "value": r[3], "threshold": r[4]} for r in rows]

@app.get("/health")
def health():
    return {"status": "ok"}

def db_writer():
    conn = get_db_connection(db_path)
    initialize_db(conn)
    cursor = conn.cursor()
    while not shutdown_event.is_set():
        try:
            data = write_queue.get(timeout=1)
            try:
                cursor.execute(
                    "INSERT INTO metrics (scid, time, metric, value, threshold) VALUES (?, ?, ?, ?, ?)",
                    (data['scid'], data['time'], data['metric'], data['value'], data['threshold'])
                )
                conn.commit()
            except Exception as e:
                logging.error(f"[DB Error] {e}")
        except Empty:
            continue
    conn.close()

def shutdown():
    shutdown_event.set()
    logging.info("Shutting down writer thread...")

if __name__ == "__main__":
    atexit.register(shutdown)
    threading.Thread(target=db_writer, daemon=True).start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config["api_port"])
