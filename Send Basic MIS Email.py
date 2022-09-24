#!/usr/bin/env python3

import requests, os, json, glob, psycopg2, sys, smtplib, ssl, imaplib, time, datetime, logging, locale, xlsxwriter, pretty_html_table, shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from jinja2 import Environment
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from datetime import date, timedelta
from pprint import pprint
import pandas as pd
from pretty_html_table import build_table
from string import Template

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

# Setting Locale
print("Setting Locale")
locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')

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
ERROR_EMAILS_TO  = os.getenv("ERROR_EMAILS_TO")
SEND_TO = os.getenv("SEND_TO")
CC_TO = os.getenv("CC_TO")

def connect_db():
    global conn, cur
    # PostgreSQL DB Connection
    conn = psycopg2.connect(host=DB_IP, dbname=DB_NAME, user=DB_USERNAME, password=DB_PASSWORD)

    # Open connection
    print("Creating connection with SQL database")
    cur = conn.cursor()

def disconnect_db():
    # Close DB connection
    if conn:
        cur.close()
        conn.close()
    
    # Close writing to Process_Progress_Email.log
    sys.stdout.close()
    
    exit()
    
def housekeeping():
    # Housekeeping
    multiple_files = glob.glob("*_RE_*.json")

    # Iterate over the list of filepaths & remove each file.
    print("Removing old files")
    for each_file in multiple_files:
        try:
            os.remove(each_file)
        except:
            pass
          
    # Housekeeping
    multiple_files = glob.glob("*.xlsx")

    # Iterate over the list of filepaths & remove each file.
    print("Removing old files")
    for each_file in multiple_files:
        try:
            os.remove(each_file)
        except:
            pass
        
def send_error_emails():
    print("Sending email for an error")
    
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = MAIL_USERN
    message["To"] = ERROR_EMAILS_TO

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
            job_name = subject,
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
            MAIL_USERN, ERROR_EMAILS_TO, emailcontent
        )

    # Save copy of the sent email to sent items folder
    with imaplib.IMAP4_SSL(IMAP_URL, IMAP_PORT) as imap:
        imap.login(MAIL_USERN, MAIL_PASSWORD)
        imap.append('Sent', '\\Seen', imaplib.Time2Internaldate(time.time()), emailcontent.encode('utf8'))
        imap.logout()

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
    
def get_constituent_data():
    global constituent_dataframe
    
    extract_sql = """
    SELECT * from constituent_list
    """
    cur.execute(extract_sql)
    constituent_data = list(cur.fetchall())
    
    # Converting to Panda's Dataframe
    print("Converting to Panda's Dataframe")
    constituent_dataframe = pd.DataFrame(constituent_data, columns = ['Constituent_ID', 'Constituent_Name', 'Type', 'Date_Added'])

def pagination_api_request(url):
    global donation_dataframe
    
    params = {}
    
    while url:
        # Blackbaud API GET request
        get_request_re(url, params)

        # Incremental File name
        i = 1
        while os.path.exists("Gift_List_in_RE_%s.json" % i):
            i += 1
        with open("Gift_List_in_RE_%s.json" % i, "w") as list_output:
            json.dump(re_api_response, list_output,ensure_ascii=False, sort_keys=True, indent=4)
        
        # Check if a variable is present in file
        with open("Gift_List_in_RE_%s.json" % i) as list_output_last:
            if 'next_link' in list_output_last.read():
                url = re_api_response["next_link"]
            else:
                break

def retrieve_token():
    global access_token
    # Retrieve access_token from file
    print("Retrieve token from API connections")
    
    with open('access_token_output.json') as access_token_output:
        data = json.load(access_token_output)
        access_token = data["access_token"]
    
