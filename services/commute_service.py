from models import Commute, RideDistance
from datetime import datetime
from .utils import find_closest_points_on_route_by_walking, get_walking_route_polyline

import logging 
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_new_commute(commute: Commute, commutes_ref, rides_ref):
    """Create a new commute and populate it with ride_distances"""
    try:
        logger.info(f"Creating new commute with ID: {commute.commuteId}")
        
        # Validate commute data
        if not commute.startLocation or not commute.endLocation:
            raise ValueError("Commute must have both start and end locations")
            
        # Check if commute already exists
        commute_ref = commutes_ref.document(commute.commuteId)
        existing = commute_ref.get()
        
        if existing.exists:
            raise ValueError(f"Commute with ID {commute.commuteId} already exists")
        
        # Get all rides
        logger.info("Fetching all rides")
        all_rides = list(rides_ref.stream())
        logger.info(f"Found {len(all_rides)} rides to evaluate")
        
        # Create RideDistance objects for each ride
        ride_distances = []
        for index, ride_doc in enumerate(all_rides):
            try:
                ride_data = ride_doc.to_dict()
                ride_id = ride_data.get("rideId")
                
                logger.info(f"Processing ride {index+1}/{len(all_rides)}: {ride_id}")
                
                # Validate ride data
                if not ride_data.get('startLocation') or not ride_data.get('endLocation'):
                    logger.warning(f"Skipping ride {ride_id}: Missing location data")
                    continue
                
                # Extract coordinates
                start_lat = ride_data.get('startLocation', {}).get('latitude')
                start_lng = ride_data.get('startLocation', {}).get('longitude')
                end_lat = ride_data.get('endLocation', {}).get('latitude')
                end_lng = ride_data.get('endLocation', {}).get('longitude')
                
                # Validate coordinates
                if None in [start_lat, start_lng, end_lat, end_lng]:
                    logger.warning(f"Skipping ride {ride_id}: Invalid coordinates")
                    continue
                
                logger.info(f"Finding closest points on route for ride {ride_id}")
                
                # Get ride polyline
                encoded_polyline = ride_data.get('ridePolyline')
                if not encoded_polyline:
                    logger.warning(f"Ride {ride_id} has no polyline data")
                
                # Find closest points
                try:
                    result = await find_closest_points_on_route_by_walking(
                        origin_A_coord=(start_lat, start_lng),
                        destination_B_coord=(end_lat, end_lng),
                        origin_X_coord=(commute.startLocation.latitude, commute.startLocation.longitude),
                        destination_Y_coord=(commute.endLocation.latitude, commute.endLocation.longitude),
                        encoded_polyline=encoded_polyline
                    )
                    
                    if not result:
                        logger.warning(f"Could not find route for ride {ride_id}")
                        continue
                        
                    entry_point, exit_point, total_walk_distance, route_polyline = result
                    
                    # Validate results
                    if not entry_point or not exit_point or total_walk_distance == float('inf'):
                        logger.warning(f"Invalid route for ride {ride_id}")
                        continue
                    
                    logger.info(f"Found viable route for ride {ride_id} with walking distance: {total_walk_distance}m")
                    
                    # Get walking polylines
                    logger.info(f"Getting walking routes for ride {ride_id}")
                    entry_polyline = await get_walking_route_polyline(
                        (commute.startLocation.latitude, commute.startLocation.longitude), 
                        entry_point
                    )
                    exit_polyline = await get_walking_route_polyline(
                        exit_point,
                        (commute.endLocation.latitude, commute.endLocation.longitude)
                    )
                    
                    # Create ride distance object
                    ride_distance = RideDistance(
                        ride_id=ride_id,
                        distance=total_walk_distance,
                        entry_point=entry_point,
                        entry_polyline=entry_polyline,
                        exit_point=exit_point,
                        exit_polyline=exit_polyline
                    )
                    ride_distances.append(ride_distance)
                    logger.info(f"Added ride {ride_id} to viable options")
                    
                except Exception as e:
                    logger.error(f"Error processing ride {ride_id}: {str(e)}")
                    continue
                    
            except Exception as e:
                logger.error(f"Error processing ride document: {str(e)}")
                continue
        
        # Set the ride_distances field in the commute
        logger.info(f"Found {len(ride_distances)} viable rides for commute")
        commute.ride_distances = ride_distances
        
        # Save the commute to Firestore
        logger.info(f"Saving commute {commute.commuteId} to Firestore")
        commute_data = commute.model_dump()
        commute_ref.set(commute_data)
        
        logger.info(f"Successfully created commute {commute.commuteId}")
        return commute
        
    except Exception as e:
        logger.error(f"Failed to create commute: {str(e)}", exc_info=True)
        raise

