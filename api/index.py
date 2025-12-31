import os
import sys

# Add the parent directory to sys.path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.app import app

# Vercel expects a variable named 'app'
# This file serves as the entrypoint for Vercel Serverless Functions