def get_request_re(url, params):
    
    print("Running GET Request from RE function")
    time.sleep(5)
    
    # Request Headers for Blackbaud API request
    headers = {
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
        
def get_constituency_data():
    
    global constituency_dataframe
    
    extract_sql = """
    SELECT * from constituency_list
    """
    cur.execute(extract_sql)
    constituency_data = list(cur.fetchall())
    
    # Converting to Panda's Dataframe
    print("Converting to Panda's Dataframe")
    constituency_dataframe = pd.DataFrame(constituency_data, columns = ['Constituency_ID', 'Constituent_ID', 'Description', 'Inactive', 'Sequence'])

def identify_current_quarter():
    global financial_year, Q1_start_date, Q1_end_date, Q2_start_date, Q2_end_date, Q3_start_date, Q3_end_date, Q4_start_date, Q4_end_date
    
    print("Identifying current quarter")
    
    current_month = int(datetime.now().strftime("%m"))
    current_year = int(datetime.now().strftime("%Y"))
    
    if int(current_month) <= 4:
        financial_year = int(datetime.now().strftime("%Y")) - 1
    else:
        financial_year = current_year
    
    # Check if current month falls between Jan and March
    if current_month >= 1 and current_month <= 3:
        
        ## Q1
        Q1_start_date = datetime.strptime(f"{current_year - 1}-04-01", "%Y-%m-%d").date()
        Q1_end_date = datetime.strptime(f"{current_year - 1}-06-30", "%Y-%m-%d").date()
        
        ## Q2
        Q2_start_date = datetime.strptime(f"{current_year - 1}-07-01", "%Y-%m-%d").date()
        Q2_end_date = datetime.strptime(f"{current_year - 1}-09-30", "%Y-%m-%d").date()
        
        ## Q3
        Q3_start_date = datetime.strptime(f"{current_year - 1}-10-01", "%Y-%m-%d").date()
        Q3_end_date = datetime.strptime(f"{current_year - 1}-12-31", "%Y-%m-%d").date()
        
        ## Q4
        Q4_start_date = datetime.strptime(f"{current_year}-01-01", "%Y-%m-%d").date()
        Q4_end_date = datetime.strptime(f"{current_year}-03-31", "%Y-%m-%d").date()
    
    else:
        
        ## Q1
        Q1_start_date = datetime.strptime(f"{current_year}-04-01", "%Y-%m-%d").date()
        Q1_end_date = datetime.strptime(f"{current_year}-06-30", "%Y-%m-%d").date()
        
        ## Q2
        Q2_start_date = datetime.strptime(f"{current_year}-07-01", "%Y-%m-%d").date()
        Q2_end_date = datetime.strptime(f"{current_year}-09-30", "%Y-%m-%d").date()
        
        ## Q3
        Q3_start_date = datetime.strptime(f"{current_year}-10-01", "%Y-%m-%d").date()
        Q3_end_date = datetime.strptime(f"{current_year}-12-31", "%Y-%m-%d").date()
        
        ## Q4
        Q4_start_date = datetime.strptime(f"{current_year + 1}-01-01", "%Y-%m-%d").date()
        Q4_end_date = datetime.strptime(f"{current_year + 1}-03-31", "%Y-%m-%d").date()

def get_constituent_breakup():
    
    # Get primary constituent code
    primary_constituency = constituency_dataframe.query('Description == "Alumni"').filter(['Constituent_ID', 'Description']).drop_duplicates()
    
    # Make complete constituent dataframe
    complete_constituent_dataframe = pd.merge(constituent_dataframe, primary_constituency, on='Constituent_ID', how='outer')
    pprint(complete_constituent_dataframe)
    
    # Convert the date to datetime64
    complete_constituent_dataframe['Date_Added'] = pd.to_datetime(complete_constituent_dataframe['Date_Added'], format='%Y-%m-%d')
    
    # Constituent Breakup list
    constituent_breakup_list = {
        'Timeline': [
            'Since Inception',
            'Created in Q1',
            'Created in Q2',
            'Created in Q3',
            'Created in Q4'
        ],
        'Individuals': [
            len(complete_constituent_dataframe.query('Type == "Individual"').index),
            len(complete_constituent_dataframe.query(f'Type == "Individual" and Date_Added >= "{Q1_start_date}" and Date_Added <= "{Q1_end_date}"').index),
            len(complete_constituent_dataframe.query(f'Type == "Individual" and Date_Added >= "{Q2_start_date}" and Date_Added <= "{Q2_end_date}"').index),
            len(complete_constituent_dataframe.query(f'Type == "Individual" and Date_Added >= "{Q3_start_date}" and Date_Added <= "{Q3_end_date}"').index),
            len(complete_constituent_dataframe.query(f'Type == "Individual" and Date_Added >= "{Q4_start_date}" and Date_Added <= "{Q4_end_date}"').index)
        ],
        'Corporate': [
            len(complete_constituent_dataframe.query('Type == "Organization"').index),
            len(complete_constituent_dataframe.query(f'Type == "Organization" and Date_Added >= "{Q1_start_date}" and Date_Added <= "{Q1_end_date}"').index),
            len(complete_constituent_dataframe.query(f'Type == "Organization" and Date_Added >= "{Q2_start_date}" and Date_Added <= "{Q2_end_date}"').index),
            len(complete_constituent_dataframe.query(f'Type == "Organization" and Date_Added >= "{Q3_start_date}" and Date_Added <= "{Q3_end_date}"').index),
            len(complete_constituent_dataframe.query(f'Type == "Organization" and Date_Added >= "{Q4_start_date}" and Date_Added <= "{Q4_end_date}"').index)            
        ]
    }
    
    prepare_html_table(constituent_breakup_list, 'center')

def prepare_html_table(dataframe, text_align):
    global html_output
    
    data = pd.DataFrame(dataframe)
    html_output = (build_table(data, 'blue_dark', font_family='Open Sans, Helvetica, Arial, sans-serif', even_color='black', padding='10px', width='900px', font_size='16px', text_align=text_align)).replace("background-color: #D9E1F2;font-family: Open Sans", "background-color: #D9E1F2; color: black;font-family: Open Sans")
    
    print(html_output)
    
try:
    
    # Retrieve Token
    retrieve_token()
    
    # Housekeeping
    housekeeping()
    
    # Connect to DB
    connect_db()
    
    # Get constituent data
    get_constituent_data()
    
    
    
except Exception as Argument:
  
    subject = "Error while preparing Basic MIS Email from Raisers Edge"
    print(subject)
    send_error_emails()
  
finally:

    # Do housekeeping
    housekeeping()
    
    # Disconnect DB
    disconnect_db()