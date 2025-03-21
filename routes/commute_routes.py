from fastapi import APIRouter, HTTPException, Request
from models import Commute
from services.commute_service import create_new_commute, update_commute
from datetime import datetime

router = APIRouter()

@router.get("/commutes/")
async def get_commutes(request: Request):
    commutes_ref = request.app.state.commutes_ref
    if not commutes_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID")
    
    try:
        commutes = []
        commute_docs = commutes_ref.where("userId", "==", user_id).stream()
        
        for doc in commute_docs:
            try:
                commute_data = doc.to_dict()
                # Handle datetime fields
                timestamp_fields = ["preferredStartTime", "preferredEndTime", "createdAt", "updatedAt"]
                for field in timestamp_fields:
                    if field in commute_data:
                        # Handle Firestore timestamps
                        value = commute_data[field]
                        if hasattr(value, 'seconds'):  # Firestore timestamp
                            commute_data[field] = datetime.fromtimestamp(value.seconds + (value.nanos / 1e9))
                
                # Validate and append the commute
                commute_obj = Commute.model_validate(commute_data)
                commutes.append(commute_obj)
            except Exception:
                # Skip documents that fail to process
                continue
        
        return commutes
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving commutes: {exc}")

@router.post("/commutes/", response_model=Commute)
async def create_commute(commute: Commute, request: Request):
    commutes_ref = request.app.state.commutes_ref
    rides_ref = request.app.state.rides_ref
    
    if not commutes_ref or not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id or user_id != commute.userId:
        raise HTTPException(status_code=403, detail="You can only create commutes for yourself")
    
    try:
        return await create_new_commute(commute, commutes_ref, rides_ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error creating commute: {exc}")

@router.put("/commutes/{commute_id}", response_model=Commute)
async def update_commute_endpoint(commute_id: str, commute_update: Commute, request: Request):
    commutes_ref = request.app.state.commutes_ref
    
    if not commutes_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id or user_id != commute_update.userId:
        raise HTTPException(status_code=403, detail="You can only update your own commutes")
    
    # Ensure IDs match
    if commute_id != commute_update.commuteId:
        raise HTTPException(status_code=400, detail="Commute ID in path must match commute ID in body")
    
    try:
        return await update_commute(commute_id, commute_update, commutes_ref)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error updating commute: {exc}")
