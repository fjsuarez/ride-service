from models import RideRequest, RideRequestStatus, RiderDetail
from datetime import datetime

async def get_ride_requests_by_rider(rider_id: str, requests_ref):
    """Get all ride requests created by a specific rider"""
    try:
        requests_query = requests_ref.where("riderId", "==", rider_id).stream()
        requests = []
        
        for doc in requests_query:
            request_data = doc.to_dict()
            request_model = RideRequest.model_validate(request_data)
            requests.append(request_model)
        
        return requests
    except Exception as exc:
        raise Exception(f"Error retrieving ride requests: {exc}")

async def get_ride_requests_by_driver(driver_id: str, requests_ref):
    """Get all ride requests for rides created by a specific driver"""
    try:
        requests_query = requests_ref.where("driverId", "==", driver_id).stream()
        requests = []
        
        for doc in requests_query:
            request_data = doc.to_dict()
            request_model = RideRequest.model_validate(request_data)
            requests.append(request_model)
        
        return requests
    except Exception as exc:
        raise Exception(f"Error retrieving ride requests: {exc}")

async def get_ride_request_by_id(request_id: str, requests_ref):
    """Get a specific ride request by ID"""
    try:
        request_doc = requests_ref.document(request_id).get()
        if not request_doc.exists:
            return None
        
        request_data = request_doc.to_dict()
        return RideRequest.model_validate(request_data)
    except Exception as exc:
        raise Exception(f"Error retrieving ride request: {exc}")

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