#!/usr/bin/env python3

import requests, os, json, glob, csv, psycopg2, sys, smtplib, ssl, imaplib, time, email, re, fuzzywuzzy, itertools, geopy, datetime, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from jinja2 import Environment
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3 import Retry

# Printing the output to file for debugging
sys.stdout = open('Process.log', 'w')

# API Request strategy
print("Setting API Request strategy")
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
print("Setting current directory")
os.chdir(os.getcwd())

from dotenv import load_dotenv

load_dotenv()

# Retrieve contents from .env file
DB_IP = os.getenv("DB_IP")
DB_NAME = os.getenv("DB_NAME")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
RE_API_KEY = os.getenv("RE_API_KEY")
MAIL_USERN = os.getenv("MAIL_USERN")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
IMAP_URL = os.getenv("IMAP_URL")
IMAP_PORT = os.getenv("IMAP_PORT")
SMTP_URL = os.getenv("SMTP_URL")
SMTP_PORT = os.getenv("SMTP_PORT")
SEND_TO  = os.getenv("SEND_TO")

# PostgreSQL DB Connection
conn = psycopg2.connect(host=DB_IP, dbname=DB_NAME, user=DB_USERNAME, password=DB_PASSWORD)

# Open connection
print("Creating connection with SQL database")
cur = conn.cursor()

# Retrieve access_token from file
print("Retrieve token from API connections")
with open('access_token_output.json') as access_token_output:
  data = json.load(access_token_output)
  access_token = data["access_token"]

def get_request_re():
    print("Running GET Request from RE function")
    time.sleep(5)
    # Request Headers for Blackbaud API request
    headers = {
    # Request headers
    'Bb-Api-Subscription-Key': RE_API_KEY,
    'Authorization': 'Bearer ' + access_token,
    }
    
    global re_api_response
    re_api_response = http.get(url, params=params, headers=headers).json()
    
    check_for_errors()
    print_json(re_api_response)
    
def check_for_errors():
    print("Checking for errors")
    error_keywords = ["invalid", "error", "bad", "Unauthorized", "Forbidden", "Not Found", "Unsupported Media Type", "Too Many Requests", "Internal Server Error", "Service Unavailable", "Unexpected", "error_code", "400"]
    
    if any(x in re_api_response for x in error_keywords):
        # Send emails
        print ("Will send email now")
        send_error_emails()
        
