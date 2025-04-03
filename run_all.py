#!/usr/bin/env python
"""
Script to run all main modules in sequence
"""
import logging
import sys
import time
from importlib import import_module

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("run_all")


def run_module(module_name):
    """Run a specific module by importing it and calling its main function"""
    try:
        logger.info(f"Starting {module_name}...")
        start_time = time.time()

        # Import the module and run its main function
        module = import_module(module_name)
        module.main()

        elapsed = time.time() - start_time
        logger.info(f"Completed {module_name} in {elapsed:.2f} seconds")
    except Exception as e:
        logger.error(f"Error running {module_name}: {str(e)}")
        return False
    return True


def main():
    """Main function to run all scripts"""
    logger.info("Starting all modules")

    # List of modules to run (without .py extension)
    modules = ["main", "main1"]

    # Run each module in sequence
    results = []
    for module in modules:
        success = run_module(module)
        results.append((module, success))

    # Report results
    logger.info("Execution summary:")
    for module, success in results:
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"  {module}: {status}")


if __name__ == "__main__":
    main()
