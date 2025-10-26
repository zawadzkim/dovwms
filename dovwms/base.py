# mypy: disable-error-code="import-untyped, no-any-return, no-any-unimported"
# The errors were caused by owslib lacking proper type stubs, which means mypy
# can't determine the exact type of WebMapService and its methods.

"""Base classes for API clients."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Union
import logging
from owslib.wms import WebMapService

logger = logging.getLogger(__name__)


class WMSClient(ABC):
    """Abstract base class for WMS service clients."""
    
    def __init__(self, base_url: str, wms_version: str = '1.3.0'):
        """Initialize the WMS client.

        The reason for the property and a setter implementation is to allow lazy connection
        to the WMS service at the point it is needed.

        Arguments:
            base_url: Base URL of the WMS service
            wms_version: WMS protocol version to use
        """
        self.base_url = base_url
        self.wms_version = wms_version
        self._wms: Optional[WebMapService] = None

    @property
    def wms(self) -> WebMapService:
        """Get the WMS connection, establishing it if needed."""
        if self._wms is None:
            self.connect_wms()
        return self._wms

    @wms.setter
    def wms(self, value: WebMapService) -> None:
        """Set the WMS connection.
        
        The setter allows injecting a mock WMS for testing.
        """
        self._wms = value

    def connect_wms(self) -> WebMapService:
        """Connect to the WMS service and return the connected WebMapService.

        Returns:
            The connected WebMapService instance.
        """
        wms_url = self.base_url if self.base_url.endswith('/wms') else f"{self.base_url}/wms"
        try:
            self._wms = WebMapService(wms_url, version=self.wms_version)
            logger.info("Connected to WMS service %s (%d layers available)", wms_url, len(self._wms.contents))
            return self._wms
        except Exception:
            logger.exception("Failed to connect to WMS service at %s", wms_url)
            raise

    def list_wms_layers(self, filter_func: Optional[Callable[[str, str], bool]] = None) -> Dict[str, str]:
        """List available WMS layers from the service, optionally filtered.
        
        Arguments:
            filter_func: Optional function to filter layers. Takes layer name and title
                       as arguments and returns bool.
        
        Returns:
            Dictionary of layer names and titles
        """
        layers = {
            name: layer.title 
            for name, layer in self.wms.contents.items()
            if filter_func is None or filter_func(name, layer.title)
        }
        return layers

    def check_layer_exists(self, layer_name: str) -> bool:
        """Check if a layer exists in the WMS service.

        Arguments:
            layer_name: Name of the layer to check
            
        Returns:
            True if layer exists, False otherwise
        """
        return layer_name in self.wms.contents

    @abstractmethod
    def parse_feature_info(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        """Parse GetFeatureInfo response content.
        
        This method should be implemented by subclasses to handle
        service-specific response formats. Preferably, in these method, each data
        type (e.g., soil texture, elevation) gets its own parsing logic in a dedicated
        private method.

        Arguments:
            content: Raw response content as string
            **kwargs: Additional parsing parameters
            
        Returns:
            Parsed content in appropriate format
        """
        pass