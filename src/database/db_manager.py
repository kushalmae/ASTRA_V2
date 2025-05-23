import sqlite3
import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str):
        logger.info(f"Initializing DatabaseManager with path: {db_path}")
        self.db_path = db_path
        self._verify_db_directory()
        self._initialize_db()

    def _verify_db_directory(self):
        """Ensure the database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        logger.info(f"Verifying database directory: {db_dir}")
        if db_dir and not os.path.exists(db_dir):
            logger.info(f"Creating database directory: {db_dir}")
            os.makedirs(db_dir)
            logger.info(f"Created database directory: {db_dir}")
        else:
            logger.info(f"Database directory already exists: {db_dir}")

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection"""
        try:
            logger.info(f"Attempting to connect to database at: {self.db_path}")
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL;")
            logger.info("Successfully connected to database")
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise

    def _initialize_db(self):
        """Initialize the database with required tables"""
        try:
            logger.info("Starting database initialization")
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create metrics table
            logger.info("Creating metrics table if not exists")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scid TEXT NOT NULL,
                time TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # Create index for faster queries
            logger.info("Creating index if not exists")
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_scid_time 
            ON metrics(scid, time);
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
        finally:
            conn.close()

    def insert_metric(self, metric_data: Dict[str, Any]) -> bool:
        """Insert a metric into the database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO metrics (scid, time, metric, value, threshold)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    metric_data['scid'],
                    metric_data['time'],
                    metric_data['metric'],
                    metric_data['value'],
                    metric_data['threshold']
                )
            )
            conn.commit()
            
            # Verify insertion
            cursor.execute(
                """
                SELECT * FROM metrics 
                WHERE scid = ? AND time = ? AND metric = ?
                """,
                (metric_data['scid'], metric_data['time'], metric_data['metric'])
            )
            inserted = cursor.fetchone()
            
            if inserted:
                logger.info(f"Successfully inserted metric: {metric_data}")
                return True
            else:
                logger.error("Insertion verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Error inserting metric: {e}")
            return False
        finally:
            conn.close()

    def get_metrics(
        self,
        scid: Optional[str] = None,
        metric: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve metrics with optional filtering"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT scid, time, metric, value, threshold FROM metrics"
            params = []
            
            conditions = []
            if scid:
                conditions.append("scid = ?")
                params.append(scid)
            if metric:
                conditions.append("metric = ?")
                params.append(metric)
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            query += " ORDER BY time DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                {
                    "scid": r[0],
                    "time": r[1],
                    "metric": r[2],
                    "value": r[3],
                    "threshold": r[4]
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Error retrieving metrics: {e}")
            return []
        finally:
            conn.close()

    def get_metrics_count(self) -> int:
        """Get total number of metrics in database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metrics")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting metrics count: {e}")
            return 0
        finally:
            conn.close() 