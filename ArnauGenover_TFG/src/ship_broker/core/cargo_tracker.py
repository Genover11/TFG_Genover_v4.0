# src/ship_broker/core/cargo_tracker.py
# from shipnext.com 

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CargoTracker:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def get_cargoes_for_vessel(self, vessel_data: Dict) -> List[Dict]:
        """Find available cargoes suitable for a specific vessel"""
        try:
            # Construct search URL based on vessel position
            base_url = f"https://shipnext.com/cargo-search"
            params = {
                'loading_port': vessel_data.get('position', ''),
                'vessel_type': vessel_data.get('type', ''),
                'dwt_min': max(0, int(vessel_data.get('dwt', 0) * 0.8)),  # 80% of vessel DWT
                'dwt_max': int(vessel_data.get('dwt', 0))
            }

            return self._scrape_cargo_data(base_url, params)
        except Exception as e:
            logger.error(f"Error fetching cargoes: {str(e)}")
            return []

    def _scrape_cargo_data(self, url: str, params: Dict) -> List[Dict]:
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                return self._extract_cargo_listings(response.text)
            logger.error(f"Failed to fetch data: {response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error scraping cargo data: {str(e)}")
            return []

    def _extract_cargo_listings(self, html_content: str) -> List[Dict]:
        soup = BeautifulSoup(html_content, 'html.parser')
        cargoes = []

        # Adjust these selectors based on ShipNext's actual HTML structure
        for cargo_div in soup.find_all('div', {'class': 'cargo-listing'}):
            try:
                cargo_data = {
                    'cargo_type': self._get_text(cargo_div, 'div', 'cargo-type'),
                    'quantity': self._parse_quantity(self._get_text(cargo_div, 'div', 'cargo-quantity')),
                    'load_port': self._get_text(cargo_div, 'div', 'loading-port'),
                    'discharge_port': self._get_text(cargo_div, 'div', 'discharge-port'),
                    'laycan_start': self._parse_date(self._get_text(cargo_div, 'div', 'laycan-start')),
                    'laycan_end': self._parse_date(self._get_text(cargo_div, 'div', 'laycan-end')),
                    'details': self._get_text(cargo_div, 'div', 'cargo-details'),
                    'last_updated': datetime.now()
                }
                cargoes.append(cargo_data)
            except Exception as e:
                logger.error(f"Error extracting cargo listing: {str(e)}")
                continue

        return cargoes

    @staticmethod
    def _get_text(element, tag, class_name) -> str:
        found = element.find(tag, {'class': class_name})
        return found.get_text(strip=True) if found else ""

    @staticmethod
    def _parse_quantity(quantity_str: str) -> float:
        try:
            return float(quantity_str.split()[0].replace(',', ''))
        except:
            return 0.0

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return None