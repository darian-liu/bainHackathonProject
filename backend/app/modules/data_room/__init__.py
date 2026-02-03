from app.modules.base import ModuleBase
from app.api.routes.data_room import router
from fastapi import APIRouter


class DataRoomModule(ModuleBase):
    @property
    def id(self) -> str:
        return "data-room"
    
    @property
    def name(self) -> str:
        return "Data Room"
    
    @property
    def router(self) -> APIRouter:
        return router
