# mypy: disable-error-code="import-untyped"

import logging
from typing import Any, Optional

from shapely.geometry import Point

from dovwms.base import WMSClient

logger = logging.getLogger(__name__)


class GeopuntClient(WMSClient):
    """Client for fetching data from the Geopunt API."""

    def __init__(self) -> None:
        super().__init__(base_url="https://geo.api.vlaanderen.be/DHMV")

    def parse_feature_info(self, content: str, **kwargs: Any) -> dict[str, Any]:
        """Parse GetFeatureInfo response from Geopunt WMS.

        The parsing method depends on the content type and query type:
        - For elevation: Parses semicolon-separated response for elevation value
        - For other queries: Returns raw content for specific handling.
        - One substantial change.

        Args:
            content: Raw response content
            **kwargs: Additional parameters:
                - content_type: Expected content type
                - query_type: Type of query (e.g., 'elevation')

        Returns:
            Dict containing either {'elevation': float or None} or {'content': str}
        """
        query_type = kwargs.get("query_type", "elevation")

        if query_type == "elevation":
            elevation = self._parse_elevation_response(content)
            return {"elevation": elevation}

        return {"content": content}

    def _parse_elevation_response(self, content: str) -> Optional[float]:
        """Parse elevation data from GetFeatureInfo response.

        Args:
            content: Raw response content from WMS GetFeatureInfo

        Returns:
            Elevation in meters or None if parsing fails

        Note:
            Response format example:
            "@DHMVII_DTM_1m Stretched value;Pixel Value; 32.360001;32.360001;"
        """
        try:
            values = content.strip().split(";")
            if len(values) >= 3:
                return float(values[2].strip())
        except (ValueError, IndexError) as e:
            logger.warning("Error parsing elevation data: %s", e)
        return None

    def fetch_elevation(
        self, location: Point, crs: str = "EPSG:31370", layer_name: str = "DHMVII_DTM_1m"
    ) -> Optional[dict[str, Any]]:
        """Fetch elevation data from the Geopunt WMS at a specific location.

        Args:
            location: Point object with x, y coordinates
            crs: Coordinate reference system
        Returns:
            Elevation in meters or None if not found
        """
        # Layer name for Digital Terrain Model (1m resolution)

        if not self.check_layer_exists(layer_name):
            try:
                available = list(self.wms.contents.keys())
            except Exception:
                available = []
            logger.warning("Layer %s not found. Available layers: %s", layer_name, available)
            return None

        buffer = 0.0001
        bbox = (location.x - buffer, location.y - buffer, location.x + buffer, location.y + buffer)

        # Image size and center pixel
        img_width = img_height = 256
        pixel_x = pixel_y = img_width // 2

        try:
            # Make GetFeatureInfo request
            response = self.wms.getfeatureinfo(
                layers=[layer_name],
                query_layers=[layer_name],
                info_format="text/plain",
                srs=crs,
                bbox=bbox,
                size=(img_width, img_height),
                xy=(pixel_x, pixel_y),
            )

            # Parse response using the base class method
            content = response.read().decode("utf-8")
            elevation = self.parse_feature_info(content, content_type="text/plain", query_type="elevation")

            if elevation is not None:
                logger.info("Fetched elevation from Geopunt API")
        except Exception:
            logger.exception("Failed to fetch elevation from Geopunt API")
            return None
        else:
            return elevation


def get_elevation(
    location: Point, crs: str = "EPSG:31370", layer_name: str = "DHMVII_DTM_1m"
) -> Optional[dict[str, Any]]:
    """Convenience wrapper to fetch elevation using the GeopuntClient.

    This helper creates a GeopuntClient, requests the elevation for the
    provided location and returns the value. Tests can patch this function
    to avoid instantiating the client or making network calls.
    """
    client = GeopuntClient()
    return client.fetch_elevation(location, crs, layer_name)
