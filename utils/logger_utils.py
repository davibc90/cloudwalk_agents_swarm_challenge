import logging

def setup_logger(name: str, level=logging.INFO):
    """
        Create and configure a logger instance with console output.

        ### Description
        This function sets up a Python `logging` logger with a console handler.  
        It applies a standard format for log messages and avoids adding duplicate handlers 
        if the logger is initialized multiple times.

        ### Parameters
        - **name** (*str*): The name of the logger, typically `__name__` of the module.
        - **level** (*int*, optional): The logging level (default: `logging.INFO`).

        ### Returns
        - **logging.Logger**: A configured logger instance.

        ### Log Format
        ```
        %(asctime)s - %(name)s - %(levelname)s - %(message)s
        ```
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Log formatting
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    if not logger.handlers:  
        logger.addHandler(console_handler)

    return logger
