from models import Ride

async def get_all_rides(rides_ref):
    """Get all rides from Firestore"""
    docs = rides_ref.stream()
    rides = []
    
    for doc in docs:
        ride_data = doc.to_dict()
        try:
            ride_model = Ride.model_validate(ride_data)
            rides.append(ride_model.model_dump())
        except Exception as exc:
            raise Exception(f"Error parsing ride document: {exc}")
    
    return rides

async def create_new_ride(ride: Ride, rides_ref):
    """Create a new ride in Firestore"""
    ride_data = ride.model_dump()
    
    # Check if ride already exists
    ride_ref = rides_ref.document(ride.rideId)
    existing = ride_ref.get()
    
    if existing.exists:
        raise ValueError("Ride already exists")
    
    # Create new ride document
    try:
        ride_ref.set(ride_data)
        return ride
    except Exception as exc:
        raise Exception(f"Error creating ride document: {exc}")