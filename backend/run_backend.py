import multiprocessing
import uvicorn
import os
from main import app

if __name__ == '__main__':
    # This line is strictly required for PyInstaller to work on Windows
    multiprocessing.freeze_support()
    
    # Grab the port from Electron, or default to 8080
    port = int(os.environ.get("API_PORT", 8080))
    
    # Run the server directly
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")