import googlemaps


class GoogleMap:
    def __init__(self):
        api_key = ''
        with open(r'C:\Users\user\Desktop\googleApi.txt',
                  'r') as f:
            api_key = f.readline()
        self.gmaps = googlemaps.Client(key=api_key)

    def distance(self, location1: dict, location2: dict):
        return \
            self.gmaps.distance_matrix(location1, location2,
                                       language='ru')[
                'rows'][
                0][
                'elements'][0]['distance'][
                'value'] / 1000000

    def location_to_point(self, location: str):
        return \
            self.gmaps.geocode(location, language='ru')[0][
                'geometry']['location']

    def point_to_location(self, point: dict):
        return \
            self.gmaps.reverse_geocode(point,
                                       language='ru')[0][
                'formatted_address']

    def location_point_from_text(self, location:str):
        result = self.gmaps.geocode(location, language='ru')[0]
        return result['formatted_address'], \
               result['geometry']['location']
