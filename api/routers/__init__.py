from api.routers.engine_routers import routers_factory as engine_routers_factory
from api.routers.models_routers import routers_factory as models_routers_factory
from engine import Engine

__all__ = [
    'routers_factory',
]


def routers_factory(engine: Engine):
    return [
        engine_routers_factory(engine=engine),
        models_routers_factory(engine=engine),
    ]
