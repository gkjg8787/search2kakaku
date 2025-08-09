from domain.models.pricelog import pricelog
from domain.models.notification import notification
from domain.models.activitylog import activitylog
from databases.sql import util as db_util


def main():
    db_util.create_db_and_tables()


if __name__ == "__main__":
    main()
