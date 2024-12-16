from config import config
from injectors.pg import PgConnectionInj
from models import *

pg = PgConnectionInj(conf=config.pg)
