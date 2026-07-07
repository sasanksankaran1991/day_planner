from database.base import Base
from database.database import engine

from database.models import *


def initialize_database():
    Base.metadata.create_all(bind=engine)
