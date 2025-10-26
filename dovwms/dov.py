"""Client for the Belgian DOV (Databank Ondergrond Vlaanderen) API."""

import json
import logging
from typing import Any, Callable, Optional

from shapely.geometry import Point

from dovwms.base import WMSClient
from dovwms.geopunt import get_elevation

logger = logging.getLogger(__name__)


class DOVClient(WMSClient):
    """Client for fetching soil data from the Belgian DOV API."""

    def __init__(self) -> None:
        """Lazy-initialize the DOV client.

        Connects to the DOV Geoserver WMS service for accessing soil data
        and related geological information.
        """
        super().__init__(base_url="https://www.dov.vlaanderen.be/geoserver")

    def list_wms_layers(self, filter_func: Optional[Callable[[str, str], bool]] = None) -> dict[str, str]:
        """List available WMS layers from the DOV service.

        Arguments:
            filter_func: Optional function to filter layers. Takes layer name and title
                     as arguments and returns bool. If None, only soil-related layers
                     are returned.

        Returns:
            Dictionary of layer names and titles
        """

        def soil_filter(name: str, title: str) -> bool:
            if filter_func is not None:
                return filter_func(name, title)
            return "bodem" in name.lower()

        return super().list_wms_layers(filter_func=soil_filter)

    def parse_feature_info(self, content: str, **kwargs: Any) -> dict[str, Any]:
        """Parse GetFeatureInfo response from DOV WMS.

        The parsing method depends on the content type and query type:
        - For soil texture: Parses JSON response with layer properties
        - For other queries: Returns raw content for specific handling

        Arguments:
            content: Raw response content
            **kwargs: Additional parameters:
                - content_type: Expected content type
                - query_type: Type of query (e.g., 'texture', 'properties')

        Returns:
            Parsed content in appropriate format
        """
        content_type = kwargs.get("content_type", "application/json")
        query_type = kwargs.get("query_type", "properties")

        if content_type == "application/json" and query_type == "texture":
            return self._parse_texture_response(content)

        return {"content": content}

    def _parse_texture_response(self, data: Any) -> dict[str, Any]:
        """Parse the WMS GetFeatureInfo response to extract texture fractions.

        Always returns a dictionary with a single key "layers" containing a
        list of layer dictionaries. This makes the parser output stable and
        lets callers attach additional information (e.g. elevation) to the
        returned dict without special-casing list vs dict.

        Args:
            data: data from a WMS GetFeatureInfo response (JSON string)

        Returns:
            Dict with key "layers" mapping to a list of layer dicts. If no
            features were found, returns {"layers": []}.
        """
        json_data = json.loads(data)
        features = json_data.get("features", [])

        if not features:
            return {"layers": []}

        properties = [feature.get("properties") for feature in features]

        # create Layer objects for each of the profiles
        depth_keys = [k for k in properties[0] if not k.endswith("_betrouwbaarheid")]

        # Map Dutch depth notation to layer info
        depth_mapping = {
            "_0_-_10_cm": (0, 10, "Layer_0-10cm"),
            "_10_-_30_cm": (10, 30, "Layer_10-30cm"),
            "_30_-_60_cm": (30, 60, "Layer_30-60cm"),
            "_60_-_100_cm": (60, 100, "Layer_60-100cm"),
            "_100_-_150_cm": (100, 150, "Layer_100-150cm"),
        }

        layers = []

        for depth_key in depth_keys:
            ci_key = f"{depth_key}_betrouwbaarheid"

            # Extract texture percentages and confidence intervals
            clay_pct = properties[0][depth_key]
            clay_mtd = {
                "source": "DOV WMS, bdbstat:fractie_klei_basisdata_bodemkartering",
                "uncertainty": properties[0][ci_key],
            }
            silt_pct = properties[1][depth_key]
            silt_mtd = {
                "source": "DOV WMS, bdbstat:fractie_leem_basisdata_bodemkartering",
                "uncertainty": properties[1][ci_key],
            }
            sand_pct = properties[2][depth_key]
            sand_mtd = {
                "source": "DOV WMS, bdbstat:fractie_zand_basisdata_bodemkartering",
                "uncertainty": properties[2][ci_key],
            }

            # Get depth info
            top_depth, bottom_depth, layer_name = depth_mapping[depth_key]

            # Create SoilLayer object
            layer = {
                "name": layer_name,
                "layer_top": top_depth,
                "layer_bottom": bottom_depth,
                "sand_content": sand_pct,
                "silt_content": silt_pct,
                "clay_content": clay_pct,
                "metadata": {
                    "sand_content": sand_mtd,
                    "silt_content": silt_mtd,
                    "clay_content": clay_mtd,
                },
            }

            layers.append(layer)

        return {"layers": layers}

    def fetch_profile(
        self, location: Point, fetch_elevation: bool = False, crs: str = "EPSG:31370"
    ) -> Optional[dict[str, Any]]:
        """Fetch soil texture information from the DOV WMS at a specific location.

        This method queries the DOV WMS service for clay, silt, and sand content
        at different depths at the specified location. The data is used to create
        a SoilProfile object with appropriate layers.

        Args:
            location: Point object with x, y coordinates
            fetch_elevation: Whether to fetch the elevation of the location from Geopunt.
            crs: Coordinate reference system

        Returns:
            Dictionary with texture data ("layers" key and optional "elevation") or None if data not found
        """
        # Texture layers from DOV bodemanalysie service.
        wms_layers = [
            "bdbstat:fractie_klei_basisdata_bodemkartering",  # clay
            "bdbstat:fractie_leem_basisdata_bodemkartering",  # silt
            "bdbstat:fractie_zand_basisdata_bodemkartering",  # sand
        ]

        # Verify layers exist
        for layer_name in wms_layers:
            if not self.check_layer_exists(layer_name):
                logger.warning("Layer %s not found", layer_name)
                return None

        # Define query area
        buffer = 0.0001
        bbox = (location.x - buffer, location.y - buffer, location.x + buffer, location.y + buffer)

        try:
            # Query texture data
            response = self.wms.getfeatureinfo(
                layers=wms_layers,
                query_layers=wms_layers,
                srs=crs,
                bbox=bbox,
                size=(100, 100),
                info_format="application/json",
                xy=(50, 50),  # center pixel
            )

            result = self.parse_feature_info(response.read(), content_type="application/json", query_type="texture")

            if fetch_elevation:
                elevation = get_elevation(location, crs)
                result["elevation"] = elevation
        except Exception:
            logger.exception("Failed to fetch profile")
            return None
        else:
            return result


