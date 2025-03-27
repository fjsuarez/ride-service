from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Literal
from enum import Enum
from uuid import uuid4

class Location(BaseModel):
    address: str | None = None
    latitude: float
    longitude: float

class RideRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class RiderDetail(BaseModel):
    """Details of a rider in a ride"""
    dropoffLocation: Location
    pickupLocation: Location
    requestId: str
    rideStatus: RideRequestStatus

class RideDistance(BaseModel):
    distance: float
    entry_point: Location | None = None
    entry_polyline: str | None = None
    exit_point: Location | None = None
    exit_polyline: str | None = None
    ride_id: str

class Ride(BaseModel):
    """A ride offered by a driver"""
    availableSeats: int
    createdAt: datetime = Field(default_factory=datetime.now)
    driverId: str
    daysOfWeek: List[str] | None = None
    endLocation: Location
    endTime: datetime
    ridePolyline: str | None = None
    rideId: str
    riders: Dict[str, RiderDetail] | None = None
    startLocation: Location
    startTime: datetime
    status: Literal["active", "cancelled", "completed"] = "active"
    totalSeats: int
    updatedAt: datetime = Field(default_factory=datetime.now)

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }

class Commute(BaseModel):
    """User's regular commute pattern"""
    commuteId: str = Field(default_factory=lambda: f"commute_{uuid4().hex}")
    createdAt: datetime = Field(default_factory=datetime.now)
    daysOfWeek: List[str]
    endLocation: Location
    preferredEndTime: datetime
    preferredStartTime: datetime
    startLocation: Location
    updatedAt: datetime = Field(default_factory=datetime.now)
    userId: str
    ride_distances: List[RideDistance] | None = None
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }

class RideRequest(BaseModel):
    """Request from a rider to join a ride"""
    createdAt: datetime = Field(default_factory=datetime.now)
    driverId: str
    dropoffLocation: Location
    pickupLocation: Location
    requestId: str = Field(default_factory=lambda: f"req_{uuid4().hex}")
    rideId: str
    riderId: str
    status: RideRequestStatus = RideRequestStatus.PENDING
    updatedAt: datetime = Field(default_factory=datetime.now)