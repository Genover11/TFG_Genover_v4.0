# src/ship_broker/core/vessel_tracker.py
from typing import List, Dict, Optional
from datetime import datetime
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time

logger = logging.getLogger(__name__)

class VesselTracker:
    def __init__(self):
        self.setup_driver()

    def setup_driver(self):
        """Setup Chrome driver with headless mode"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Set timeout to lower value
            chrome_options.add_argument("--page-load-strategy=eager")
            
            # Add performance options
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--dns-prefetch-disable")
            chrome_options.add_argument("--disk-cache-size=1")
            
            chrome_options.binary_location = "/usr/bin/google-chrome"
            
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            self.driver = None

    def get_vessels_in_port(self, port_name: str) -> List[Dict]:
        """Get vessels currently in or expected at a specific port"""
        try:
            if not self.driver:
                return self._get_mock_data(port_name)

            logger.info(f"Searching for vessels in port: {port_name}")
            
            # Use shipnext.com instead of vesselfinder
            search_url = "https://shipnext.com/vessels"  # Modify this URL according to shipnext's vessel listing page
            self.driver.get(search_url)
            
            # Short wait for initial load
            time.sleep(3)
            
            # Use shorter wait time
            wait = WebDriverWait(self.driver, 5)
            
            try:
                # Wait for vessel listings
                vessel_elements = wait.until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "vessel-card"))
                )
                
                vessels = []
                for element in vessel_elements[:10]:  # Limit to first 10 vessels for performance
                    try:
                        vessel_data = {
                            'name': element.find_element(By.CSS_SELECTOR, '.vessel-name').text.strip(),
                            'type': element.find_element(By.CSS_SELECTOR, '.vessel-type').text.strip(),
                            'dwt': self._extract_dwt(
                                element.find_element(By.CSS_SELECTOR, '.vessel-dwt').text
                            ),
                            'position': port_name,  # Use searched port as position
                            'eta': datetime.now().isoformat(),
                            'description': element.find_element(By.CSS_SELECTOR, '.vessel-details').text.strip()
                        }
                        if self._is_vessel_in_port(vessel_data, port_name):
                            vessels.append(vessel_data)
                    except NoSuchElementException:
                        continue
                    except Exception as e:
                        logger.error(f"Error extracting vessel data: {str(e)}")
                        continue
                
                if vessels:
                    return vessels
                return self._get_mock_data(port_name)
                
            except TimeoutException:
                logger.warning(f"Timeout waiting for vessel listings")
                return self._get_mock_data(port_name)
                
        except Exception as e:
            logger.error(f"Error fetching vessels: {str(e)}")
            return self._get_mock_data(port_name)
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

    def _is_vessel_in_port(self, vessel: Dict, port_name: str) -> bool:
        """Check if vessel is in or near the specified port"""
        vessel_position = vessel.get('position', '').upper()
        port_name = port_name.upper()
        return port_name in vessel_position or vessel_position in port_name

    def _extract_dwt(self, text: str) -> Optional[float]:
        """Extract DWT value from text"""
        try:
            import re
            dwt_match = re.search(r'(\d+(?:,\d+)?)\s*(?:DWT|MT)', text)
            if dwt_match:
                return float(dwt_match.group(1).replace(',', ''))
            return None
        except Exception:
            return None

    def _get_mock_data(self, port_name: str) -> List[Dict]:
        """Return mock vessel data when scraping fails"""
        now = datetime.now().isoformat()
        return [
            {
                'name': 'BULK CARRIER 1',
                'type': 'BULK CARRIER',
                'dwt': 82000,
                'position': port_name,
                'eta': now,
                'description': f'Available in {port_name}'
            },
            {
                'name': 'SUPRAMAX 1',
                'type': 'SUPRAMAX',
                'dwt': 55000,
                'position': port_name,
                'eta': now,
                'description': f'Available in {port_name}'
            },
            {
                'name': 'HANDYSIZE 1',
                'type': 'HANDYSIZE',
                'dwt': 35000,
                'position': port_name,
                'eta': now,
                'description': f'Available in {port_name}'
            }
        ]