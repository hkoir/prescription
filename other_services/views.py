from django.shortcuts import render
from .models import NearbyService
from math import radians, sin, cos, sqrt, atan2



def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def nearby_service_list(request):
    services = []
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    radius = float(request.GET.get('radius', 10))
    service_type = request.GET.get('service_type', '').strip()

    user_lat = lat or ''
    user_lng = lng or ''

    if lat and lng:
        try:
            lat = float(lat)
            lng = float(lng)

            queryset = NearbyService.objects.all()
            if service_type:
                queryset = queryset.filter(service_type=service_type)

            for service in queryset:
                distance = haversine(lat, lng, service.latitude, service.longitude)
                if distance <= radius:
                  services.append({
                        'service': {
                            'name': service.name or '',
                            'latitude': service.latitude or 0,
                            'longitude': service.longitude or 0,
                            'address': service.address or 'N/A',
                            'contact_number': service.contact_number or 'N/A',
                            'service_type': service.get_service_type_display() or 'N/A',
                        },
                        'distance': round(distance, 2),
                    })



            services.sort(key=lambda x: x['distance'])

        except ValueError:
            pass

    return render(request, 'other_services/nearby_services_list.html', {
        'services': services,
        'user_lat': user_lat,
        'user_lng': user_lng,
        'radius': radius,
        'service_type': service_type
    })
