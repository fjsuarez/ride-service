from fastapi import APIRouter, HTTPException, Request
from typing import List
from models import RideRequest, RideRequestStatus
from services.request_service import (
    create_ride_request, handle_ride_request,
    get_ride_requests_by_rider, get_ride_requests_by_driver, get_ride_request_by_id
)

router = APIRouter()

@router.get("/requests/rider/{rider_id}", response_model=List[RideRequest])
async def get_rider_requests(rider_id: str, request: Request):
    requests_ref = request.app.state.requests_ref
    if not requests_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id or user_id != rider_id:
        raise HTTPException(status_code=403, detail="Unauthorized to view these requests")
    
    try:
        return await get_ride_requests_by_rider(rider_id, requests_ref)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving requests: {exc}")

@router.get("/requests/driver/{driver_id}", response_model=List[RideRequest])
async def get_driver_requests(driver_id: str, request: Request):
    requests_ref = request.app.state.requests_ref
    if not requests_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id or user_id != driver_id:
        raise HTTPException(status_code=403, detail="Unauthorized to view these requests")
    
    try:
        return await get_ride_requests_by_driver(driver_id, requests_ref)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving requests: {exc}")

@router.get("/requests/{request_id}", response_model=RideRequest)
async def get_request(request_id: str, request: Request):
    requests_ref = request.app.state.requests_ref
    if not requests_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID")
    
    try:
        ride_request = await get_ride_request_by_id(request_id, requests_ref)
        if not ride_request:
            raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
        
        # Verify user has permission to view this request
        if user_id != ride_request.riderId and user_id != ride_request.driverId:
            raise HTTPException(status_code=403, detail="Unauthorized to view this request")
            
        return ride_request
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving request: {exc}")

@router.post("/requests", response_model=RideRequest)
async def request_ride(request_data: RideRequest, request: Request):
    rides_ref = request.app.state.rides_ref
    requests_ref = request.app.state.requests_ref
    if not rides_ref or not requests_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id or user_id != request_data.riderId:
        raise HTTPException(status_code=403, detail="You can only request rides for yourself")
    
    try:
        return await create_ride_request(request_data, rides_ref, requests_ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error creating ride request: {exc}")

@router.put("/requests/{request_id}/approve")
async def approve_request(request_id: str, request: Request):
    rides_ref = request.app.state.rides_ref
    requests_ref = request.app.state.requests_ref
    if not rides_ref or not requests_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID")
    
    try:
        return await handle_ride_request(request_id, user_id, RideRequestStatus.APPROVED, rides_ref, requests_ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error approving request: {exc}")

@router.put("/requests/{request_id}/reject")
async def reject_request(request_id: str, request: Request):
    rides_ref = request.app.state.rides_ref
    requests_ref = request.app.state.requests_ref
    if not rides_ref or not requests_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID")
    
    try:
        return await handle_ride_request(request_id, user_id, RideRequestStatus.REJECTED, rides_ref, requests_ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error rejecting request: {exc}")
