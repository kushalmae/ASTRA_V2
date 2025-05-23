from apscheduler.schedulers.background import BackgroundScheduler
import time
import logging
import matlab.engine
import requests
from config import config

logging.basicConfig(level=logging.INFO)
SCRIPTS = config["scripts"]

# Start MATLAB Engine
eng = matlab.engine.start_matlab()

def run_matlab_script(script_name):
    logging.info(f"Running {script_name}...")
    try:
        func_name = script_name.replace(".m", "")
        scid, timeStr, metric, value, threshold = eng.feval(func_name, nargout=5)

        payload = {
            "scid": scid,
            "time": timeStr,
            "metric": metric,
            "value": float(value),
            "threshold": float(threshold)
        }

        response = requests.post("http://localhost:5000/log_metric", json=payload)
        if response.status_code == 200:
            logging.info("Metric logged successfully.")
        else:
            logging.error(f"Failed to log metric: {response.text}")
    except Exception as e:
        logging.error(f"MATLAB Engine Error: {e}")

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    for script, interval in SCRIPTS.items():
        scheduler.add_job(run_matlab_script, 'interval', seconds=interval, args=[script], id=script)
    scheduler.start()
    logging.info("APScheduler started with MATLAB Engine. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Scheduler stopped.")
        eng.quit()
