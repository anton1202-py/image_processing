from base_module.services.rabbit import RabbitService
from config import config


def rabbit() -> RabbitService:
    """."""
    return RabbitService(config.rabbit)