def get_profile_from_dov(
    x: float, y: float, crs: str = "EPSG:31370", fetch_elevation: bool = True, profile_name: Optional[str] = None
) -> Optional[dict[str, Any]]:
    """Convenience function to fetch a soil profile from DOV at given coordinates.

    This function handles all the necessary client setup and coordinate conversion
    to get a soil profile from the DOV service. It's a simpler alternative to
    creating and managing DOV and Geopunt clients manually.

    Args:
        x: X-coordinate in the specified CRS (default Lambert72)
        y: Y-coordinate in the specified CRS (default Lambert72)
        profile_name: Optional name for the profile. If None, will use coordinates
        crs: Coordinate reference system of the input coordinates
        fetch_elevation: elevation data

    Returns:
        SoilProfile object with texture and optional elevation data,
        or None if the data couldn't be fetched

    Example:
        >>> profile = get_profile_from_dov(247172.56, 204590.58)
        >>> print(f"Elevation: {profile.elevation:.2f}m")
        >>> print(f"Number of layers: {len(profile.layers)}")
    """
    try:
        # Create location point
        location = Point(x, y)

        # Use coordinates for profile name if none provided (kept for backward compatibility,
        # but DOVClient.fetch_profile does not currently accept a profile_name parameter)
        if profile_name is None:
            profile_name = f"Profile_{x:.0f}_{y:.0f}"

        # Create DOV client
        client = DOVClient()

        # Fetch profile. Use the public DOVClient API: (location, fetch_elevation, crs)
        profile = client.fetch_profile(location, fetch_elevation=fetch_elevation, crs=crs)
    except Exception:
        logger.exception("Failed to get profile from DOV")
        return None
    else:
        return profile
        logger.exception("Error fetching profile from DOV")
        return None