def send_error_emails():
    print("Sending email for an error")
    
    # Close writing to Process.log
    sys.stdout.close()
    
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = MAIL_USERN
    message["To"] = SEND_TO

    # Adding Reply-to header
    message.add_header('reply-to', MAIL_USERN)
        
    TEMPLATE="""
    <table style="background-color: #ffffff; border-color: #ffffff; width: auto; margin-left: auto; margin-right: auto;">
    <tbody>
    <tr style="height: 127px;">
    <td style="background-color: #363636; width: 100%; text-align: center; vertical-align: middle; height: 127px;">&nbsp;
    <h1><span style="color: #ffffff;">&nbsp;Raiser's Edge Automation: {{job_name}} Failed</span>&nbsp;</h1>
    </td>
    </tr>
    <tr style="height: 18px;">
    <td style="height: 18px; background-color: #ffffff; border-color: #ffffff;">&nbsp;</td>
    </tr>
    <tr style="height: 18px;">
    <td style="width: 100%; height: 18px; background-color: #ffffff; border-color: #ffffff; text-align: center; vertical-align: middle;">&nbsp;<span style="color: #455362;">This is to notify you that execution of Auto-updating Alumni records has failed.</span>&nbsp;</td>
    </tr>
    <tr style="height: 18px;">
    <td style="height: 18px; background-color: #ffffff; border-color: #ffffff;">&nbsp;</td>
    </tr>
    <tr style="height: 61px;">
    <td style="width: 100%; background-color: #2f2f2f; height: 61px; text-align: center; vertical-align: middle;">
    <h2><span style="color: #ffffff;">Job details:</span></h2>
    </td>
    </tr>
    <tr style="height: 52px;">
    <td style="height: 52px;">
    <table style="background-color: #2f2f2f; width: 100%; margin-left: auto; margin-right: auto; height: 42px;">
    <tbody>
    <tr>
    <td style="width: 50%; text-align: center; vertical-align: middle;">&nbsp;<span style="color: #ffffff;">Job :</span>&nbsp;</td>
    <td style="background-color: #ff8e2d; width: 50%; text-align: center; vertical-align: middle;">&nbsp;{{job_name}}&nbsp;</td>
    </tr>
    <tr>
    <td style="width: 50%; text-align: center; vertical-align: middle;">&nbsp;<span style="color: #ffffff;">Failed on :</span>&nbsp;</td>
    <td style="background-color: #ff8e2d; width: 50%; text-align: center; vertical-align: middle;">&nbsp;{{current_time}}&nbsp;</td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    <tr style="height: 18px;">
    <td style="height: 18px; background-color: #ffffff;">&nbsp;</td>
    </tr>
    <tr style="height: 18px;">
    <td style="height: 18px; width: 100%; background-color: #ffffff; text-align: center; vertical-align: middle;">Below is the detailed error log,</td>
    </tr>
    <tr style="height: 217.34375px;">
    <td style="height: 217.34375px; background-color: #f8f9f9; width: 100%; text-align: left; vertical-align: middle;">{{error_log_message}}</td>
    </tr>
    </tbody>
    </table>
    """
    
    # Create a text/html message from a rendered template
    emailbody = MIMEText(
        Environment().from_string(TEMPLATE).render(
            job_name = "Syncing Raisers Edge and AlmaBase",
            current_time=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            error_log_message = Argument
        ), "html"
    )
    
    # Add HTML parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(emailbody)
    attach_file_to_email(message, 'Process.log')
    emailcontent = message.as_string()
    
    # Create secure connection with server and send email
    context = ssl._create_unverified_context()
    with smtplib.SMTP_SSL(SMTP_URL, SMTP_PORT, context=context) as server:
        server.login(MAIL_USERN, MAIL_PASSWORD)
        server.sendmail(
            MAIL_USERN, SEND_TO, emailcontent
        )

    # Save copy of the sent email to sent items folder
    with imaplib.IMAP4_SSL(IMAP_URL, IMAP_PORT) as imap:
        imap.login(MAIL_USERN, MAIL_PASSWORD)
        imap.append('Sent', '\\Seen', imaplib.Time2Internaldate(time.time()), emailcontent.encode('utf8'))
        imap.logout()
        
    # Close DB connection
    if conn:
        cur.close()
        conn.close()
        
    exit()

def attach_file_to_email(message, filename):
    # Open the attachment file for reading in binary mode, and make it a MIMEApplication class
    with open(filename, "rb") as f:
        file_attachment = MIMEApplication(f.read())
    # Add header/name to the attachments    
    file_attachment.add_header(
        "Content-Disposition",
        f"attachment; filename= {filename}",
    )
    # Attach the file to the message
    message.attach(file_attachment)
    
def print_json(d):
    print(json.dumps(d, indent=4))
    
def get_constituent_from_re():
    # Housekeeping
    multiple_files = glob.glob("Constituents_in_RE_*.json")

    # Iterate over the list of filepaths & remove each file.
    print("Removing old files with list of constituents")
    for each_file in multiple_files:
        try:
            os.remove(each_file)
        except:
            pass
        
    global url, params
    
    # Request parameters for Blackbaud API request
    params = {
        'fields': 'id, name',
        'limit': '5000'
    }
    
    # Blackbaud API URL
    url = 'https://api.sky.blackbaud.com/constituent/v1/constituents'
    
    # Pagination request to retreive list
    while url:
        # Blackbaud API GET request
        get_request_re()

        # Incremental File name
        i = 1
        while os.path.exists("Constituents_in_RE_%s.json" % i):
            i += 1
        with open("Constituents_in_RE_%s.json" % i, "w") as list_output:
            json.dump(re_api_response, list_output,ensure_ascii=False, sort_keys=True, indent=4)
        
        # Check if a variable is present in file
        with open("Constituents_in_RE_%s.json" % i) as list_output_last:
            if 'next_link' in list_output_last.read():
                url = re_api_response["next_link"]
            else:
                break
            
    # Delete rows in table
    cur.execute("truncate constituent_list;")
    
    # Commit changes
    conn.commit()
        
    # Read each file
    multiple_files = glob.glob("Constituents_in_RE_*.json")
    for each_file in multiple_files:

        # Open JSON file
        print("Getting data from JSON and storing into Constituents_in_RE.csv file")
        with open(each_file, 'r') as json_file:
            json_content = json.load(json_file)

            for results in json_content['value']:
                constituent_id = results['id']
                name = results['name']
                
                # Will update in PostgreSQL
                insert_updates = """
                                INSERT INTO constituent_list (constituent_id, name)
                                VALUES (%s, %s)
                                """
                cur.execute(insert_updates, [constituent_id, name])
                
                conn.commit()
                
        os.remove(each_file)

