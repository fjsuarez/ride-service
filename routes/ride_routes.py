from fastapi import APIRouter, HTTPException, Request, Query
from typing import List
from models import Ride, Commute
from services.ride_service import (
    get_all_rides, create_new_ride, get_ride_by_id, update_ride, cancel_ride,
    get_rides_by_driver, get_rides_for_rider, get_available_rides
)

router = APIRouter()

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
    print("creating ride...")
    rides_ref = request.app.state.rides_ref
    if not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID")
    
    # Ensure the driverId matches the logged-in user
    if ride.driverId != user_id:
        raise HTTPException(status_code=403, detail="You can only create rides for yourself")

    try:
        return await create_new_ride(ride, rides_ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error creating ride: {exc}")

@router.get("/available", response_model=List[Ride])
async def get_available_rides_endpoint(
    request: Request,
    max_distance: float = Query(5.0, description="Maximum walking distance in km")
):
    print(f"getting available rides with max_distance: {max_distance}")
    print(f"request params: {request._query_params}")
    rides_ref = request.app.state.rides_ref
    commutes_ref = request.app.state.commutes_ref
    if not rides_ref or not commutes_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID")
    
    try:
        # Get user's commute
        commute_docs = commutes_ref.where("userId", "==", user_id).stream()
        commute = None
        for doc in commute_docs:
            commute = Commute.model_validate(doc.to_dict())
            break
        
        if not commute:
            raise HTTPException(status_code=400, detail="No commute found, please create one first")
        
        return await get_available_rides(user_id, commute, max_distance, rides_ref, commutes_ref)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving available rides: {exc}")

@router.get("/{ride_id}", response_model=Ride)
async def get_ride(ride_id: str, request: Request):
    rides_ref = request.app.state.rides_ref
    if not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    try:
        ride = await get_ride_by_id(ride_id, rides_ref)
        if not ride:
            raise HTTPException(status_code=404, detail=f"Ride {ride_id} not found")
        return ride
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving ride: {exc}")

@router.put("/{ride_id}", response_model=Ride)
async def update_ride_endpoint(ride_id: str, ride_update: Ride, request: Request):
    rides_ref = request.app.state.rides_ref
    
    if not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id or user_id != ride_update.driverId:
        raise HTTPException(status_code=403, detail="You can only update your own rides")
    
    # Ensure IDs match
    if ride_id != ride_update.rideId:
        raise HTTPException(status_code=400, detail="Ride ID in path must match ride ID in body")
    
    try:
        return await update_ride(ride_id, ride_update.model_dump(), rides_ref)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error updating ride: {exc}")

@router.delete("/{ride_id}")
async def delete_ride(ride_id: str, request: Request):
    rides_ref = request.app.state.rides_ref
    requests_ref = request.app.state.requests_ref
    if not rides_ref or not requests_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID")
    
    try:
        result = await cancel_ride(ride_id, user_id, rides_ref, requests_ref)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error cancelling ride: {exc}")

@router.get("/driver/{driver_id}", response_model=List[Ride])
async def get_driver_rides(driver_id: str, request: Request):
    rides_ref = request.app.state.rides_ref
    if not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id or user_id != driver_id:
        raise HTTPException(status_code=403, detail="Unauthorized to view these rides")
    
    try:
        return await get_rides_by_driver(driver_id, rides_ref)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving rides: {exc}")

@router.get("/rider/{rider_id}", response_model=List[Ride])
async def get_rider_rides(rider_id: str, request: Request):
    rides_ref = request.app.state.rides_ref
    if not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id or user_id != rider_id:
        raise HTTPException(status_code=403, detail="Unauthorized to view these rides")
    
    try:
        return await get_rides_for_rider(rider_id, rides_ref)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving rides: {exc}")