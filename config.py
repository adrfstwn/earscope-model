import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration settings"""
    # Server settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))

    APP_KEY = os.getenv('APP_KEY', '')
    API_VIDEO_URL = os.getenv('API_VIDEO_URL', '')