def get_opportunity_list_from_re():
    global url
    
    # Read multiple files
    multiple_files = glob.glob("Opportunity_List_from_RE_*.json")
    
    # Housekeeping
    print("Remove Opportunity_List_from_RE_*.json files")
    for each_file in multiple_files:
        try:
            os.remove(each_file)
        except:
            pass
    
    # Blackbaud API URL
    url = 'https://api.sky.blackbaud.com/opportunity/v1/opportunities?include_inactive=false'
    
    # Pagination request to retreive list
    while url:
        # Blackbaud API GET request
        get_request_re()

        # Incremental File name
        i = 1
        while os.path.exists("Opportunity_List_from_RE_%s.json" % i):
            i += 1
        with open("Opportunity_List_from_RE_%s.json" % i, "w") as list_output:
            json.dump(re_api_response, list_output,ensure_ascii=False, sort_keys=True, indent=4)
        
        # Check if a variable is present in file
        with open("Opportunity_List_from_RE_%s.json" % i) as list_output_last:
            if 'next_link' in list_output_last.read():
                url = re_api_response["next_link"]
            else:
                break
    
    # Read each file
    print("Parsing content from Opportunity_List_from_RE_*.json files and adding to DB")
    multiple_files = glob.glob("Opportunity_List_from_RE_*.json")
    for each_file in multiple_files:

        # Open JSON file
        with open(each_file, 'r') as json_file:
            json_content = json.load(json_file)

            for results in json_content['value']:
                opportunity_id = results['id']
                
                try:
                    ask_amount = results['ask_amount']['value']
                except:
                    ask_amount = ""
                    
                constituent_id = results['constituent_id']
                
                try:
                    date_added = results['date_added']
                except:
                    date_added = ""
                    
                try:
                    date_modified = results['date_modified']
                except:
                    date_modified = ""
                
                try:
                    expected_amount = results['expected_amount']['value']
                except:
                    expected_amount = ""
                
                try:
                    funded_amount = results['funded_amount']['value']
                except:
                    funded_amount = ""
                    
                try:
                    opportunity_name = results['name']
                except:
                    opportunity_name = ""
                
                try:
                    purpose = results['purpose']
                except:
                    purpose = ""
                
                try:
                    status = results['status']
                except:
                    status = ""

                # Will update in PostgreSQL
                insert_updates = """
                                INSERT INTO opportunity_list (opportunity_id, ask_amount, constituent_id, date_added, date_modified, expected_amount, funded_amount, opportunity_name, purpose, status ,date)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                                """
                cur.execute(insert_updates, [opportunity_id, ask_amount, constituent_id, date_added, date_modified, expected_amount, funded_amount, opportunity_name, purpose, status])
                
                conn.commit()
                
        os.remove(each_file)
    
try:
    # Get list of constituents in RE
    print("Get list of constituents in RE")
    get_constituent_from_re()
    
    # Get opportunity list from RE
    print("Get opportunity list from RE")
    params = ""
    get_opportunity_list_from_re()
    
    # Close DB connection
    cur.close()
    conn.close()

except Exception as Argument:
    print("Error while downloading opportunity list from Raisers Edge")
    subject = "Error while downloading opportunity list from Raisers Edge"
    send_error_emails()