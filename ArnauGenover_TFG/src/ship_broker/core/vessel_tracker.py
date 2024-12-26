# src/ship_broker/core/vessel_tracker.py
# from VesselFinder.com

import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class VesselTracker:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "apikey": api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def get_vessels_in_port(self, port_name: str) -> List[Dict]:
        base_url = f"https://www.vesselfinder.com/ports/{port_name.replace(' ', '-')}"
        return self._scrape_port_data(base_url)

    def _scrape_port_data(self, url: str) -> List[Dict]:
        params = {"url": url}
        try:
            response = requests.get(
                'https://app.zenscrape.com/api/v1/get', 
                headers=self.headers, 
                params=params
            )
            if response.status_code == 200:
                return self._extract_vessel_data(response.text)
            logger.error(f"Failed to fetch data: {response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error scraping port data: {str(e)}")
            return []

    def _extract_vessel_data(self, html_content: str) -> List[Dict]:
        soup = BeautifulSoup(html_content, 'html.parser')
        vessels = []
        
        for vessel_div in soup.find_all('div', {'class': 'ship-list-row'}):
            try:
                vessel_data = {
                    'name': self._get_text(vessel_div, 'a', 'ship-name'),
                    'type': self._get_text(vessel_div, 'div', 'ship-type'),
                    'dwt': self._parse_dwt(self._get_text(vessel_div, 'div', 'ship-details')),
                    'position': self._get_text(vessel_div, 'span', 'ship-position'),
                    'eta': self._parse_eta(self._get_text(vessel_div, 'div', 'ship-eta')),
                    'last_updated': datetime.now()
                }
                vessels.append(vessel_data)
            except Exception as e:
                logger.error(f"Error extracting vessel data: {str(e)}")
                continue
        
        return vessels

    @staticmethod
    def _get_text(element, tag, class_name) -> str:
        found = element.find(tag, {'class': class_name})
        return found.get_text(strip=True) if found else ""

    @staticmethod
    def _parse_dwt(details: str) -> Optional[float]:
        try:
            if 'DWT' in details:
                dwt_str = details.split('DWT')[0].strip().replace(',', '')
                return float(dwt_str)
            return None
        except:
            return None

    @staticmethod
    def _parse_eta(eta_str: str) -> Optional[datetime]:
        try:
            return datetime.strptime(eta_str, '%Y-%m-%d %H:%M')
        except:
            return None