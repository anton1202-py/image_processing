import flask
from flask import jsonify, request

from injectors.services import processing_injector

task_router = flask.Blueprint("tasks", __name__, url_prefix="/api/")


@task_router.post("/processing/<int:file_id>")
def task_create(file_id):
    ts = processing_injector()
    response = ts.create_task(file_id, request.get_json())
    return jsonify(response)


@task_router.get("/tasks")
def tasks_list():
    ts = processing_injector()
    response = ts.get_all()
    return jsonify(response)


@task_router.get("/tasks/<int:task_id>")
def tasks_status(task_id):
    ts = processing_injector()
    response = ts.get(task_id)
    return jsonify(response)
