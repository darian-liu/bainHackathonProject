from app.modules.base import ModuleBase
from app.modules.data_room import DataRoomModule

MODULES: list[ModuleBase] = [
    DataRoomModule(),
    # Add ExpertNetworkModule() here when ready
]


def get_module(module_id: str) -> ModuleBase | None:
    for module in MODULES:
        if module.id == module_id:
            return module
    return None
