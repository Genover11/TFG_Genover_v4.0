# src/ship_broker/core/email_parser.py
import email
import imaplib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class VesselData:
    name: str
    dwt: Optional[float] = None
    position: Optional[str] = None
    eta: Optional[datetime] = None
    open_date: Optional[datetime] = None
    vessel_type: Optional[str] = None
    description: str = ""

@dataclass
class CargoData:
    cargo_type: str
    quantity: Optional[float] = None
    load_port: Optional[str] = None
    discharge_port: Optional[str] = None
    laycan_start: Optional[datetime] = None
    laycan_end: Optional[datetime] = None
    rate: Optional[str] = None
    description: str = ""

class EmailParser:
    def __init__(self, email_address: str, password: str, imap_server: str = "imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server

    def connect(self) -> imaplib.IMAP4_SSL:
        logger.info(f"Connecting to {self.imap_server}")
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email_address, self.password)
        return mail

    def get_emails(self, days: int = 1) -> List[Dict]:
        logger.info(f"Fetching emails from last {days} days")
        mail = self.connect()
        mail.select('INBOX')
        
        # Calculate date for search
        date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        _, messages = mail.search(None, f'(SINCE "{date}")')
        
        emails_data = []
        for num in messages[0].split():
            _, msg_data = mail.fetch(num, '(RFC822)')
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            content = self._get_email_content(email_message)
            subject = email_message["subject"] or ""
            
            logger.info(f"Found email with subject: {subject}")
            emails_data.append({
                'subject': subject,
                'content': content
            })
            
        mail.close()
        mail.logout()
        return emails_data

    def _get_email_content(self, email_message) -> str:
        content = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        content += part.get_payload(decode=True).decode()
                    except:
                        logger.error("Failed to decode email part")
                        continue
        else:
            try:
                content = email_message.get_payload(decode=True).decode()
            except:
                logger.error("Failed to decode email")
                content = email_message.get_payload()
        return content

    def extract_vessels(self, text: str) -> List[VesselData]:
        logger.info("Extracting vessel information from email")
        vessels = []
        
        # Look for vessel sections
        vessel_sections = re.split(r'\n\s*\n', text)
        
        for section in vessel_sections:
            # Look for vessel name patterns
            name_match = re.search(r'(?:VESSEL|NAME|M/?V)\s*:?\s*([A-Z][A-Z\s]+)', section, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()
                logger.info(f"Found vessel: {name}")
                
                # Extract other details
                dwt_match = re.search(r'(?:DWT|DEADWEIGHT)\s*:?\s*([\d,\.]+)', section, re.IGNORECASE)
                position_match = re.search(r'(?:POSITION|PORT|LOC)\s*:?\s*([A-Z][A-Z\s]+)', section, re.IGNORECASE)
                type_match = re.search(r'(?:TYPE|VESSEL TYPE)\s*:?\s*([A-Z][A-Z\s]+)', section, re.IGNORECASE)
                
                vessel = VesselData(
                    name=name,
                    dwt=float(dwt_match.group(1).replace(',', '')) if dwt_match else None,
                    position=position_match.group(1).strip() if position_match else None,
                    vessel_type=type_match.group(1).strip() if type_match else None,
                    description=section.strip()
                )
                vessels.append(vessel)
        
        logger.info(f"Found {len(vessels)} vessels")
        return vessels

    def extract_cargoes(self, text: str) -> List[CargoData]:
        logger.info("Extracting cargo information from email")
        cargoes = []
        
        # Look for cargo sections
        cargo_sections = re.split(r'\n\s*\n', text)
        
        for section in cargo_sections:
            # Look for cargo type patterns
            type_match = re.search(r'(?:CARGO|TYPE)\s*:?\s*([A-Z][A-Z\s]+)', section, re.IGNORECASE)
            if type_match:
                cargo_type = type_match.group(1).strip()
                logger.info(f"Found cargo: {cargo_type}")
                
                # Extract other details
                quantity_match = re.search(r'(?:QTY|QUANTITY)\s*:?\s*([\d,\.]+)', section, re.IGNORECASE)
                load_match = re.search(r'(?:LOAD|LOADING)\s*:?\s*([A-Z][A-Z\s]+)', section, re.IGNORECASE)
                discharge_match = re.search(r'(?:DISCH|DISCHARGE)\s*:?\s*([A-Z][A-Z\s]+)', section, re.IGNORECASE)
                rate_match = re.search(r'(?:RATE|FREIGHT)\s*:?\s*([\d\.,]+\s*(?:USD|PMT|USD/MT))', section, re.IGNORECASE)
                
                cargo = CargoData(
                    cargo_type=cargo_type,
                    quantity=float(quantity_match.group(1).replace(',', '')) if quantity_match else None,
                    load_port=load_match.group(1).strip() if load_match else None,
                    discharge_port=discharge_match.group(1).strip() if discharge_match else None,
                    rate=rate_match.group(1).strip() if rate_match else None,
                    description=section.strip()
                )
                cargoes.append(cargo)
        
        logger.info(f"Found {len(cargoes)} cargoes")
        return cargoes