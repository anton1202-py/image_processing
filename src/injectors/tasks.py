from base_module.sevices.rabbit import RabbitService
from config import config


def rabbit() -> RabbitService:
    """."""
    return RabbitService(config.rabbit)
