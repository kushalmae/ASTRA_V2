# ASTRA V2

A system for monitoring and analyzing spacecraft metrics.

## Project Structure

```
ASTRA_V2/
├── config/                 # Configuration files
│   └── db_config.json     # Database and metric configurations
├── data/                  # Data storage
│   └── output/           # JSON output files
├── src/                  # Source code
│   ├── api/             # API related code
│   │   └── main.py      # FastAPI application
│   ├── metrics/         # Metric calculation scripts
│   │   ├── runMetric1.m # Temperature metric
│   │   └── runMetric2.m # Pressure metric
│   └── utils/           # Utility functions
│       ├── config.py    # Configuration loader
│       ├── database.py  # Database operations
│       ├── schedule_runner.py # Script scheduler
│       └── writeMetricToJson.m # JSON output handler
└── requirements.txt      # Python dependencies
```

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure metrics in `config/db_config.json`:
   - Set database path
   - Configure API port
   - Define metrics and their thresholds for each SCID

3. Run the API server:
   ```bash
   python src/api/main.py
   ```

## Features

- Real-time metric monitoring
- Configurable thresholds per SCID
- JSON output for metric breaches
- RESTful API for data access
- Scheduled metric calculations