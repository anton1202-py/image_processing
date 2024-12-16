import flask

import routers
from injectors.connections import pg


def setup_app():
    current = flask.Flask(__name__)
    pg.setup(current)

    return current


app = setup_app()

app.register_blueprint(routers.task_router)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
