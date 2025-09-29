import logging

# Configuração básica de logging
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
    
    Example:
    ```
    2025-09-29 15:45:10,123 - my_module - INFO - This is a log message
    ```
    ### Example
    ```python
    logger = setup_logger(__name__)
    logger.info("Application started")
    ```
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Criar um manipulador de console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Formato do log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Adicionar os manipuladores ao logger
    if not logger.handlers:  # Evitar adicionar múltiplos handlers
        logger.addHandler(console_handler)

    return logger
