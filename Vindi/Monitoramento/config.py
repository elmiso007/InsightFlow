import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    # Database
    DB_SERVER = os.getenv('DB_SERVER', '10.30.138.28')
    DB_NAME = os.getenv('DB_NAME', 'report_requesttracker')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')

    # Slack
    SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
    SLACK_CHANNELS = ['C0AA7PP9EKF'] # Default channel

    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Application
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Validation
    @classmethod
    def validate(cls):
        missing = []
        if not cls.DB_USER: missing.append("DB_USER")
        if not cls.DB_PASSWORD: missing.append("DB_PASSWORD")
        if not cls.SLACK_BOT_TOKEN: missing.append("SLACK_BOT_TOKEN")
        if not cls.OPENAI_API_KEY: missing.append("OPENAI_API_KEY")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
