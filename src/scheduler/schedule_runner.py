from apscheduler.schedulers.background import BackgroundScheduler
import time
import logging
import matlab.engine
import requests
import json
import os
import sys
import signal
import atexit

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import config

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
log_path = os.path.join(project_root, "logs")

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_path, 'schduler.log'))
    ]
)   
logger = logging.getLogger(__name__)

SCRIPTS = config["scripts"]
API_URL = config["api_url"]

# Start MATLAB Engine
eng = matlab.engine.start_matlab()

# Add MATLAB functions directory to MATLAB path
matlab_functions_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'metrics')
eng.addpath(matlab_functions_dir, nargout=0)
logging.info(f"Added MATLAB path: {matlab_functions_dir}")

def run_matlab_script(script_name):
    logging.info(f"Running {script_name}...")
    try:
        func_name = script_name.replace(".m", "")
        # Get script configuration
        script_config = SCRIPTS[script_name]
        
        # Run for each SCID in the script's configuration
        for scid, scid_config in script_config["scids"].items():
            try:
                # Call MATLAB function with SCID-specific parameters
                json_output = eng.feval(func_name, 
                                     scid, 
                                     scid_config["metric"], 
                                     scid_config["threshold"], 
                                     nargout=1)
                
                # Parse the JSON output
                if json_output:  # Check if there are any breaches
                    breaches = json.loads(json_output)
                    if isinstance(breaches, list) and breaches:  # Ensure it's a non-empty list
                        for breach in breaches:
                            payload = {
                                "scid": breach["scid"],
                                "time": breach["time"],
                                "metric": breach["metric"],
                                "value": float(breach["value"]),
                                "threshold": float(breach["threshold"])
                            }
                            
                            response = requests.post(f"{API_URL}/log_metric", json=payload)
                            if response.status_code == 200:
                                logging.info(f"Metric logged successfully for SCID {scid} in func_name {func_name}")
                                logging.info(f"Payload details: SCID={payload['scid']}, Time={payload['time']}, Metric={payload['metric']}, Value={payload['value']}, Threshold={payload['threshold']}")
                            else:
                                logging.error(f"Failed to log metric for SCID {scid}: {response.text}")
                    else:
                        logging.info(f"No breaches found for SCID {scid} in json_output, it's empty")
                else:
                    logging.info(f"No breaches found for SCID {scid}, json_output was not returened")
                    
            except Exception as e:
                logging.error(f"Error processing SCID {scid}: {e}")
                
    except Exception as e:
        logging.error(f"MATLAB Engine Error: {e}")

def cleanup():
    """Cleanup function to be called on exit"""
    logging.info("Starting cleanup...")
    try:
        # First pause the scheduler to prevent new jobs from starting
        if scheduler.running:
            scheduler.pause()
            logging.info("Scheduler paused.")
            
            # Wait for any running jobs to complete (with timeout)
            timeout = 10  # seconds
            start_time = time.time()
            while scheduler.get_jobs() and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            # Now shutdown the scheduler
            scheduler.shutdown(wait=True)
            logging.info("Scheduler stopped.")
        
        # Then stop the MATLAB engine
        try:
            eng.quit()
            logging.info("MATLAB engine stopped.")
        except Exception as e:
            logging.error(f"Error stopping MATLAB engine: {e}")
            
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")
    finally:
        logging.info("Cleanup completed.")

def signal_handler(signum, frame):
    """Handle termination signals"""
    logging.info(f"Received signal {signum}")
    cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # Register cleanup function
    atexit.register(cleanup)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    scheduler = BackgroundScheduler()
    
    # Validate and schedule jobs
    for script_name, script_config in SCRIPTS.items():
        try:
           
            scheduler.add_job(run_matlab_script, 
                            'interval', 
                            seconds=script_config["interval"], 
                            args=[script_name], 
                            id=script_name)
            logging.info(f"Scheduled job '{script_name}' to run every {script_config['interval']} seconds")
            logging.info(f"Job configuration for {script_name}:")
            for scid, scid_config in script_config["scids"].items():
                logging.info(f"  SCID {scid}:")
                logging.info(f"    Metric: {scid_config['metric']}")
                logging.info(f"    Threshold: {scid_config['threshold']}")
        except Exception as e:
            logging.error(f"Failed to schedule job {script_name}: {str(e)}")
            continue
    
    scheduler.start()
    logging.info("APScheduler started with MATLAB Engine. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Received shutdown signal...")
        cleanup()
