from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Literal
from enum import Enum
from uuid import uuid4

class Location(BaseModel):
    latitude: float
    longitude: float
    address: str

class Commute(BaseModel):
    """User's regular commute pattern"""
    commuteId: str = Field(default_factory=lambda: f"commute_{uuid4().hex}")
    userId: str
    startLocation: Location
    endLocation: Location
    preferredStartTime: datetime
    preferredEndTime: datetime
    daysOfWeek: List[str]
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }

class RideRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class RideRequest(BaseModel):
    """Request from a rider to join a ride"""
    requestId: str = Field(default_factory=lambda: f"req_{uuid4().hex}")
    rideId: str
    riderId: str
    driverId: str
    status: RideRequestStatus = RideRequestStatus.PENDING
    pickupLocation: Location
    dropoffLocation: Location
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    walkingDistance: float = 0  # Calculated walking distance in meters

class RiderDetail(BaseModel):
    """Details of a rider in a ride"""
    pickupLocation: Location
    dropoffLocation: Location
    rideStatus: RideRequestStatus
    requestId: str

class Ride(BaseModel):
    """A ride offered by a driver"""
    rideId: str
    driverId: str
    startLocation: Location
    endLocation: Location
    startTime: datetime
    endTime: datetime
    daysOfWeek: List[str] | None = None
    availableSeats: int
    totalSeats: int
    status: Literal["active", "cancelled", "completed"] = "active"
    riders: Dict[str, RiderDetail] | None = None
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }