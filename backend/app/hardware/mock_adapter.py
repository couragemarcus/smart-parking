from .adapter import HardwareAdapter

class MockAdapter(HardwareAdapter):
    def __init__(self):
        self.distance = 100.0

    async def initialize(self):
        pass
        
    async def read_distance_cm(self) -> float:
        return self.distance
        
    async def cleanup(self):
        pass
        
    def is_vehicle_detected(self, distance_cm: float, threshold_cm: float) -> bool:
        return distance_cm < threshold_cm
