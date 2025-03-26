import math
import polyline

def decode_polyline(encoded_polyline_str):
    if not encoded_polyline_str:
        return []
    return polyline.decode(encoded_polyline_str)

def haversine(coord1, coord2):
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000 # Radius of Earth in meters
    return c * r

def interpolate(coord1, coord2, fraction):
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    lat = lat1 + (lat2 - lat1) * fraction
    lon = lon1 + (lon2 - lon1) * fraction
    return lat, lon

def sample_points_along_polyline(decoded_coords, sampling_distance_meters):
    if not decoded_coords or len(decoded_coords) < 2:
        return decoded_coords[:] # Return a copy if too short to sample

    sampled_points = [decoded_coords[0]]
    distance_covered_on_segment = 0.0

    for i in range(len(decoded_coords) - 1):
        segment_start_coord = decoded_coords[i]
        segment_end_coord = decoded_coords[i+1]
        segment_length = haversine(segment_start_coord, segment_end_coord)
        if segment_length <= 1e-9:
            continue
        distance_needed_from_segment_start = sampling_distance_meters - distance_covered_on_segment
        current_pos_on_segment = 0.0
        while distance_needed_from_segment_start <= (segment_length - current_pos_on_segment):
            current_pos_on_segment += distance_needed_from_segment_start
            fraction = current_pos_on_segment / segment_length
            new_sample = interpolate(segment_start_coord, segment_end_coord, fraction)
            if not sampled_points or haversine(new_sample, sampled_points[-1]) > 1e-6:
                 sampled_points.append(new_sample)
            distance_covered_on_segment = 0.0
            distance_needed_from_segment_start = sampling_distance_meters
        distance_covered_on_segment += (segment_length - current_pos_on_segment)

    if not sampled_points or haversine(decoded_coords[-1], sampled_points[-1]) > 1e-6:
         sampled_points.append(decoded_coords[-1])

    return sampled_points