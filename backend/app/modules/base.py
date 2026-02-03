from abc import ABC, abstractmethod
from fastapi import APIRouter


class ModuleBase(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        ...
    
    @property
    @abstractmethod
    def router(self) -> APIRouter:
        ...
