"""."""

import os
import sys


def run_mule():
    from injectors import services

    services.tasks_mule().run()


if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    from injectors import connections

    connections.pg.init_db()
    run_mule()
