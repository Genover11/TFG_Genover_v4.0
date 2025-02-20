# src/ship_broker/core/cargo_tracker.py


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

class CargoTracker:
    def __init__(self):
        self.setup_driver()

    def setup_driver(self):
        """Setup Chrome driver with headless mode"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in headless mode
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Hide automation
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set window size
            self.driver.set_window_size(1920, 1080)
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            self.driver = None

    def get_cargoes_for_vessel(self, vessel_data: Dict) -> List[Dict]:
        """Find available cargoes suitable for a specific vessel"""
        try:
            if not self.driver:
                logger.warning("No web driver available - returning mock cargo data")
                return self._get_mock_data(vessel_data)

            logger.info(f"Searching for cargoes suitable for vessel at {vessel_data.get('position', 'Unknown')}")

            # Updated URL for cargoes
            search_url = "https://shipnext.com/cargoes/all"  # More likely to contain real cargo data
            self.driver.get(search_url)
            time.sleep(5)  # Wait for page to load

            # Find cargo listings
            try:
                cargo_elements = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "cargo-card"))  # Updated class name
                )
                
                cargoes = []
                for element in cargo_elements:
                    try:
                        cargo_data = {
                            'cargo_type': element.find_element(By.CSS_SELECTOR, '.cargo-name').text.strip(),
                            'quantity': self._parse_quantity(
                                element.find_element(By.CSS_SELECTOR, '.cargo-quantity').text
                            ),
                            'load_port': element.find_element(By.CSS_SELECTOR, '.loading-port').text.strip(),
                            'discharge_port': element.find_element(By.CSS_SELECTOR, '.discharge-port').text.strip(),
                            'laycan_start': self._parse_date(
                                element.find_element(By.CSS_SELECTOR, '.laycan').text.split('-')[0]
                            ),
                            'laycan_end': self._parse_date(
                                element.find_element(By.CSS_SELECTOR, '.laycan').text.split('-')[1]
                            ),
                            'description': element.find_element(By.CSS_SELECTOR, '.cargo-description').text.strip(),
                            'is_mock': False  # Flag to indicate real data
                        }
                        if self._is_cargo_suitable(cargo_data, vessel_data):
                            cargoes.append(cargo_data)
                    except NoSuchElementException as e:
                        logger.debug(f"Missing element in cargo card: {str(e)}")
                        continue
                    except Exception as e:
                        logger.error(f"Error extracting cargo data: {str(e)}")
                        continue

                if cargoes:
                    return cargoes
                
                logger.warning("No suitable cargoes found - returning mock data")
                return self._get_mock_data(vessel_data)

            except TimeoutException:
                logger.warning("Web scraping failed (timeout) - returning mock cargo data for demonstration purposes")
                return self._get_mock_data(vessel_data)

        except Exception as e:
            logger.error(f"Error fetching cargoes: {str(e)}")
            return self._get_mock_data(vessel_data)

        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass


    def _is_cargo_suitable(self, cargo: Dict, vessel: Dict) -> bool:
        """Check if cargo is suitable for vessel based on capacity and position"""
        try:
            vessel_dwt = vessel.get('dwt', 0)
            cargo_quantity = cargo.get('quantity', 0)
            
            if not vessel_dwt or not cargo_quantity:
                return False
            
            # Basic size compatibility check
            if cargo_quantity > vessel_dwt:
                return False
                
            if cargo_quantity < vessel_dwt * 0.3:  # Too small for vessel
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking cargo suitability: {str(e)}")
            return False

    def _parse_quantity(self, text: str) -> Optional[float]:
        """Parse quantity value from text"""
        try:
            import re
            quantity_match = re.search(r'(\d+(?:,\d+)?)\s*(?:MT|KMT|K|TONS?)', text)
            if quantity_match:
                return float(quantity_match.group(1).replace(',', ''))
            return None
        except Exception:
            return None

    def _parse_date(self, date_text: str) -> Optional[str]:
        """Parse date from text to ISO format"""
        try:
            return datetime.strptime(date_text.strip(), '%Y-%m-%d').isoformat()
        except Exception:
            return None


    def _get_mock_data(self, vessel_data: Dict) -> List[Dict]:
        """Return mock data when scraping fails"""
        vessel_dwt = vessel_data.get('dwt', 50000)
        return [
            {
                'cargo_type': '[MOCK] GRAIN',
                'quantity': vessel_dwt * 0.8,
                'load_port': vessel_data.get('position', 'SINGAPORE'),
                'discharge_port': 'ROTTERDAM',
                'laycan_start': datetime.now().isoformat(),
                'laycan_end': datetime.now().isoformat(),
                'description': '[MOCK DATA] Sample grain cargo',
                'is_mock': True
            },
            {
                'cargo_type': '[MOCK] COAL',
                'quantity': vessel_dwt * 0.9,
                'load_port': 'NEWCASTLE',
                'discharge_port': 'QINGDAO',
                'laycan_start': datetime.now().isoformat(),
                'laycan_end': datetime.now().isoformat(),
                'description': '[MOCK DATA] Sample coal cargo',
                'is_mock': True
            }
        ]
    