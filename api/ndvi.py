from http.server import BaseHTTPRequestHandler
import json
from sentinelhub import (
    SHConfig, BBox, CRS, DataCollection,
    SentinelHubRequest, MimeType, bbox_to_dimensions
)
import numpy as np

CLIENT_ID     = 'sh-2cd34e24-e2d3-4c5d-bc65-4b42a4daf928'
CLIENT_SECRET = 'ncYvC4pWU2Hmf7TV6YW1EwK71EQNovdE'

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            lat = float(self.path.split('lat=')[1].split('&')[0]) if 'lat=' in self.path else 26.3
            lon = float(self.path.split('lon=')[1].split('&')[0]) if 'lon=' in self.path else 43.9

            config = SHConfig()
            config.sh_client_id     = CLIENT_ID
            config.sh_client_secret = CLIENT_SECRET
            config.sh_base_url      = 'https://sh.dataspace.copernicus.eu'
            config.sh_token_url     = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'

            bbox = BBox([lon-0.05, lat-0.05, lon+0.05, lat+0.05], crs=CRS.WGS84)
            size = bbox_to_dimensions(bbox, resolution=60)

            evalscript = """
//VERSION=3
function setup() {
  return { input: ["B04","B08"], output: { bands: 1, sampleType: "FLOAT32" } };
}
function evaluatePixel(s) {
  return [(s.B08 - s.B04) / (s.B08 + s.B04)];
}
"""
            request = SentinelHubRequest(
                evalscript=evalscript,
                input_data=[SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A.define_from(
                        'S2L2A', service_url='https://sh.dataspace.copernicus.eu'
                    ),
                    time_interval=('2025-05-01', '2025-05-31'),
                    other_args={"dataFilter": {"maxCloudCoverage": 30}}
                )],
                responses=[SentinelHubRequest.output_response('default', MimeType.TIFF)],
                bbox=bbox, size=size, config=config
            )

            data = request.get_data()[0]
            ndvi = float(np.nanmean(data))

            result = {
                "ndvi": round(ndvi, 4),
                "lat": lat, "lon": lon,
                "status": "إجهاد شديد" if ndvi < 0.2 else "إجهاد واضح" if ndvi < 0.4 else "إجهاد خفيف" if ndvi < 0.6 else "صحي"
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.end_headers()
