from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
from queue import Queue, Empty
import threading
import logging
import atexit
from datetime import datetime
from typing import List, Optional
import sys
import os
import sqlite3

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import config
from utils.database import get_db_connection, initialize_db

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api.log')
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ASTRA V2 API",
    description="API for monitoring spacecraft metrics",
    version="2.0.0"
)

write_queue = Queue()
db_path = config["db_path"]
shutdown_event = threading.Event()

def verify_database():
    """Verify database connection and table structure"""
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Check if metrics table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'")
        if not cursor.fetchone():
            logger.info("Metrics table not found, initializing database...")
            initialize_db(conn)
        
        # Check table structure
        cursor.execute("PRAGMA table_info(metrics)")
        columns = cursor.fetchall()
        logger.info(f"Database table structure: {columns}")
        
        conn.close()
        logger.info("Database verification completed successfully")
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        raise

def get_connection():
    try:
        conn = get_db_connection(db_path)
        logger.info(f"Database connection established to {db_path}")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

class Metric(BaseModel):
    scid: str = Field(..., description="Spacecraft ID")
    time: str = Field(..., description="Timestamp in ISO format")
    metric: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    threshold: float = Field(..., description="Threshold value")

    class Config:
        schema_extra = {
            "example": {
                "scid": "1",
                "time": "2024-02-20 10:00:00",
                "metric": "temperature",
                "value": 26.5,
                "threshold": 25.5
            }
        }

@app.post("/log_metric", response_model=dict)
async def log_metric(data: Metric):
    try:
        # Log incoming request
        logger.info(f"Received metric data: SCID={data.scid}, Metric={data.metric}, Value={data.value}, Threshold={data.threshold}")
        
        # Validate timestamp format
        datetime.strptime(data.time, "%Y-%m-%d %H:%M:%S")
        
        # Add to queue
        write_queue.put(data.dict())
        logger.info(f"Metric queued for processing: SCID={data.scid}, Metric={data.metric}")
        return {"status": "queued", "message": "Metric successfully queued for processing"}
    except ValueError:
        logger.error(f"Invalid timestamp format: {data.time}")
        raise HTTPException(status_code=400, detail="Invalid timestamp format. Use YYYY-MM-DD HH:MM:SS")
    except Exception as e:
        logger.error(f"Error queueing metric: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/metrics", response_model=List[Metric])
def get_metrics(
    metric: Optional[str] = Query(None, description="Filter by metric name"),
    scid: Optional[str] = Query(None, description="Filter by spacecraft ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return")
):
    try:
        logger.info(f"Retrieving metrics: SCID={scid}, Metric={metric}, Limit={limit}")
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT scid, time, metric, value, threshold FROM metrics"
        params = []
        
        # Build query based on filters
        conditions = []
        if metric:
            conditions.append("metric = ?")
            params.append(metric)
        if scid:
            conditions.append("scid = ?")
            params.append(scid)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY time DESC LIMIT ?"
        params.append(limit)
        
        logger.info(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Log the actual data retrieved
        logger.info(f"Retrieved {len(rows)} rows from database")
        for row in rows:
            logger.info(f"Row data: {row}")
        
        conn.close()
        
        metrics = [{"scid": r[0], "time": r[1], "metric": r[2], "value": r[3], "threshold": r[4]} for r in rows]
        return metrics
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving metrics")

@app.get("/health")
def health():
    queue_size = write_queue.qsize()
    logger.info(f"Health check - Queue size: {queue_size}")
    return {
        "status": "ok",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "queue_size": queue_size
    }

def db_writer():
    conn = get_db_connection(db_path)
    initialize_db(conn)
    cursor = conn.cursor()
    logger.info("Database writer thread started")
    
    while not shutdown_event.is_set():
        try:
            data = write_queue.get(timeout=1)
            try:
                logger.info(f"Writing metric to database: SCID={data['scid']}, Metric={data['metric']}, Value={data['value']}")
                
                # Verify the data before insertion
                logger.info(f"Inserting data: {data}")
                
                cursor.execute(
                    "INSERT INTO metrics (scid, time, metric, value, threshold) VALUES (?, ?, ?, ?, ?)",
                    (data['scid'], data['time'], data['metric'], data['value'], data['threshold'])
                )
                conn.commit()
                
                # Verify the insertion
                cursor.execute(
                    "SELECT * FROM metrics WHERE scid = ? AND time = ? AND metric = ?",
                    (data['scid'], data['time'], data['metric'])
                )
                inserted = cursor.fetchone()
                if inserted:
                    logger.info(f"Successfully verified insertion: {inserted}")
                else:
                    logger.error("Insertion verification failed - data not found in database")
                
            except Exception as e:
                logger.error(f"Database write error: {e}")
                # Keep the item in queue for retry
                write_queue.put(data)
        except Empty:
            continue
        except Exception as e:
            logger.error(f"Unexpected error in db_writer: {e}")
    
    conn.close()
    logger.info("Database writer thread stopped")

def shutdown():
    shutdown_event.set()
    logger.info("Shutting down writer thread...")

if __name__ == "__main__":
    # Verify database on startup
    verify_database()
    
    atexit.register(shutdown)
    threading.Thread(target=db_writer, daemon=True).start()
    import uvicorn
    logger.info(f"Starting API server on port {config['api_port']}")
    uvicorn.run(app, host="127.0.0.1", port=config["api_port"])
