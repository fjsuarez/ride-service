from models import Ride, RideRequestStatus
from datetime import datetime
from uuid import uuid4

async def get_all_rides(rides_ref):
    """Get all rides from Firestore with validation error handling"""
    rides = []    
    for doc in rides_ref.stream():
        try:
            ride_data = doc.to_dict()
            
            if 'availableSeats' in ride_data and 'totalSeats' not in ride_data:
                ride_data['totalSeats'] = ride_data['availableSeats']
            
            if 'riders' in ride_data and ride_data['riders']:
                for rider_id, rider_details in ride_data['riders'].items():
                    # Convert 'reserved' to 'approved'
                    if rider_details.get('rideStatus') == 'reserved':
                        ride_data['riders'][rider_id]['rideStatus'] = 'approved'
                    
                    if 'requestId' not in rider_details:
                        ride_data['riders'][rider_id]['requestId'] = f"req_{uuid4().hex}"
            
            ride_model = Ride.model_validate(ride_data)
            rides.append(ride_model.model_dump())
        except Exception as exc:
            print(f"Error parsing ride document {doc.id}: {exc}")
    
    return rides

async def get_ride_by_id(ride_id: str, rides_ref):
    """Get a ride by its ID"""
    ride_doc = rides_ref.document(ride_id).get()
    if not ride_doc.exists:
        return None
    
    try:
        ride_data = ride_doc.to_dict()
        return Ride.model_validate(ride_data)
    except Exception as exc:
        raise Exception(f"Error parsing ride document: {exc}")

async def create_new_ride(ride: Ride, rides_ref):
    """Create a new ride in Firestore"""
    ride_data = ride.model_dump()
    
    # Check if ride already exists
    ride_ref = rides_ref.document(ride.rideId)
    existing = ride_ref.get()
    
    if existing.exists:
        raise ValueError("Ride already exists")
    
    # Set total seats equal to available seats initially
    if ride.availableSeats is None:
        ride_data["availableSeats"] = ride_data["totalSeats"]
    
    # Initialize empty riders dictionary if not provided
    if ride_data.get("riders") is None:
        ride_data["riders"] = {}
    
    # Create new ride document
    try:
        ride_ref.set(ride_data)
        return ride
    except Exception as exc:
        raise Exception(f"Error creating ride document: {exc}")

async def update_ride(ride_id: str, updates: dict, rides_ref):
    """Update a ride in Firestore"""
    ride_ref = rides_ref.document(ride_id)
    ride_doc = ride_ref.get()
    
    if not ride_doc.exists:
        raise ValueError(f"Ride {ride_id} not found")
    
    updates["updatedAt"] = datetime.now()
    
    try:
        ride_ref.update(updates)
        updated_doc = ride_ref.get()
        return Ride.model_validate(updated_doc.to_dict())
    except Exception as exc:
        raise Exception(f"Error updating ride: {exc}")

async def cancel_ride(ride_id: str, driver_id: str, rides_ref, requests_ref):
    """Cancel a ride and update all associated requests"""
    # Verify ride exists and belongs to driver
    ride_doc = rides_ref.document(ride_id).get()
    if not ride_doc.exists:
        raise ValueError(f"Ride {ride_id} not found")
    
    ride_data = ride_doc.to_dict()
    if ride_data["driverId"] != driver_id:
        raise ValueError("You don't have permission to cancel this ride")
    
    # Update ride status to cancelled
    try:
        rides_ref.document(ride_id).update({
            "status": "cancelled",
            "updatedAt": datetime.now()
        })
        
        # Update all pending requests for this ride to cancelled
        pending_requests = requests_ref.where("rideId", "==", ride_id).where(
            "status", "==", RideRequestStatus.PENDING).stream()
        
        for req_doc in pending_requests:
            req_doc.reference.update({
                "status": RideRequestStatus.CANCELLED,
                "updatedAt": datetime.now()
            })
            
        return {"status": "success", "message": "Ride cancelled successfully"}
    except Exception as exc:
        raise Exception(f"Error cancelling ride: {exc}")

async def get_rides_by_driver(driver_id: str, rides_ref):
    """Get all rides for a specific driver"""
    try:
        rides_query = rides_ref.where("driverId", "==", driver_id).stream()
        rides = []
        
        for doc in rides_query:
            ride_data = doc.to_dict()
            ride = Ride.model_validate(ride_data)
            rides.append(ride.model_dump())
            
        return rides
    except Exception as exc:
        raise Exception(f"Error retrieving driver rides: {exc}")

async def get_rides_for_rider(rider_id: str, rides_ref):
    """Get all rides that a rider is part of"""
    try:
        # Need to filter in memory since Firestore doesn't support subcollection queries easily
        all_rides = await get_all_rides(rides_ref)
        rider_rides = []
        
        for ride in all_rides:
            if ride.get("riders") and rider_id in ride.get("riders"):
                rider_rides.append(ride)
        
        return rider_rides
    except Exception as exc:
        raise Exception(f"Error retrieving rider rides: {exc}")

async def get_available_rides(rider_id: str, commute, max_distance: float, rides_ref, commutes_ref):
    """Get available rides sorted by walking distance"""
    try:
        # Get all active rides with available seats
        active_rides = rides_ref.where("status", "==", "active").where(
            "availableSeats", ">", 0).stream()
        
        rides_with_distance = []
        
        for ride_doc in active_rides:
            ride_data = ride_doc.to_dict()
            
            # Calculate walking distance (placeholder - would be replaced with actual calculation)
            # For now, we'll just set a random distance for demonstration
            import random
            walking_distance = random.uniform(0.1, 5.0)  # km
            
            # Filter by maximum distance if provided
            if max_distance and walking_distance > max_distance:
                continue
            
            ride_data["walkingDistance"] = walking_distance
            rides_with_distance.append(ride_data)
        
        # Sort by walking distance
        rides_with_distance.sort(key=lambda x: x["walkingDistance"])
        
        return rides_with_distance
    except Exception as exc:
        raise Exception(f"Error retrieving available rides: {exc}")