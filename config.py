import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
    
    # CourtListener API
    COURTLISTENER_API_KEY = os.getenv('COURTLISTENER_API_KEY')
    if not COURTLISTENER_API_KEY:
        raise ValueError("COURTLISTENER_API_KEY environment variable is not set")
    COURTLISTENER_BASE_URL = 'https://www.courtlistener.com/api/rest/v4'
    
    # Case search parameters
    CASE_START_DATE = os.getenv('CASE_START_DATE', "2025-01-18")
    PARTY_NAME = os.getenv('PARTY_NAME', 'Department of Government Efficiency')
    
    # Webhook settings
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', os.urandom(32).hex())
    ALLOWED_IPS = ['34.210.230.218', '54.189.59.91']
    
    # Flask environment
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    
    # Scheduler
    SCHEDULER_API_ENABLED = True 