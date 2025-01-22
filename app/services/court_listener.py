import requests
from datetime import datetime
import logging
import json
import os
from flask import current_app
from urllib.parse import quote

class CourtListenerService:
    def __init__(self):
        self.cache_file = 'data/cache.json'
        self.cases_file = 'data/cases.json'
        self._ensure_data_directory()
        self.cache = self._load_cache()
        self.cases = self._load_cases()
        self.base_url = current_app.config['COURTLISTENER_BASE_URL']

    def _ensure_data_directory(self):
        os.makedirs('data', exist_ok=True)

    def _load_cache(self):
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def _load_cases(self):
        try:
            with open(self.cases_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_cases(self):
        with open(self.cases_file, 'w') as f:
            json.dump(self.cases, f, indent=2)

    def _get_headers(self):
        api_key = current_app.config['COURTLISTENER_API_KEY']
        if not api_key:
            raise ValueError("CourtListener API key not found in configuration")
        
        headers = {
            'Authorization': f'Token {api_key}',
            'Content-Type': 'application/json',
        }
        print(f"Using headers: {headers}")
        return headers

    def get_cases(self):
        return self.cases

    def _check_docket_for_entities(self, docket):
        """Check if docket is related to any tracked entities"""
        found_entities = []
        
        for entity_id, entity in current_app.config['TRACKED_ENTITIES'].items():
            if self._check_docket_for_entity(docket, entity):
                found_entities.append(entity_id)
                
        return found_entities

    def _check_docket_for_entity(self, docket, entity):
        """Check if docket is related to a specific entity"""
        # Check case name against all keywords
        case_name = docket['case_name'].lower()
        if any(keyword.lower() in case_name for keyword in entity['keywords']):
            print(f"Found {entity['name']} in case name: {docket['case_name']}")
            return True
            
        # Check case name variations if available
        for name_field in ['case_name_short', 'case_name_full']:
            if docket.get(name_field):
                if any(keyword.lower() in docket[name_field].lower() for keyword in entity['keywords']):
                    print(f"Found {entity['name']} in {name_field}: {docket[name_field]}")
                    return True
        
        # For government entities, do additional checks
        if entity.get('gov_entity'):
            if docket.get('jurisdiction_type') and 'U.S. Government' in docket['jurisdiction_type']:
                # Check cause of action
                if docket.get('cause'):
                    cause = docket['cause'].lower()
                    if any(term in cause for term in ['administrative', 'agency', 'government']):
                        print(f"Potential {entity['name']} case - Government jurisdiction with cause: {docket['cause']}")
                        return True
                
                # Check nature of suit
                if docket.get('nature_of_suit'):
                    suit = docket['nature_of_suit'].lower()
                    if any(term in suit for term in ['administrative', 'agency action', 'government']):
                        print(f"Potential {entity['name']} case - Government jurisdiction with nature of suit: {docket['nature_of_suit']}")
                        return True
        
        return False

    def refresh_cases(self):
        try:
            print("Fetching dockets...")
            dockets = self._fetch_dockets()
            new_cases = []
            
            for docket in dockets:
                docket_id = str(docket['id'])
                
                # Skip if we've already checked this docket and found no entities
                if docket_id in self.cache and not self.cache[docket_id]['entities']:
                    print(f"Skipping known non-matching docket {docket_id}")
                    continue
                
                # Skip if we've already processed this docket and found entities
                if docket_id in self.cache and self.cache[docket_id]['entities']:
                    print(f"Found cached docket {docket_id} with entities: {self.cache[docket_id]['entities']}")
                    new_cases.append(self.cache[docket_id]['case_data'])
                    continue

                print(f"Checking new docket {docket_id}")
                found_entities = self._check_docket_for_entities(docket)
                
                case_data = {
                    'id': docket_id,
                    'case_name': docket['case_name'],
                    'docket_number': docket['docket_number'],
                    'court': docket['court_id'],
                    'filing_date': docket['date_filed'],
                    'url': f"https://www.courtlistener.com{docket['absolute_url']}",
                    'jurisdiction': docket.get('jurisdiction_type', ''),
                    'nature_of_suit': docket.get('nature_of_suit', ''),
                    'cause': docket.get('cause', ''),
                    'entities': found_entities
                }
                
                # Cache the result immediately
                self.cache[docket_id] = {
                    'entities': found_entities,
                    'case_data': case_data,
                    'last_checked': datetime.now().isoformat()
                }
                self._save_cache()  # Save cache after each docket check
                
                if found_entities:
                    new_cases.append(case_data)
                    # Save cases immediately when we find matching entities
                    self.cases = new_cases
                    self._save_cases()
            
            # Final update of cases list
            self.cases = new_cases
            self._save_cases()
            print(f"Refresh complete. Found {len(new_cases)} matching cases.")
            
        except Exception as e:
            logging.error(f"Error refreshing cases: {str(e)}")
            raise

    def _fetch_dockets(self):
        try:
            date_param = quote(current_app.config['CASE_START_DATE'])
            url = f"{self.base_url}/dockets/?date_filed__gte={date_param}&party_name=Department of Government Efficiency"
            print(f"Fetching dockets with URL: {url}")
            
            response = requests.get(
                url,
                headers=self._get_headers()
            )
            response.raise_for_status()
            data = response.json()
            print(f"Got {len(data['results'])} dockets")
            return data['results']
        except requests.exceptions.RequestException as e:
            print(f"Error in _fetch_dockets: {str(e)}")
            print(f"Response content: {e.response.content if hasattr(e, 'response') else 'No response'}")
            raise

    def _fetch_parties(self, docket_id):
        try:
            url = f"{self.base_url}/parties/?docket={docket_id}/"
            print(f"Fetching parties with URL: {url}")
            
            response = requests.get(
                url,
                headers=self._get_headers()
            )
            response.raise_for_status()
            data = response.json()
            print(f"Got {len(data['results']) if 'results' in data else 1} parties")
            return [data] if 'results' not in data else data['results']
        except requests.exceptions.RequestException as e:
            print(f"Error in _fetch_parties: {str(e)}")
            print(f"Response content: {e.response.content if hasattr(e, 'response') else 'No response'}")
            raise

    def _is_doge_party(self, parties):
        search_term = current_app.config['PARTY_NAME'].lower()
        for party in parties:
            if search_term in party['name'].lower():
                print(f"Found DOGE in party: {party['name']}")
                return True
        return False 