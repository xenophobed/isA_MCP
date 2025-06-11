# app/tools/tracking.py

from langchain_core.tools import tool
from langchain.schema import Document
from .....utils.token_manager import APIClient
from app.config.config_manager import config_manager

logger = config_manager.get_logger(__name__)

@tool 
def fetch_track(order_id: str) -> list:
    """
    Fetch the order tracking details.
    
    Args:
        order_id: The order ID to track
        
    Returns:
        List containing tracking information or empty list if no valid tracking found
    """
    logger.debug(f"Fetch tool called with order_id: {order_id}")
    
    # Get tracking config
    party_config = config_manager.get_config('party')
    tp_settings = party_config.get_tp_settings()
    
    # Validate order number format
    if not order_id or len(order_id) < 5:  # Assuming valid order numbers are at least 5 digits
        logger.warning(f"Invalid order number format: {order_id}")
        return []
        
    # Create API client
    api_client = APIClient()
    
    # Define request parameters
    params = {
        "no": order_id
    }
    api_url = f"{tp_settings['endpoint']}/queryTracks"
    logger.debug(f"Making request to: {api_url}")
    
    try:
        # Make API request
        response = api_client.make_request(api_url, params=params)
        logger.debug(f"API Response status: {response.status_code}")
        
        response_data = response.json()
        events = response_data.get("data", [])
        
        if not events or not events[0].get('trackList'):
            logger.info(f"No valid tracking information found for order: {order_id}")
            return []

        track_list = events[0]['trackList']

        # Format tracking content
        track_content = (
            f"Order ID: {order_id}\n" + 
            "\n".join(
                f"Desc: {track['desc']}, Location: {track['localtion']}, Time: {track['time']}"
                for track in track_list
            )
        )
        
        return [Document(page_content=track_content)]
        
    except Exception as e:
        logger.error(f"Error fetching tracking info: {str(e)}", exc_info=True)
        return []
    
