from apscheduler.schedulers.background import BackgroundScheduler
import time
import logging
import matlab.engine
import requests
import json
import os
import sys

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import config

logging.basicConfig(level=logging.INFO)
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
                        logging.info(f"No breaches found for SCID {scid}")
                else:
                    logging.info(f"No breaches found for SCID {scid}")
                    
            except Exception as e:
                logging.error(f"Error processing SCID {scid}: {e}")
                
    except Exception as e:
        logging.error(f"MATLAB Engine Error: {e}")

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    for script_name, script_config in SCRIPTS.items():
        scheduler.add_job(run_matlab_script, 
                         'interval', 
                         seconds=script_config["interval"], 
                         args=[script_name], 
                         id=script_name)
    scheduler.start()
    logging.info("APScheduler started with MATLAB Engine. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Scheduler stopped.")
        eng.quit()
