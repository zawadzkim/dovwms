"""Shared pytest fixtures for the dovwms tests.

Place common fixtures here so test modules can import them implicitly.
"""

import pytest
from shapely.geometry import Point

from dovwms import DOVClient, GeopuntClient


@pytest.fixture
def dov_client():
    """Provide a DOV client instance for testing."""
    return DOVClient()


@pytest.fixture
def geopunt_client():
    """Provide a Geopunt client instance for testing."""
    return GeopuntClient()


@pytest.fixture
def sample_location():
    """Provide a sample location point in Lambert72 coordinates."""
    return Point(247172.56, 204590.58)


@pytest.fixture
def mock_wms_response():
    """Provide a mock WMS GetFeatureInfo response with texture data."""
    # Realistic WMS-like response with numeric uncertainty values and extra metadata
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "",
                "geometry": None,
                "properties": {
                    "_0_-_10_cm": 3.611795663833618,
                    "_10_-_30_cm": 3.3866608142852783,
                    "_30_-_60_cm": 3.2221295833587646,
                    "_60_-_100_cm": 4.441609859466553,
                    "_100_-_150_cm": 5.9969096183776855,
                    "_0_-_10_cm_betrouwbaarheid": 0.36081814765930176,
                    "_10_-_30_cm_betrouwbaarheid": 0.052916716784238815,
                    "_30_-_60_cm_betrouwbaarheid": 1.635129451751709,
                    "_60_-_100_cm_betrouwbaarheid": 2.9045262336730957,
                    "_100_-_150_cm_betrouwbaarheid": 0.6920930743217468,
                },
            },
            {
                "type": "Feature",
                "id": "",
                "geometry": None,
                "properties": {
                    "_0_-_10_cm": 22.44235610961914,
                    "_10_-_30_cm": 21.5340576171875,
                    "_30_-_60_cm": 23.25323486328125,
                    "_60_-_100_cm": 17.14266014099121,
                    "_100_-_150_cm": 12.025032997131348,
                    "_0_-_10_cm_betrouwbaarheid": 0.3361551761627197,
                    "_10_-_30_cm_betrouwbaarheid": 3.2321090698242188,
                    "_30_-_60_cm_betrouwbaarheid": 0.04036116972565651,
                    "_60_-_100_cm_betrouwbaarheid": 2.195176362991333,
                    "_100_-_150_cm_betrouwbaarheid": 1.328452467918396,
                },
            },
            {
                "type": "Feature",
                "id": "",
                "geometry": None,
                "properties": {
                    "_0_-_10_cm": 72.97166442871094,
                    "_10_-_30_cm": 72.86681365966797,
                    "_30_-_60_cm": 76.02572631835938,
                    "_60_-_100_cm": 77.10255432128906,
                    "_100_-_150_cm": 81.56967163085938,
                    "_0_-_10_cm_betrouwbaarheid": 0.17820630967617035,
                    "_10_-_30_cm_betrouwbaarheid": 0.8113504648208618,
                    "_30_-_60_cm_betrouwbaarheid": 0.15391893684864044,
                    "_60_-_100_cm_betrouwbaarheid": 2.6368417739868164,
                    "_100_-_150_cm_betrouwbaarheid": 3.644649028778076,
                },
            },
        ],
        "totalFeatures": "unknown",
        "numberReturned": 3,
        "timeStamp": "2025-10-26T11:38:35.044Z",
        "crs": None,
    }


@pytest.fixture
def empty_wms_response():
    """Provide an empty WMS response."""
    return {"type": "FeatureCollection", "features": []}
