from abc import ABC, abstractmethod

class HardwareAdapter(ABC):
    @abstractmethod
    async def initialize(self): ...
    
    @abstractmethod
    async def read_distance_cm(self) -> float: ...
    
    @abstractmethod
    async def cleanup(self): ...
    
    @abstractmethod
    def is_vehicle_detected(self, distance_cm: float, threshold_cm: float) -> bool: ...
