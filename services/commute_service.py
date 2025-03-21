from models import Commute, RideDistance
from datetime import datetime

    
async def create_new_commute(commute: Commute, commutes_ref, rides_ref):
    """Create a new commute and populate it with ride_distances"""
    # Check if commute already exists
    commute_ref = commutes_ref.document(commute.commuteId)
    existing = commute_ref.get()
    
    if existing.exists:
        raise ValueError("Commute already exists")
    
    # Get all rides
    all_rides = rides_ref.stream()
    
    # Create RideDistance objects for each ride
    ride_distances = []
    for ride_doc in all_rides:
        ride_data = ride_doc.to_dict()
        ride_distance = RideDistance(
            ride_id=ride_data.get("rideId"),
            distance=1.0  # Default distance value
        )
        ride_distances.append(ride_distance)
    
    # Set the ride_distances field in the commute
    commute.ride_distances = ride_distances
    
    # Save the commute to Firestore
    commute_data = commute.model_dump()
    commute_ref.set(commute_data)
    
    return commute

async def update_commute(commute_id: str, commute_update: Commute, commutes_ref):
    """Update an existing commute in Firestore"""
    # Check if commute exists
    commute_ref = commutes_ref.document(commute_id)
    existing = commute_ref.get()
    
    if not existing.exists:
        raise ValueError(f"Commute {commute_id} not found")
    
    # Set updated timestamp
    commute_update.updatedAt = datetime.now()
    
    # Update the commute
    try:
        commute_data = commute_update.model_dump()
        commute_ref.set(commute_data)
        return commute_update
    except Exception as exc:
        raise Exception(f"Error updating commute: {exc}")