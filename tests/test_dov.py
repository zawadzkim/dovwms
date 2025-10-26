"""Tests for the DOV client module."""

import json
from unittest.mock import Mock, patch

import pytest
from shapely.geometry import Point

from dovwms import DOVClient, get_profile_from_dov

# Shared fixtures were moved to tests/conftest.py


# Tests for DOVClient initialization


def test_dov_client_initialization(dov_client):
    """Test that DOV client initializes with correct base URL."""
    assert dov_client.base_url == "https://www.dov.vlaanderen.be/geoserver"


# Tests for list_wms_layers


@patch.object(DOVClient, "list_wms_layers")
def test_list_wms_layers_only_soil(mock_list, dov_client):
    """Test listing WMS layers with soil filter."""
    mock_list.return_value = {"bodem:texture": "Soil Texture", "bodem:type": "Soil Type"}

    layers = dov_client.list_wms_layers(only_soil=True)

    assert len(layers) == 2
    assert all("bodem" in name.lower() for name in layers.keys())
    mock_list.assert_called_once()


@patch.object(DOVClient, "list_wms_layers")
def test_list_wms_layers_all(mock_list, dov_client):
    """Test listing all WMS layers without filter."""
    mock_list.return_value = {"bodem:texture": "Soil Texture", "geologie:bedrock": "Bedrock Geology"}

    layers = dov_client.list_wms_layers(only_soil=False)

    assert len(layers) == 2
    mock_list.assert_called_once()


# Tests for parse_feature_info


def test_parse_feature_info_texture(dov_client, mock_wms_response):
    """Test parsing texture data from WMS response."""
    json_content = json.dumps(mock_wms_response)

    result = dov_client.parse_feature_info(json_content, content_type="application/json", query_type="texture")

    assert isinstance(result, dict)
    layers = result.get("layers", [])
    assert len(layers) == 5  # Five depth layers

    # Check first layer structure and numeric ranges (values vary in real responses)
    first_layer = layers[0]
    assert first_layer["name"] == "Layer_0-10cm"
    assert first_layer["layer_top"] == 0
    assert first_layer["layer_bottom"] == 10

    # Contents should be numeric percentages (0-100)
    for key in ("clay_content", "silt_content", "sand_content"):
        assert key in first_layer
        assert isinstance(first_layer[key], (int, float))
        assert 0.0 <= float(first_layer[key]) <= 100.0

    # Check metadata and that uncertainty is numeric (real responses provide numeric CI)
    assert "metadata" in first_layer
    assert isinstance(first_layer["metadata"]["clay_content"]["uncertainty"], (int, float))
    assert "DOV WMS" in first_layer["metadata"]["sand_content"]["source"]


def test_parse_feature_info_empty(dov_client, empty_wms_response):
    """Test parsing empty WMS response."""
    json_content = json.dumps(empty_wms_response)

    result = dov_client.parse_feature_info(json_content, content_type="application/json", query_type="texture")

    assert isinstance(result, dict)
    assert result.get("layers") == []


def test_parse_feature_info_raw_content(dov_client):
    """Test parsing non-texture content returns content wrapped in dict."""
    raw_content = "Some raw content"

    result = dov_client.parse_feature_info(raw_content, content_type="text/plain", query_type="properties")

    assert isinstance(result, dict)
    assert "content" in result
    assert result["content"] == raw_content


# Tests for _parse_texture_response


def test_parse_texture_response_all_layers(dov_client, mock_wms_response):
    """Test that all depth layers are parsed correctly."""
    json_content = json.dumps(mock_wms_response)
    result = dov_client._parse_texture_response(json_content)
    layers = result.get("layers", [])

    expected_depths = [
        (0, 10, "Layer_0-10cm"),
        (10, 30, "Layer_10-30cm"),
        (30, 60, "Layer_30-60cm"),
        (60, 100, "Layer_60-100cm"),
        (100, 150, "Layer_100-150cm"),
    ]

    assert len(layers) == len(expected_depths)

    for layer, (top, bottom, name) in zip(layers, expected_depths):
        assert layer["layer_top"] == top
        assert layer["layer_bottom"] == bottom
        assert layer["name"] == name


def test_parse_texture_response_metadata_sources(dov_client, mock_wms_response):
    """Test that metadata sources are correctly assigned."""
    json_content = json.dumps(mock_wms_response)
    result = dov_client._parse_texture_response(json_content)
    layers = result.get("layers", [])

    for layer in layers:
        metadata = layer["metadata"]
        assert "fractie_klei" in metadata["clay_content"]["source"]
        assert "fractie_leem" in metadata["silt_content"]["source"]
        assert "fractie_zand" in metadata["sand_content"]["source"]


# Tests for fetch_profile


