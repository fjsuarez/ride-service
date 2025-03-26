import asyncio
from google.maps import routing_v2
from google.type import latlng_pb2
from .helpers import decode_polyline, sample_points_along_polyline

async def get_driving_route_polyline(origin_coord, destination_coord):
    async with routing_v2.RoutesAsyncClient() as client:
        origin = routing_v2.Waypoint(location=routing_v2.Location(lat_lng=latlng_pb2.LatLng(latitude=origin_coord[0], longitude=origin_coord[1])))
        destination = routing_v2.Waypoint(location=routing_v2.Location(lat_lng=latlng_pb2.LatLng(latitude=destination_coord[0], longitude=destination_coord[1])))

        request = routing_v2.ComputeRoutesRequest(
            origin=origin,
            destination=destination,
            travel_mode=routing_v2.RouteTravelMode.DRIVE
        )
        field_mask = "routes.polyline.encodedPolyline" # Only need the polyline
        metadata = (("x-goog-fieldmask", field_mask),)

        try:
            response = await client.compute_routes(request=request, metadata=metadata)
            if response.routes:
                return response.routes[0].polyline.encoded_polyline
            else:
                print("Warning: No driving route found between A and B.")
                return None
        except Exception as e:
            print(f"Error getting driving route polyline: {type(e).__name__} - {e}")
            return None
        
async def get_walking_route_polyline(origin_coord, destination_coord):
    async with routing_v2.RoutesAsyncClient() as client:
        origin = routing_v2.Waypoint(location=routing_v2.Location(lat_lng=latlng_pb2.LatLng(latitude=origin_coord[0], longitude=origin_coord[1])))
        destination = routing_v2.Waypoint(location=routing_v2.Location(lat_lng=latlng_pb2.LatLng(latitude=destination_coord[0], longitude=destination_coord[1])))

        request = routing_v2.ComputeRoutesRequest(
            origin=origin,
            destination=destination,
            travel_mode=routing_v2.RouteTravelMode.WALK
        )
        field_mask = "routes.polyline.encodedPolyline" # Only need the polyline
        metadata = (("x-goog-fieldmask", field_mask),)

        try:
            response = await client.compute_routes(request=request, metadata=metadata)
            if response.routes:
                return response.routes[0].polyline.encoded_polyline
            else:
                print("Warning: No driving route found between A and B.")
                return None
        except Exception as e:
            print(f"Error getting driving route polyline: {type(e).__name__} - {e}")
            return None

async def get_walking_distance(client, origin_coord, destination_coord):
    async with routing_v2.RoutesAsyncClient() as client:
        origin = routing_v2.Waypoint(location=routing_v2.Location(lat_lng=latlng_pb2.LatLng(latitude=origin_coord[0], longitude=origin_coord[1])))
        destination = routing_v2.Waypoint(location=routing_v2.Location(lat_lng=latlng_pb2.LatLng(latitude=destination_coord[0], longitude=destination_coord[1])))

        request = routing_v2.ComputeRoutesRequest(
            origin=origin,
            destination=destination,
            travel_mode=routing_v2.RouteTravelMode.WALK
        )
        field_mask = "routes.distanceMeters"
        metadata = (("x-goog-fieldmask", field_mask),)

        try:
            response = await client.compute_routes(request=request, metadata=metadata)
            if response.routes and hasattr(response.routes[0], 'distance_meters'):
                return response.routes[0].distance_meters
            else:
                return float('inf')
        except Exception as e:
            print(f"Error getting walking distance from {origin_coord} to {destination_coord}: {type(e).__name__} - {e}")
            return float('inf')

async def find_closest_points_on_route_by_walking(
    origin_A_coord,
    destination_B_coord,
    origin_X_coord,
    destination_Y_coord,
    encoded_polyline,
    sampling_distance_meters=100 # Sample approx every 100 meters
):
    
    if not encoded_polyline:
        try:
            encoded_polyline = await get_driving_route_polyline(origin_A_coord, destination_B_coord)
        except Exception as e:
            print(f"Error getting driving route polyline: {type(e).__name__} - {e}")
            return None, None

    decoded_coords = decode_polyline(encoded_polyline)
    sample_coords = sample_points_along_polyline(decoded_coords, sampling_distance_meters)
    if not sample_coords:
            return None, None
    
    min_total_walk_dist = float('inf')
    best_entry_point_coord = None
    best_exit_point_coord = None
    valid_pairs_evaluated = 0

    tasks_X = [get_walking_distance(origin_X_coord, p_coord) for p_coord in sample_coords]
    walking_distances_X = await asyncio.gather(*tasks_X, return_exceptions=True)
    tasks_Y = [get_walking_distance(p_coord, destination_Y_coord) for p_coord in sample_coords]
    walking_distances_Y = await asyncio.gather(*tasks_Y, return_exceptions=True)
    
    for i in range(len(walking_distances_X)):
        if isinstance(walking_distances_X[i], Exception) or walking_distances_X[i] == float('inf'):
            continue
        for j in range(len(walking_distances_Y)):
            if isinstance(walking_distances_Y[j], Exception) or walking_distances_Y[j] == float('inf'):
                continue
            current_total_walk_dist = walking_distances_X[i] + walking_distances_Y[j]
            valid_pairs_evaluated += 1
            if current_total_walk_dist < min_total_walk_dist:
                min_total_walk_dist = current_total_walk_dist
                best_entry_point_coord = sample_coords[i]
                best_exit_point_coord = sample_coords[j]
    
    if best_entry_point_coord:
        return best_entry_point_coord, best_exit_point_coord, min_total_walk_dist, encoded_polyline
    else:
        print("   Could not determine the best entry and exit points.")
        return None, None, float('inf'), None