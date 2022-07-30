#!/usr/bin/env python3

import json, requests, os, shutil
from requests.adapters import HTTPAdapter
from urllib3 import Retry

# API Request strategy
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],
    backoff_factor=10
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

# Set current directory
#os.chdir(os.path.dirname(sys.argv[0]))
os.chdir(os.getcwd())

from dotenv import load_dotenv

load_dotenv()

# Retrieve contents from .env file
AUTH_CODE = os.getenv("AUTH_CODE")

# Blackbaud Token URL
url = 'https://oauth2.sky.blackbaud.com/token'

def access_token():
    # Retrieve access_token from file
    with open('access_token_output.json') as access_token_output:
      data = json.load(access_token_output)
      access_token = data["access_token"]
    return access_token

og_file = "access_token_output.json"
bak_file = "access_token_output.json.bak"

# Check if the output is empty
if access_token() == "":
    shutil.copyfile(bak_file, og_file)

# Take Backup
shutil.copyfile(og_file, bak_file)

# Retrieve refresh_token from file
with open('access_token_output.json') as access_token_output:
  data = json.load(access_token_output)
  refresh_token = data["refresh_token"]

# Request Headers for Blackbaud API request
headers = {
    # Request headers
    'Content-Type': 'application/x-www-form-urlencoded',
    'Authorization': 'Basic ' + AUTH_CODE
}

# Request parameters for Blackbaud API request
data = {
    'grant_type': 'refresh_token',
    'refresh_token': refresh_token
}

# API Request
response = http.post(url, data=data, headers=headers).json()

# Write output to JSON file
with open("access_token_output.json", "w") as response_output:
    json.dump(response, response_output, ensure_ascii=False, sort_keys=True, indent=4)

# Check if the output is empty
if access_token() == "":
    shutil.copyfile(bak_file, og_file)