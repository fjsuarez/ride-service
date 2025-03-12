from fastapi import APIRouter, HTTPException, Request
from typing import List
from models import Ride
from services.ride_service import get_all_rides, create_new_ride

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.get("/", response_model=List[Ride])
async def get_rides(request: Request):
    rides_ref = request.app.state.rides_ref
    if not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    try:
        return await get_all_rides(rides_ref)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving rides: {exc}")

@router.post("/", response_model=Ride)
async def create_ride(ride: Ride, request: Request):
    rides_ref = request.app.state.rides_ref
    if not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")

    try:
        return await create_new_ride(ride, rides_ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error creating ride: {exc}")