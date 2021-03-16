import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    filename='filename.txt')  # pass explicit filename here
# logger = logging.get_logger()  # get the root logger
logger = logging.getLogger()

logger.warning('This should go in the file.')
print logger.handlers   # you should have one FileHandler object