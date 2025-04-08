import logging
from app.utils.logging_config import configure_logging

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: The name of the logger
        
    Returns:
        A configured logger
    """
    return logging.getLogger(name) 