async def update_commute(commute_id: str, commute_update: Commute, commutes_ref, rides_ref):
    """Update an existing commute in Firestore and recalculate ride distances"""
    try:
        logger.info(f"Updating commute with ID: {commute_id}")
        
        # Validate commute data
        if not commute_update.startLocation or not commute_update.endLocation:
            logger.error("Cannot update commute: Missing start or end location")
            raise ValueError("Commute must have both start and end locations")
        
        # Check if commute exists
        logger.info(f"Checking if commute {commute_id} exists")
        commute_ref = commutes_ref.document(commute_id)
        existing = commute_ref.get()
        
        if not existing.exists:
            logger.error(f"Commute {commute_id} not found")
            raise ValueError(f"Commute {commute_id} not found")
        
        # Set updated timestamp
        commute_update.updatedAt = datetime.now()
        logger.info(f"Updating commute timestamp to {commute_update.updatedAt}")
        
        # Get all rides
        logger.info("Fetching all rides to recalculate distances")
        all_rides = list(rides_ref.stream())
        logger.info(f"Found {len(all_rides)} rides to evaluate")
        
        # Create RideDistance objects for each ride
        ride_distances = []
        for index, ride_doc in enumerate(all_rides):
            try:
                ride_data = ride_doc.to_dict()
                ride_id = ride_data.get("rideId")
                
                logger.info(f"Processing ride {index+1}/{len(all_rides)}: {ride_id}")
                
                # Validate ride data
                if not ride_data.get('startLocation') or not ride_data.get('endLocation'):
                    logger.warning(f"Skipping ride {ride_id}: Missing location data")
                    continue
                
                # Extract coordinates
                start_lat = ride_data.get('startLocation', {}).get('latitude')
                start_lng = ride_data.get('startLocation', {}).get('longitude')
                end_lat = ride_data.get('endLocation', {}).get('latitude')
                end_lng = ride_data.get('endLocation', {}).get('longitude')
                
                # Validate coordinates
                if None in [start_lat, start_lng, end_lat, end_lng]:
                    logger.warning(f"Skipping ride {ride_id}: Invalid coordinates")
                    continue
                
                # Get ride polyline
                encoded_polyline = ride_data.get('ridePolyline')
                if not encoded_polyline:
                    logger.warning(f"Ride {ride_id} has no polyline data, may affect route calculation")
                
                logger.info(f"Finding closest points on route for ride {ride_id}")
                
                # Find closest points
                try:
                    result = await find_closest_points_on_route_by_walking(
                        origin_A_coord=(start_lat, start_lng),
                        destination_B_coord=(end_lat, end_lng),
                        origin_X_coord=(commute_update.startLocation.latitude, commute_update.startLocation.longitude),
                        destination_Y_coord=(commute_update.endLocation.latitude, commute_update.endLocation.longitude),
                        encoded_polyline=encoded_polyline
                    )
                    
                    if not result:
                        logger.warning(f"Could not find route for ride {ride_id}")
                        continue
                    
                    entry_point, exit_point, total_walk_distance, route_polyline = result
                    
                    # Validate results
                    if not entry_point or not exit_point or total_walk_distance == float('inf'):
                        logger.warning(f"Invalid route calculation for ride {ride_id}")
                        continue
                    
                    logger.info(f"Found viable route for ride {ride_id} with walking distance: {total_walk_distance}m")
                    
                    # Generate walking polylines
                    logger.info(f"Generating walking routes for ride {ride_id}")
                    
                    try:
                        logger.info(f"Getting entry walking route for ride {ride_id}")
                        entry_polyline = await get_walking_route_polyline(
                            (commute_update.startLocation.latitude, commute_update.startLocation.longitude),
                            entry_point
                        )
                        
                        logger.info(f"Getting exit walking route for ride {ride_id}")
                        exit_polyline = await get_walking_route_polyline(
                            exit_point,
                            (commute_update.endLocation.latitude, commute_update.endLocation.longitude)
                        )
                        
                        # Create ride distance object
                        ride_distance = RideDistance(
                            ride_id=ride_id,
                            distance=total_walk_distance,
                            entry_point=entry_point,
                            entry_polyline=entry_polyline,
                            exit_point=exit_point,
                            exit_polyline=exit_polyline
                        )
                        ride_distances.append(ride_distance)
                        logger.info(f"Added ride {ride_id} to viable options")
                        
                    except Exception as e:
                        logger.error(f"Error generating walking routes for ride {ride_id}: {str(e)}")
                        continue
                        
                except Exception as e:
                    logger.error(f"Error finding route points for ride {ride_id}: {str(e)}")
                    continue
                
            except Exception as e:
                logger.error(f"Error processing ride {ride_id}: {str(e)}")
                continue
        
        # Set the updated ride_distances field in the commute
        logger.info(f"Found {len(ride_distances)} viable rides for commute {commute_id}")
        commute_update.ride_distances = ride_distances
        
        # Update the commute
        try:
            logger.info(f"Saving updated commute {commute_id} to Firestore")
            commute_data = commute_update.model_dump()
            commute_ref.set(commute_data)
            logger.info(f"Successfully updated commute {commute_id}")
            return commute_update
        except Exception as exc:
            logger.error(f"Error saving commute to Firestore: {str(exc)}")
            raise Exception(f"Error updating commute: {exc}")
            
    except Exception as e:
        logger.error(f"Failed to update commute {commute_id}: {str(e)}", exc_info=True)
        raise