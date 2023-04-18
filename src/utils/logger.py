import logging
import os

logs_path = "./logs"


def get_logger(
    name: str,
    level: int = logging.DEBUG,
    mode: str = "w",
    formatter_string: str = "[%(asctime)s] %(levelname)s [%(pathname)s:%(lineno)d]: %(message)s"
    ) -> logging.Logger:
    """
    Creates a proper logging.Logger object with options from args

    Args:
        name (str): path and name of the file to log in. Use __file__ variable
        level (str, optional): level of messages to log (ascending order: DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to "DEBUG".
        mode (str, optional): writing mode of log file. Defaults to "a".
        formatter_string (str, optional): how to format logging string. Defaults to "[%(asctime)s] %(levelname)s [%(pathname)s:%(lineno)d]: %(message)s".

    Returns:
        logging.Logger: logging.Logger object
    """
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)
    if not os.path.exists(f"{logs_path}\\{os.path.splitext(os.path.split(name)[-1])[0]}.log"):
        with open(f"{logs_path}\\{os.path.splitext(os.path.split(name)[-1])[0]}.log", "w", encoding="utf-8"):
            pass

    logger = logging.getLogger(name)
    logger.setLevel(level)

    ch = logging.FileHandler(f"{logs_path}\\{os.path.splitext(os.path.split(name)[-1])[0]}.log", mode, encoding = "utf-8")
    ch.setLevel(level)

    formatter = logging.Formatter(formatter_string)
    ch.setFormatter(formatter)

    for handler in logger.handlers:
        logger.removeHandler(handler)
    logger.addHandler(ch)

    return logger
