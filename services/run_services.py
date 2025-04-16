"""
Run both the main application and QuotestreamPY service concurrently
"""
import os
import sys
import time
import threading
import subprocess
import logging
import signal

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("runner")

# Process objects for the services
main_process = None
quotestream_process = None

# Flag to indicate if we should keep running
keep_running = True

def run_main_app():
    """Run the main application using gunicorn"""
    global main_process
    
    cmd = ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]
    
    try:
        logger.info(f"Starting main application: {' '.join(cmd)}")
        main_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor the output
        for line in main_process.stdout:
            print(f"[MAIN_APP] {line.strip()}")
            
        main_process.wait()
        logger.warning("Main application process exited")
    except Exception as e:
        logger.error(f"Error running main application: {e}")

def run_quotestream():
    """Run the QuotestreamPY service"""
    global quotestream_process
    
    cmd = [sys.executable, "quotestream_service.py"]
    
    try:
        logger.info(f"Starting QuotestreamPY service: {' '.join(cmd)}")
        quotestream_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor the output
        for line in quotestream_process.stdout:
            print(f"[QUOTESTREAM] {line.strip()}")
            
        quotestream_process.wait()
        logger.warning("QuotestreamPY service process exited")
    except Exception as e:
        logger.error(f"Error running QuotestreamPY service: {e}")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global keep_running, main_process, quotestream_process
    
    logger.info("Shutting down services...")
    keep_running = False
    
    # Terminate processes
    if quotestream_process:
        logger.info("Terminating QuotestreamPY service...")
        quotestream_process.terminate()
        
    if main_process:
        logger.info("Terminating main application...")
        main_process.terminate()
    
    # Give processes time to terminate gracefully
    time.sleep(2)
    
    # Force kill if still running
    if quotestream_process and quotestream_process.poll() is None:
        logger.warning("Force killing QuotestreamPY service...")
        quotestream_process.kill()
        
    if main_process and main_process.poll() is None:
        logger.warning("Force killing main application...")
        main_process.kill()
    
    logger.info("All services stopped")
    sys.exit(0)

def main():
    """Run both services"""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start QuotestreamPY service in a separate thread
    quotestream_thread = threading.Thread(target=run_quotestream)
    quotestream_thread.daemon = True
    quotestream_thread.start()
    
    # Give QuotestreamPY service some time to start
    time.sleep(2)
    
    # Start main application in the main thread
    run_main_app()
    
    # If we get here, the main application has exited
    # We should stop the QuotestreamPY service as well
    signal_handler(None, None)

if __name__ == "__main__":
    main()