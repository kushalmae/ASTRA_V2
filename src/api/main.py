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

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import config
from database.db_manager import DatabaseManager

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(project_root, config["db_path"])
log_path = os.path.join(project_root, "logs")

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_path, 'api.log'))
    ]
)   
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ASTRA V2 API",
    description="API for monitoring spacecraft metrics",
    version="2.0.0"
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to ASTRA V2 API",
        "version": "2.0.0",
        "endpoints": {
            "root": "/",
            "log_metric": "/log_metric",
            "get_metrics": "/metrics",
            "health": "/health"
        },
        "documentation": "/docs"
    }

write_queue = Queue()

# Get absolute path relative to project root
db_path = os.path.join(project_root, config["db_path"])
db_manager = DatabaseManager(db_path)
shutdown_event = threading.Event()

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
    limit: int = Query(20, ge=1, le=100, description="Number of records to return")
):
    try:
        logger.info(f"Retrieving metrics: SCID={scid}, Metric={metric}, Limit={limit}")
        metrics = db_manager.get_metrics(scid=scid, metric=metric, limit=limit)
        logger.info(f"Retrieved {len(metrics)} metrics")
        return metrics
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving metrics")

@app.get("/health")
def health():
    queue_size = write_queue.qsize()
    metrics_count = db_manager.get_metrics_count()
    logger.info(f"Health check - Queue size: {queue_size}, Total metrics: {metrics_count}")
    return {
        "status": "ok",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "queue_size": queue_size,
        "total_metrics": metrics_count
    }

def db_writer():
    logger.info("Database writer thread started")
    
    while not shutdown_event.is_set():
        try:
            data = write_queue.get(timeout=1)
            try:                             
                if db_manager.insert_metric(data):
                    logger.info(f"Successfully wrote metric to database: SCID={data['scid']}, Metric={data['metric']}, Value={data['value']}")
                else:
                    logger.error("Failed to write metric to database")
                    # Keep the item in queue for retry
                    write_queue.put(data)
                    
            except Exception as e:
                logger.error(f"Database write error: {e}")
                # Keep the item in queue for retry
                write_queue.put(data)
        except Empty:
            continue
        except Exception as e:
            logger.error(f"Unexpected error in db_writer: {e}")
    
    logger.info("Database writer thread stopped")

def shutdown():
    shutdown_event.set()
    logger.info("Shutting down writer thread...")

if __name__ == "__main__":
    atexit.register(shutdown)
    threading.Thread(target=db_writer, daemon=True).start()
    import uvicorn
    logger.info(f"Starting API server on port {config['api_port']}")
    uvicorn.run(app, host="127.0.0.1", port=config["api_port"])
