from models import Ride, RideRequest, RideRequestStatus, RiderDetail
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
    if ride.totalSeats is None:
        ride_data["totalSeats"] = ride_data["availableSeats"]
    
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

async def create_ride_request(request: RideRequest, rides_ref, requests_ref):
    """Create a new ride request"""
    # Check if ride exists and has available seats
    ride_doc = rides_ref.document(request.rideId).get()
    if not ride_doc.exists:
        raise ValueError(f"Ride {request.rideId} not found")
    
    ride_data = ride_doc.to_dict()
    if ride_data["availableSeats"] <= 0:
        raise ValueError("No available seats on this ride")
    
    if ride_data["status"] != "active":
        raise ValueError("This ride is not active")
    
    # Check if rider already has a pending request for this ride
    existing_requests = requests_ref.where("riderId", "==", request.riderId).where(
        "status", "==", RideRequestStatus.PENDING).stream()
    
    for _ in existing_requests:
        raise ValueError("You already have a pending ride request")
    
    # Create the request
    request_data = request.model_dump()
    request_ref = requests_ref.document(request.requestId)
    
    try:
        request_ref.set(request_data)
        return request
    except Exception as exc:
        raise Exception(f"Error creating ride request: {exc}")

async def handle_ride_request(request_id: str, driver_id: str, status: RideRequestStatus, rides_ref, requests_ref):
    """Approve or reject a ride request"""
    # Get the request
    request_doc = requests_ref.document(request_id).get()
    if not request_doc.exists:
        raise ValueError(f"Request {request_id} not found")
    
    request_data = request_doc.to_dict()
    
    # Verify driver owns the ride
    if request_data["driverId"] != driver_id:
        raise ValueError("You don't have permission to handle this request")
    
    # Get the ride
    ride_doc = rides_ref.document(request_data["rideId"]).get()
    if not ride_doc.exists:
        raise ValueError(f"Ride {request_data['rideId']} not found")
    
    ride_data = ride_doc.to_dict()
    
    # If approving, check available seats
    if status == RideRequestStatus.APPROVED and ride_data["availableSeats"] <= 0:
        raise ValueError("No available seats left on this ride")
    
    # Update request status
    try:
        requests_ref.document(request_id).update({
            "status": status,
            "updatedAt": datetime.now()
        })
        
        # If approved, update the ride
        if status == RideRequestStatus.APPROVED:
            rider_id = request_data["riderId"]
            rider_detail = RiderDetail(
                pickupLocation=request_data["pickupLocation"],
                dropoffLocation=request_data["dropoffLocation"],
                rideStatus=RideRequestStatus.APPROVED,
                requestId=request_id
            )
            
            # Update ride with rider information and decrement available seats
            if not ride_data.get("riders"):
                ride_data["riders"] = {}
                
            ride_data["riders"][rider_id] = rider_detail.model_dump()
            ride_data["availableSeats"] -= 1
            ride_data["updatedAt"] = datetime.now()
            
            rides_ref.document(request_data["rideId"]).set(ride_data)
            
        return {"status": "success", "message": f"Request {status}"}
    except Exception as exc:
        raise Exception(f"Error handling ride request: {exc}")

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