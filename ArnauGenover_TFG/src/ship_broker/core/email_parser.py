import email
import imaplib
import re
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from email.header import decode_header
import os
from dataclasses import dataclass
import spacy
import json

@dataclass
class Vessel:
    name: str
    dwt: Optional[float]
    position: Optional[str]
    eta: Optional[datetime]
    open_date: Optional[datetime]
    vessel_type: Optional[str]
    description: str

@dataclass
class Cargo:
    cargo_type: str
    quantity: Optional[float]
    load_port: Optional[str]
    discharge_port: Optional[str]
    laycan: Optional[tuple]
    rate: Optional[str]
    description: str

class EmailParser:
    def __init__(self, email_address: str, password: str, imap_server: str = "imap.gmail.com"):
        """Initialize the email parser with credentials."""
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        # Load spaCy model for NER
        self.nlp = spacy.load("en_core_web_sm")
        
        # Common vessel type patterns
        self.vessel_types = [
            "bulk carrier", "bulker", "tanker", "container ship", "cargo vessel",
            "lng", "lpg", "roro", "panamax", "supramax", "handysize"
        ]
        
    def connect(self) -> imaplib.IMAP4_SSL:
        """Establish connection to email server."""
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email_address, self.password)
        return mail

    def get_emails(self, folder: str = "INBOX", days: int = 7) -> List[Dict]:
        """Retrieve emails from specified folder within last n days."""
        mail = self.connect()
        mail.select(folder)
        
        # Search for recent emails
        date_criterion = f'(SINCE "{(datetime.now() - pd.Timedelta(days=days)).strftime("%d-%b-%Y")}")'
        _, messages = mail.search(None, date_criterion)
        
        emails_data = []
        for num in messages[0].split():
            _, msg_data = mail.fetch(num, '(RFC822)')
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            subject = self._decode_email_header(email_message["subject"])
            sender = self._decode_email_header(email_message["from"])
            date = email_message["date"]
            
            content = self._get_email_content(email_message)
            
            emails_data.append({
                "subject": subject,
                "sender": sender,
                "date": date,
                "content": content
            })
            
        mail.close()
        mail.logout()
        return emails_data

    def _decode_email_header(self, header: str) -> str:
        """Decode email header to readable format."""
        if header is None:
            return ""
        decoded_parts = decode_header(header)
        return " ".join(
            part.decode(encoding) if isinstance(part, bytes) else part
            for part, encoding in decoded_parts
        )

    def _get_email_content(self, email_message) -> str:
        """Extract email content, handling multiple parts and encodings."""
        content = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        content += part.get_payload(decode=True).decode()
                    except:
                        continue
        else:
            try:
                content = email_message.get_payload(decode=True).decode()
            except:
                content = email_message.get_payload()
        return content

    def extract_vessels(self, text: str) -> List[Vessel]:
        """Extract vessel information from text."""
        vessels = []
        # Split text into paragraphs
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            # Skip if paragraph is too short
            if len(paragraph) < 10:
                continue
                
            # Use spaCy for named entity recognition
            doc = self.nlp(paragraph)
            
            # Look for vessel type mentions
            vessel_type = None
            for v_type in self.vessel_types:
                if v_type in paragraph.lower():
                    vessel_type = v_type
                    break
            
            # Extract potential vessel names (usually in caps)
            vessel_names = re.findall(r'[A-Z]{2,}(?:\s+[A-Z]+)*', paragraph)
            
            # Extract DWT (Dead Weight Tonnage)
            dwt_match = re.search(r'(\d{2,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:DWT|dwt)', paragraph)
            dwt = float(dwt_match.group(1).replace(',', '')) if dwt_match else None
            
            # Extract dates
            dates = self._extract_dates(paragraph)
            
            # Extract position
            position = None
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC"]:
                    position = ent.text
                    break
            
            if vessel_names:
                vessels.append(Vessel(
                    name=vessel_names[0],
                    dwt=dwt,
                    position=position,
                    eta=dates.get('eta'),
                    open_date=dates.get('open_date'),
                    vessel_type=vessel_type,
                    description=paragraph
                ))
                
        return vessels

    def extract_cargoes(self, text: str) -> List[Cargo]:
        """Extract cargo information from text."""
        cargoes = []
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(paragraph) < 10:
                continue
                
            doc = self.nlp(paragraph)
            
            # Extract cargo type and quantity
            quantity_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(MT|KT|tons?|tonnes?)', 
                                    paragraph, re.IGNORECASE)
            quantity = float(quantity_match.group(1).replace(',', '')) if quantity_match else None
            
            # Extract ports
            ports = []
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC"]:
                    ports.append(ent.text)
            
            # Extract laycan (laydays cancelling) dates
            dates = self._extract_dates(paragraph)
            laycan = (dates.get('start_date'), dates.get('end_date')) if dates else None
            
            # Extract rate information
            rate_match = re.search(r'\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*USD', paragraph)
            rate = rate_match.group(1) if rate_match else None
            
            if quantity or (len(ports) >= 2):
                cargoes.append(Cargo(
                    cargo_type=self._identify_cargo_type(paragraph),
                    quantity=quantity,
                    load_port=ports[0] if ports else None,
                    discharge_port=ports[1] if len(ports) > 1 else None,
                    laycan=laycan,
                    rate=rate,
                    description=paragraph
                ))
                
        return cargoes

    def _extract_dates(self, text: str) -> Dict:
        """Extract various types of dates from text."""
        # Common date patterns in broker emails
        date_patterns = [
            r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        dates = {}
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)
                try:
                    date = pd.to_datetime(date_str)
                    # Classify date based on context
                    context = text[max(0, match.start() - 20):min(len(text), match.end() + 20)]
                    if any(word in context.lower() for word in ['eta', 'arrival', 'arriving']):
                        dates['eta'] = date
                    elif any(word in context.lower() for word in ['open', 'available']):
                        dates['open_date'] = date
                    elif any(word in context.lower() for word in ['laycan', 'start']):
                        dates['start_date'] = date
                    elif any(word in context.lower() for word in ['cancel', 'end']):
                        dates['end_date'] = date
                except:
                    continue
                    
        return dates

    def _identify_cargo_type(self, text: str) -> str:
        """Identify type of cargo from text description."""
        common_cargos = {
            'grain': ['wheat', 'corn', 'soybean', 'grain', 'barley'],
            'coal': ['coal', 'petcoke'],
            'ore': ['iron ore', 'bauxite', 'manganese'],
            'steel': ['steel', 'plates', 'coils'],
            'fertilizer': ['fertilizer', 'urea', 'phosphate'],
            'oil': ['crude', 'petroleum', 'diesel', 'gasoline'],
        }
        
        text_lower = text.lower()
        for cargo_type, keywords in common_cargos.items():
            if any(keyword in text_lower for keyword in keywords):
                return cargo_type
        return 'general cargo'

    def save_to_database(self, vessels: List[Vessel], cargoes: List[Cargo], 
                        filename: str = 'shipping_data.json'):
        """Save extracted data to a JSON database."""
        data = {
            'vessels': [vars(v) for v in vessels],
            'cargoes': [vars(c) for c in cargoes],
            'timestamp': datetime.now().isoformat()
        }
        
        # Convert datetime objects to strings
        for vessel in data['vessels']:
            for key, value in vessel.items():
                if isinstance(value, datetime):
                    vessel[key] = value.isoformat()
                    
        for cargo in data['cargoes']:
            if cargo['laycan']:
                cargo['laycan'] = tuple(d.isoformat() if d else None for d in cargo['laycan'])
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    # Configuration
    EMAIL_ADDRESS = "your_email@example.com"
    EMAIL_PASSWORD = "your_password"
    IMAP_SERVER = "imap.gmail.com"
    
    # Initialize parser
    parser = EmailParser(EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER)
    
    try:
        # Get recent emails
        emails = parser.get_emails(days=7)
        
        all_vessels = []
        all_cargoes = []
        
        # Process each email
        for email_data in emails:
            content = email_data['content']
            
            # Extract vessels and cargoes
            vessels = parser.extract_vessels(content)
            cargoes = parser.extract_cargoes(content)
            
            all_vessels.extend(vessels)
            all_cargoes.extend(cargoes)
            
        # Save results
        parser.save_to_database(all_vessels, all_cargoes)
        
        print(f"Successfully processed {len(emails)} emails")
        print(f"Found {len(all_vessels)} vessels and {len(all_cargoes)} cargoes")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    main()