@patch.object(DOVClient, "check_layer_exists")
@patch.object(DOVClient, "parse_feature_info")
def test_fetch_profile_success(mock_parse, mock_check, dov_client, sample_location, mock_wms_response):
    """Test successful profile fetching without elevation."""
    mock_check.return_value = True
    mock_parse.return_value = {"layers": [{"name": "Layer_0-10cm", "clay_content": 15.2}]}

    # Mock the WMS getfeatureinfo call
    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_wms_response)
    dov_client.wms = Mock()
    dov_client.wms.getfeatureinfo.return_value = mock_response

    profile = dov_client.fetch_profile(sample_location, fetch_elevation=False)

    assert profile is not None
    assert isinstance(profile, dict)
    assert len(profile.get("layers", [])) == 1
    mock_check.assert_called()


@patch.object(DOVClient, "check_layer_exists")
def test_fetch_profile_layer_not_found(mock_check, dov_client, sample_location):
    """Test handling of missing layers."""
    mock_check.return_value = False

    profile = dov_client.fetch_profile(sample_location)

    assert profile is None


@patch.object(DOVClient, "check_layer_exists")
def test_fetch_profile_wms_error(mock_check, dov_client, sample_location):
    """Test handling of WMS service errors."""
    mock_check.return_value = True
    dov_client.wms = Mock()
    dov_client.wms.getfeatureinfo.side_effect = Exception("WMS connection failed")

    profile = dov_client.fetch_profile(sample_location)

    assert profile is None


def test_fetch_profile_custom_crs(dov_client, sample_location):
    """Test profile fetching with custom CRS."""
    dov_client.wms = Mock()
    dov_client.check_layer_exists = Mock(return_value=True)

    mock_response = Mock()
    mock_response.read.return_value = json.dumps({"features": []})
    dov_client.wms.getfeatureinfo.return_value = mock_response
    dov_client.parse_feature_info = Mock(return_value={"layers": []})

    profile = dov_client.fetch_profile(sample_location, crs="EPSG:4326")

    # Verify CRS was passed to getfeatureinfo
    call_kwargs = dov_client.wms.getfeatureinfo.call_args[1]
    assert call_kwargs["srs"] == "EPSG:4326"


# Tests for get_profile_from_dov convenience function


@patch("dovwms.dov.DOVClient")
def test_get_profile_from_dov_success(mock_client_cls):
    """Test successful profile retrieval via convenience function."""
    mock_client = Mock()
    mock_client.fetch_profile.return_value = {"layers": [{"name": "Layer_0-10cm"}]}
    mock_client_cls.return_value = mock_client

    profile = get_profile_from_dov(247172.56, 204590.58)

    assert profile is not None
    mock_client.fetch_profile.assert_called_once()


@patch("dovwms.dov.DOVClient")
def test_get_profile_from_dov_custom_crs(mock_client_cls):
    """Test convenience function with custom CRS."""
    mock_client = Mock()
    mock_client.fetch_profile.return_value = {"layers": [{"name": "Layer_0-10cm"}]}
    mock_client_cls.return_value = mock_client

    profile = get_profile_from_dov(6.5, 50.5, crs="EPSG:4326", fetch_elevation=False)

    assert profile is not None
    call_kwargs = mock_client.fetch_profile.call_args[1]
    assert call_kwargs["crs"] == "EPSG:4326"


@patch("dovwms.dov.DOVClient")
def test_get_profile_from_dov_error_handling(mock_client_cls):
    """Test error handling in convenience function."""
    mock_client = Mock()
    mock_client.fetch_profile.side_effect = Exception("Connection failed")
    mock_client_cls.return_value = mock_client

    profile = get_profile_from_dov(247172.56, 204590.58)

    assert profile is None


@patch("dovwms.dov.DOVClient")
def test_get_profile_from_dov_point_creation(mock_client_cls):
    """Test that coordinates are correctly converted to Point."""
    mock_client = Mock()
    mock_client.fetch_profile.return_value = {"layers": [{"name": "Layer_0-10cm"}]}
    mock_client_cls.return_value = mock_client

    x, y = 247172.56, 204590.58
    get_profile_from_dov(x, y)

    # Verify Point was created with correct coordinates
    call_args = mock_client.fetch_profile.call_args
    location_arg = call_args[1].get("location") or call_args[0][0]
    assert isinstance(location_arg, Point)
    assert location_arg.x == x
    assert location_arg.y == y


# Integration-style tests (can be marked to skip in CI)


@pytest.mark.integration
def test_fetch_profile_real_service(sample_location):
    """Integration test with real DOV service (requires network)."""
    client = DOVClient()
    profile = client.fetch_profile(sample_location, fetch_elevation=False)

    # This will only work if the service is accessible
    if profile is not None:
        assert isinstance(profile, dict)
        assert len(profile.get("layers", [])) > 0


@pytest.mark.integration
def test_get_profile_from_dov_real_service():
    """Integration test for convenience function with real service."""
    profile = get_profile_from_dov(247172.56, 204590.58, fetch_elevation=False)

    if profile is not None:
        assert isinstance(profile, dict)
