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
            
        # Add to dataframe
        add_to_dataframe(i)
        
        # Check if a variable is present in file
        with open("Gift_List_in_RE_%s.json" % i) as list_output_last:
            if 'next_link' in list_output_last.read():
                url = re_api_response["next_link"]
            else:
                break

def add_to_dataframe(i):
    
    global dataframe
    
    with open(f'Gift_List_in_RE_{i}.json','r') as f:
        value = json.loads(f.read())
    
    if i == 1:
        # dataframe = pd.json_normalize(value, record_path=['value', 'gift_splits'], meta=[['value', 'id'], ['value', 'amount', 'value'], ['value', 'constituent_id'], ['value', 'date'], ['value', 'lookup_id']])
        dataframe = pd.json_normalize(value, record_path=['value', 'gift_splits'], meta=[['value', 'id'], ['value', 'amount', 'value'], ['value', 'constituent_id']])
    else:
        dataframe_new = pd.json_normalize(value, record_path=['value', 'gift_splits'], meta=[['value', 'id'], ['value', 'amount', 'value'], ['value', 'constituent_id']])
        # dataframe.append(dataframe_new)
        dataframe = pd.concat([dataframe, dataframe_new])

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
      
    global complete_constituent_dataframe
    
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
    
def send_email():    
    subject = f"Summary of records | Raisers Edge"
    
    print(f"Sending '{subject}' email...")
    
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = MAIL_USERN
    message["To"] = SEND_TO
    message['Cc'] = CC_TO

    # Adding Reply-to header
    message.add_header('reply-to', MAIL_USERN)
        
    TEMPLATE = """
                <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
                <html xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office" style="font-family:arial, 'helvetica neue', helvetica, sans-serif"> 
                <head> 
                  <meta charset="UTF-8"> 
                  <meta content="width=device-width, initial-scale=1" name="viewport"> 
                  <meta name="x-apple-disable-message-reformatting"> 
                  <meta http-equiv="X-UA-Compatible" content="IE=edge"> 
                  <meta content="telephone=no" name="format-detection"> 
                  <title>Summary of records | Raisers Edge</title><!--[if (mso 16)]>
                    <style type="text/css">
                    a {text-decoration: none;}
                    </style>
                    <![endif]--><!--[if gte mso 9]><style>sup { font-size: 100% !important; }</style><![endif]--><!--[if gte mso 9]>
                <xml>
                    <o:OfficeDocumentSettings>
                    <o:AllowPNG></o:AllowPNG>
                    <o:PixelsPerInch>96</o:PixelsPerInch>
                    </o:OfficeDocumentSettings>
                </xml>
                <![endif]--> 
                  <style type="text/css">
                .rollover div {
                  font-size:0;
                }
                #outlook a {
                  padding:0;
                }
                .es-button {
                  mso-style-priority:100!important;
                  text-decoration:none!important;
                }
                a[x-apple-data-detectors] {
                  color:inherit!important;
                  text-decoration:none!important;
                  font-size:inherit!important;
                  font-family:inherit!important;
                  font-weight:inherit!important;
                  line-height:inherit!important;
                }
                .es-desk-hidden {
                  display:none;
                  float:left;
                  overflow:hidden;
                  width:0;
                  max-height:0;
                  line-height:0;
                  mso-hide:all;
                }
                [data-ogsb] .es-button {
                  border-width:0!important;
                  padding:10px 20px 10px 20px!important;
                }
                @media only screen and (max-width:600px) {p, ul li, ol li, a { line-height:150%!important } h1, h2, h3, h1 a, h2 a, h3 a { line-height:120% } h1 { font-size:30px!important; text-align:left } h2 { font-size:24px!important; text-align:left } h3 { font-size:20px!important; text-align:left } .es-header-body h1 a, .es-content-body h1 a, .es-footer-body h1 a { font-size:30px!important; text-align:left } .es-header-body h2 a, .es-content-body h2 a, .es-footer-body h2 a { font-size:24px!important; text-align:left } .es-header-body h3 a, .es-content-body h3 a, .es-footer-body h3 a { font-size:20px!important; text-align:left } .es-menu td a { font-size:14px!important } .es-header-body p, .es-header-body ul li, .es-header-body ol li, .es-header-body a { font-size:14px!important } .es-content-body p, .es-content-body ul li, .es-content-body ol li, .es-content-body a { font-size:14px!important } .es-footer-body p, .es-footer-body ul li, .es-footer-body ol li, .es-footer-body a { font-size:14px!important } .es-infoblock p, .es-infoblock ul li, .es-infoblock ol li, .es-infoblock a { font-size:12px!important } *[class="gmail-fix"] { display:none!important } .es-m-txt-c, .es-m-txt-c h1, .es-m-txt-c h2, .es-m-txt-c h3 { text-align:center!important } .es-m-txt-r, .es-m-txt-r h1, .es-m-txt-r h2, .es-m-txt-r h3 { text-align:right!important } .es-m-txt-l, .es-m-txt-l h1, .es-m-txt-l h2, .es-m-txt-l h3 { text-align:left!important } .es-m-txt-r img, .es-m-txt-c img, .es-m-txt-l img { display:inline!important } .es-button-border { display:inline-block!important } a.es-button, button.es-button { font-size:18px!important; display:inline-block!important } .es-adaptive table, .es-left, .es-right { width:100%!important } .es-content table, .es-header table, .es-footer table, .es-content, .es-footer, .es-header { width:100%!important; max-width:600px!important } .es-adapt-td { display:block!important; width:100%!important } .adapt-img { width:100%!important; height:auto!important } .es-m-p0 { padding:0!important } .es-m-p0r { padding-right:0!important } .es-m-p0l { padding-left:0!important } .es-m-p0t { padding-top:0!important } .es-m-p0b { padding-bottom:0!important } .es-m-p20b { padding-bottom:20px!important } .es-mobile-hidden, .es-hidden { display:none!important } tr.es-desk-hidden, td.es-desk-hidden, table.es-desk-hidden { width:auto!important; overflow:visible!important; float:none!important; max-height:inherit!important; line-height:inherit!important } tr.es-desk-hidden { display:table-row!important } table.es-desk-hidden { display:table!important } td.es-desk-menu-hidden { display:table-cell!important } .es-menu td { width:1%!important } table.es-table-not-adapt, .esd-block-html table { width:auto!important } table.es-social { display:inline-block!important } table.es-social td { display:inline-block!important } .es-desk-hidden { display:table-row!important; width:auto!important; overflow:visible!important; max-height:inherit!important } .es-m-p5 { padding:5px!important } .es-m-p5t { padding-top:5px!important } .es-m-p5b { padding-bottom:5px!important } .es-m-p5r { padding-right:5px!important } .es-m-p5l { padding-left:5px!important } .es-m-p10 { padding:10px!important } .es-m-p10t { padding-top:10px!important } .es-m-p10b { padding-bottom:10px!important } .es-m-p10r { padding-right:10px!important } .es-m-p10l { padding-left:10px!important } .es-m-p15 { padding:15px!important } .es-m-p15t { padding-top:15px!important } .es-m-p15b { padding-bottom:15px!important } .es-m-p15r { padding-right:15px!important } .es-m-p15l { padding-left:15px!important } .es-m-p20 { padding:20px!important } .es-m-p20t { padding-top:20px!important } .es-m-p20r { padding-right:20px!important } .es-m-p20l { padding-left:20px!important } .es-m-p25 { padding:25px!important } .es-m-p25t { padding-top:25px!important } .es-m-p25b { padding-bottom:25px!important } .es-m-p25r { padding-right:25px!important } .es-m-p25l { padding-left:25px!important } .es-m-p30 { padding:30px!important } .es-m-p30t { padding-top:30px!important } .es-m-p30b { padding-bottom:30px!important } .es-m-p30r { padding-right:30px!important } .es-m-p30l { padding-left:30px!important } .es-m-p35 { padding:35px!important } .es-m-p35t { padding-top:35px!important } .es-m-p35b { padding-bottom:35px!important } .es-m-p35r { padding-right:35px!important } .es-m-p35l { padding-left:35px!important } .es-m-p40 { padding:40px!important } .es-m-p40t { padding-top:40px!important } .es-m-p40b { padding-bottom:40px!important } .es-m-p40r { padding-right:40px!important } .es-m-p40l { padding-left:40px!important } .h-auto { height:auto!important } }
                </style> 
                </head> 
                <body style="width:100%;font-family:arial, 'helvetica neue', helvetica, sans-serif;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;padding:0;Margin:0"><span style="display:none !important;font-size:0px;line-height:0;color:#ffffff;visibility:hidden;opacity:0;height:0;width:0;mso-hide:all">Dear Team, Please find the below summary of records in Raisers Edge in F.Y. {{financial_year}}.&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;</span> 
                  <div class="es-wrapper-color" style="background-color:#F6F6F6"><!--[if gte mso 9]>
                      <v:background xmlns:v="urn:schemas-microsoft-com:vml" fill="t">
                        <v:fill type="tile" color="#f6f6f6"></v:fill>
                      </v:background>
                    <![endif]--> 
                  <table class="es-wrapper" width="100%" cellspacing="0" cellpadding="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;padding:0;Margin:0;width:100%;height:100%;background-repeat:repeat;background-position:center top"> 
                    <tr> 
                      <td valign="top" style="padding:0;Margin:0"> 
                      <table class="es-header" cellspacing="0" cellpadding="0" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;table-layout:fixed !important;width:100%;background-color:transparent;background-repeat:repeat;background-position:center top"> 
                        <tr> 
                          <td align="center" style="padding:0;Margin:0"> 
                          <table class="es-header-body" cellspacing="0" cellpadding="0" bgcolor="#ffffff" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:900px"> 
                            <tr> 
                              <td align="left" bgcolor="#305496" style="padding:0;Margin:0;background-color:#305496"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:900px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" style="padding:20px;Margin:0;font-size:0px"><img src="data:image/jpg;base64,iVBORw0KGgoAAAANSUhEUgAAAyAAAAFLCAYAAAAu3OjYAAAKMWlDQ1BJQ0MgcHJvZmlsZQAASImd
                                        lndUU9kWh8+9N71QkhCKlNBraFICSA29SJEuKjEJEErAkAAiNkRUcERRkaYIMijggKNDkbEiioUB
                                        UbHrBBlE1HFwFBuWSWStGd+8ee/Nm98f935rn73P3Wfvfda6AJD8gwXCTFgJgAyhWBTh58WIjYtn
                                        YAcBDPAAA2wA4HCzs0IW+EYCmQJ82IxsmRP4F726DiD5+yrTP4zBAP+flLlZIjEAUJiM5/L42VwZ
                                        F8k4PVecJbdPyZi2NE3OMErOIlmCMlaTc/IsW3z2mWUPOfMyhDwZy3PO4mXw5Nwn4405Er6MkWAZ
                                        F+cI+LkyviZjg3RJhkDGb+SxGXxONgAoktwu5nNTZGwtY5IoMoIt43kA4EjJX/DSL1jMzxPLD8XO
                                        zFouEiSniBkmXFOGjZMTi+HPz03ni8XMMA43jSPiMdiZGVkc4XIAZs/8WRR5bRmyIjvYODk4MG0t
                                        bb4o1H9d/JuS93aWXoR/7hlEH/jD9ld+mQ0AsKZltdn6h21pFQBd6wFQu/2HzWAvAIqyvnUOfXEe
                                        unxeUsTiLGcrq9zcXEsBn2spL+jv+p8Of0NffM9Svt3v5WF485M4knQxQ143bmZ6pkTEyM7icPkM
                                        5p+H+B8H/nUeFhH8JL6IL5RFRMumTCBMlrVbyBOIBZlChkD4n5r4D8P+pNm5lona+BHQllgCpSEa
                                        QH4eACgqESAJe2Qr0O99C8ZHA/nNi9GZmJ37z4L+fVe4TP7IFiR/jmNHRDK4ElHO7Jr8WgI0IABF
                                        QAPqQBvoAxPABLbAEbgAD+ADAkEoiARxYDHgghSQAUQgFxSAtaAYlIKtYCeoBnWgETSDNnAYdIFj
                                        4DQ4By6By2AE3AFSMA6egCnwCsxAEISFyBAVUod0IEPIHLKFWJAb5AMFQxFQHJQIJUNCSAIVQOug
                                        UqgcqobqoWboW+godBq6AA1Dt6BRaBL6FXoHIzAJpsFasBFsBbNgTzgIjoQXwcnwMjgfLoK3wJVw
                                        A3wQ7oRPw5fgEVgKP4GnEYAQETqiizARFsJGQpF4JAkRIauQEqQCaUDakB6kH7mKSJGnyFsUBkVF
                                        MVBMlAvKHxWF4qKWoVahNqOqUQdQnag+1FXUKGoK9RFNRmuizdHO6AB0LDoZnYsuRlegm9Ad6LPo
                                        EfQ4+hUGg6FjjDGOGH9MHCYVswKzGbMb0445hRnGjGGmsVisOtYc64oNxXKwYmwxtgp7EHsSewU7
                                        jn2DI+J0cLY4X1w8TogrxFXgWnAncFdwE7gZvBLeEO+MD8Xz8MvxZfhGfA9+CD+OnyEoE4wJroRI
                                        QiphLaGS0EY4S7hLeEEkEvWITsRwooC4hlhJPEQ8TxwlviVRSGYkNimBJCFtIe0nnSLdIr0gk8lG
                                        ZA9yPFlM3kJuJp8h3ye/UaAqWCoEKPAUVivUKHQqXFF4pohXNFT0VFysmK9YoXhEcUjxqRJeyUiJ
                                        rcRRWqVUo3RU6YbStDJV2UY5VDlDebNyi/IF5UcULMWI4kPhUYoo+yhnKGNUhKpPZVO51HXURupZ
                                        6jgNQzOmBdBSaaW0b2iDtCkVioqdSrRKnkqNynEVKR2hG9ED6On0Mvph+nX6O1UtVU9Vvuom1TbV
                                        K6qv1eaoeajx1UrU2tVG1N6pM9R91NPUt6l3qd/TQGmYaYRr5Grs0Tir8XQObY7LHO6ckjmH59zW
                                        hDXNNCM0V2ju0xzQnNbS1vLTytKq0jqj9VSbru2hnaq9Q/uE9qQOVcdNR6CzQ+ekzmOGCsOTkc6o
                                        ZPQxpnQ1df11Jbr1uoO6M3rGelF6hXrtevf0Cfos/ST9Hfq9+lMGOgYhBgUGrQa3DfGGLMMUw12G
                                        /YavjYyNYow2GHUZPTJWMw4wzjduNb5rQjZxN1lm0mByzRRjyjJNM91tetkMNrM3SzGrMRsyh80d
                                        zAXmu82HLdAWThZCiwaLG0wS05OZw2xljlrSLYMtCy27LJ9ZGVjFW22z6rf6aG1vnW7daH3HhmIT
                                        aFNo02Pzq62ZLde2xvbaXPJc37mr53bPfW5nbse322N3055qH2K/wb7X/oODo4PIoc1h0tHAMdGx
                                        1vEGi8YKY21mnXdCO3k5rXY65vTW2cFZ7HzY+RcXpkuaS4vLo3nG8/jzGueNueq5clzrXaVuDLdE
                                        t71uUnddd457g/sDD30PnkeTx4SnqWeq50HPZ17WXiKvDq/XbGf2SvYpb8Tbz7vEe9CH4hPlU+1z
                                        31fPN9m31XfKz95vhd8pf7R/kP82/xsBWgHcgOaAqUDHwJWBfUGkoAVB1UEPgs2CRcE9IXBIYMj2
                                        kLvzDecL53eFgtCA0O2h98KMw5aFfR+OCQ8Lrwl/GGETURDRv4C6YMmClgWvIr0iyyLvRJlESaJ6
                                        oxWjE6Kbo1/HeMeUx0hjrWJXxl6K04gTxHXHY+Oj45vipxf6LNy5cDzBPqE44foi40V5iy4s1lic
                                        vvj4EsUlnCVHEtGJMYktie85oZwGzvTSgKW1S6e4bO4u7hOeB28Hb5Lvyi/nTyS5JpUnPUp2Td6e
                                        PJninlKR8lTAFlQLnqf6p9alvk4LTduf9ik9Jr09A5eRmHFUSBGmCfsytTPzMoezzLOKs6TLnJft
                                        XDYlChI1ZUPZi7K7xTTZz9SAxESyXjKa45ZTk/MmNzr3SJ5ynjBvYLnZ8k3LJ/J9879egVrBXdFb
                                        oFuwtmB0pefK+lXQqqWrelfrry5aPb7Gb82BtYS1aWt/KLQuLC98uS5mXU+RVtGaorH1futbixWK
                                        RcU3NrhsqNuI2ijYOLhp7qaqTR9LeCUXS61LK0rfb+ZuvviVzVeVX33akrRlsMyhbM9WzFbh1uvb
                                        3LcdKFcuzy8f2x6yvXMHY0fJjpc7l+y8UGFXUbeLsEuyS1oZXNldZVC1tep9dUr1SI1XTXutZu2m
                                        2te7ebuv7PHY01anVVda926vYO/Ner/6zgajhop9mH05+x42Rjf2f836urlJo6m06cN+4X7pgYgD
                                        fc2Ozc0tmi1lrXCrpHXyYMLBy994f9Pdxmyrb6e3lx4ChySHHn+b+O31w0GHe4+wjrR9Z/hdbQe1
                                        o6QT6lzeOdWV0iXtjusePhp4tLfHpafje8vv9x/TPVZzXOV42QnCiaITn07mn5w+lXXq6enk02O9
                                        S3rvnIk9c60vvG/wbNDZ8+d8z53p9+w/ed71/LELzheOXmRd7LrkcKlzwH6g4wf7HzoGHQY7hxyH
                                        ui87Xe4Znjd84or7ldNXva+euxZw7dLI/JHh61HXb95IuCG9ybv56Fb6ree3c27P3FlzF3235J7S
                                        vYr7mvcbfjT9sV3qID0+6j068GDBgztj3LEnP2X/9H686CH5YcWEzkTzI9tHxyZ9Jy8/Xvh4/EnW
                                        k5mnxT8r/1z7zOTZd794/DIwFTs1/lz0/NOvm1+ov9j/0u5l73TY9P1XGa9mXpe8UX9z4C3rbf+7
                                        mHcTM7nvse8rP5h+6PkY9PHup4xPn34D94Tz+3EBhusAAAAGYktHRAAAAAAAAPlDu38AACAASURB
                                        VHja7F13mFxl+T3f7KYnBAJJKAklEEroSO8gvYNSBSlSVPiBCIoo1YogICAqAoKIBaRJB+ldqvQa
                                        WkLZUEI2ISHJ7pzfH9/5mDc3d3Zn28xs8p7nmefOTrn3a3f2nO9tgMPhcDgcDofD4XA4HA6Hw+Fw
                                        OBwOh8PhcDgcDofD4XA4HA6Hw+FwOBwOh8PhcDgcDofD4XA4HA6Hw+FwOBwOh8PhcDgcDofD4XA4
                                        HPMsgg+Bo55BcgCAxQH0A7AggAEAFtPfCwFYAkARQCOAzQGsBmAqgCE5p0uvXwngAwB9AMwG8JaO
                                        0wF8BGAGgE8BzNJrXwD4IoQw3WfE4XA4HA6HwwWIY94UHoUQQpHkZgDuq2FTHgPwOoAPATQBuDqE
                                        MMFnyOFwOBwOh6NzaPQhcNSlMo7iowBgDUTLxesARujtvuajA8zzIRWefmrm7xnm+SxzHAxgfT0S
                                        3gYwgWQIIdBnyuFwOBwOh8MFiKOXw5D7wQB20ctjOyAwqMccmgYli1/2PEPaESszAEyT8FkXwLUu
                                        PhwOh8PhcDhcgDjmPYwEsCWASShZP5LAaMt9MKBz7oXMOQ7RY4COq5McGkKY4tPjcDgcDofD4QLE
                                        MW8huV9l8V7m78UywmQaostWEiMtAIYBGJMRL9My55+FaOXomxE8CVMBrIwYFD8lxan4NDkcDofD
                                        4XC4AHH0YoQQqPiPzRGtDilGoxnAAgB+C+BhxMxVsxCDw1vMKVoRM1dZNADon3mtj8RE0HsjELNr
                                        jQYwCsAmEkEFteNNiZgxAF72mXI4HA6Hw+FwOHo5SAYdFyf5KCOaSU4hWSR5H8llq9SW0SQ/UBuK
                                        JMfr+bEkG3y2HA6Hw+FwODqOgg+Bo86Q3KOWQcw+NRHR+pBcp54H8AnJBpKNOoYuPBpIFnS0jz4A
                                        3kdMvwtdf7ieb4EYIP+lYHI4HA6Hw+FwVAZ3wZrPIMIc6jh2gWrjCvo7pcUdhBiM/imAz9WHlm64
                                        XmvZRsRUwA8iumFBQmgigJ0RiyB6ILqjt/4O3A5g2/mku/uEEK7yMfMxc3QKO4UQbuniOjgUwMXz
                                        wVi9hugS3gxgMuIm5sd6/jFioePJenwaQpjpAsQxXwiPEAKVPpb13EaSgxDjP4BodaDW6isAHgoh
                                        zCZZrbX7AID/y7w2FdFC83ZvmHNf/Q6Hw+Fw9DiW16PS/9FXAngaMb50PIAJ81OGTRcg877wKIQQ
                                        iomIklxa5PnBbrIg9ASGAzgApfS7RUT3q4EAntVnWqvUlpcRg93TvdIX0RKyNoB765ngmzl3IeLI
                                        4iwA53Xh+4sBuLQK7XwNwPe6eI63fMxqNma1wr8BvKr/IZ8AmK7f8dlt/O8YBeBPVWjbEwBOLfez
                                        rf81ffQYCmARAIsC2BTAar10Pv4LYIeu/DsDcEuV2nq01v8UREvGdERPjJk6FjVHjeIDQxGzbI4A
                                        sCqAvTsgQvbXw3K2fwG4U+vktRDCDP935ehNoiPY2ASS/UmOI3kCyVcVSH2oYihCPbVbx20UeN6k
                                        trbq+PskqqrYlsEknzDtaNbz60gOqNf513FI3usORzessTGsDh7wMeu9Y0by9ir09xyS+5Bci+Ri
                                        JPt3sq0rVGl+bujC//WhWkebk/wuyRur0N4d64TTVAujutjWRpLLkNyT5A1dbEsTyZNJblCvfKMr
                                        cAvIPCY8gDl2vgcCWAfAdgB+lNkhuxjA1BDCVfWyQ27asCXmTL+bcH+1SLRJBTwDwGOIFg+7c7Y6
                                        gCUAvFFPFgbjxrYmgKNIPgzg/hDCeLMuvH6Jw+HozTgZwF0AXgohNM8PHdbv9xQ93gRwH8k/IFpu
                                        1gBwIICv+dKo+Ty1IFpQ3iJ5PYC1AHwHwEGdON0IAD/V4yWSZwO4J4TwtgsQR70Kj4UAbABgX5TM
                                        exMRzYUDEF0B3gTwT5LTQgi31JqUGuI8DMCGetkq/vEAxusz1drJL4QQWkg+ixiHkuqBTESsBTIa
                                        wBuI5mHWwzow4uN2/XgdAmAiyYsBXAPgzRDCF3nrxuFwOOoYkwD8AMCdIYQPfTi+/O2eAGACyVsB
                                        rILovnycj07diJHHST4N4DoAlyC/yHElGAe5cJL8KYC/hxBe7c3j42l4e7/4KKTgcpLDSO4monmL
                                        xMdEPUZp4Q/RY7h+0G8muYEyPtXSRSddewzibs4ktXOK1ultKPklV4swJ0H2P8TsFQ26dsrMtWyV
                                        29PuPyOSmwO4UXM9UUJzFIDTAbwI4DSS65EcYNaN/w44HI56xg8ArBJCuMLFR9nf/9YQwrMaq3UA
                                        XOujUj9CJIRwE+LG8IPdcMpTALxC8kySS7kAcVRbeKTd6yLJBUnuAeDvAK5HdGGaiJitaZQeFKFO
                                        pHoIooVhEoAbSK5UZevCXF3ScUW17bPM69MATCfZUMUd+3Sd1wB8YF4brOfrkBxU43GzMR/bArgX
                                        MSguzf0YPZ+kNXECokvZJSS3JDk4Wb48RsThcNQZHgawVgjhNyGEj3w4KiK7DCE8ibgBeZiPSF3N
                                        zZuIQep3dKMwf5vkQcoe6gLE0aNks5B+ZEgOIvlVAFdqt2NbxB3vRD5TEPJniBaGgh5ZEQIAvyM5
                                        uhY74sZ1aACAdfXygjougJgN4nllgyhU8ceCsjA1S4QkjBCh39e0s2biQ+3cDtHtapKZWyuYRmhN
                                        TNJjPwB3a96/moSUXWMOh8NRQ5wFYOcQwjM+FJ36//VFCOESRGvIaz4idTMvHwA40vyv7g5cBuBG
                                        kiu5AHH0CNEU2SyS7EtyfcSUgXcB2FGLeSrijneqHF40ZP4JADcBeDxHhADRanImyUVq6I61IGKg
                                        Vkq/m+IumtVumHZXG3diTlerWRq7xWu8HpL4uA3RwjEgIz6CHkX9PUKPqfr8gVpDl0iIDHSLiMPh
                                        qDFOBHByCGGyD0WXCe+TiIloHvTRqJs5GY9M+t1uwJaIgeo795ZNRBcgvUR8GH/9lQGcBOBRxF3s
                                        5Go1wgiPFpQsHk8AOBMxC9a+ALYH8B+9l+qApHiBfQCcTHJIjdyKVlIfZhkCDcRMVO9qHFprNA1P
                                        oRSnAsSAfiAG/VU9kNush+0lPiYhul4l8dGs9rYg5r4vmL+pzyWLSJr7uwD8muT6JPvYOiJ+Fzoc
                                        jirhGAC/md+rRHfz/4u3EF1/7vPRqBvcg56pO3MjgB+Q7OsCxNEl4ZHIpvKbHw3gBcQUhDbGw1o8
                                        UiGjxwCcgWhROD2EcA+ALwBMBrAnovtNI0qpZUfpnEcDOIJkY7VEiCHvG2bIfRIhN4UQZmUEQNWm
                                        Qcd3EN3bkvUoua5tWc3dBhPvUSC5A4BbMbfloxXRde0RAF+VSPq91k4j5raIjELJInKUxO3PVTsm
                                        WVmCCxGHw9HD+DmAP9RxkdzeLEI+QMyK6O5Y9TEfrQB+20OnPwPAj0j285F2dIpk6vlgknuYonzN
                                        JCdkitV8Zp7/l+SvSK5KssGcp1HHBh2XJPmMvtNivj9ex0Ps93uyr3oMJHmz6aMtQLhRIt21mg8V
                                        F/qL2jPbtPEpkotWuT0NKiSZChU1m/lLc3kzyeUzgmVVkqebYpSpL8VM4SO7vo6yhZk8PsShdeCF
                                        CH3MKulzRwoRXqbaVbVqa10XIuzGfq7hhQh7rhBhJ/r1+x7sy09dhDg6LD5EMtcmebkh5Vmy2WpI
                                        +hMkzya5WqoEq3MUsjvXiUSSXNEIjtYcEbJrd5JOIzZCTrX2saZ/zSSnqA1/JblIjQVIH7X3h4a0
                                        07R1LTPeoSesBRkhcbCuP6GM+Pi3xEfBrIEG08bREiKvZNZSVogk0fsoya+RXCBPJDtcgLgA8THr
                                        ogCZUE3iNz8LEPV1PxcgtRcg6tv6PdyfY/z/taO9RVgwz0eTPD4jCCzRnGLIZhPJP5HcKCldkcyG
                                        9nbRddyU5Dsin62ZfwgkuU1nCad+NAptfVeWj9HaabfXnazjz0guUEsXIDNWm5GcoXYVTVuPJDm4
                                        rbntStuN+Gg0lo/xmR+ZJIpuILl8+nxOOxrM3CxJ8jSSL7ZhEbHWkKtIbmgErP+ouQBxAeJj1h0C
                                        ZKs6aOv8JED6dGDn3QVIz/ZtYI5XS3djRzgc7RDM/spg8HiZHe6iER7jSd5Ecnulr00Es9CB6yYy
                                        uq/OWzTk07p6rZ8VSW38SOQKBZHnBUguRXITkvuoiM5lpr/M7OY/K1ewQLJPHczPwiRfyLEYNZP8
                                        m1zf9iG5JslF0rxUOkbtCVSNBXN+rNKauE6xQqGtubLrRGJ1CQm9NzIWEWasbwmnkRydHR+HCxAX
                                        ID5mnRAgv66H35D5SYCYjU4XIDUWIOrfD6vQr3H+n8sxBxE0z8eRPKfMznM2zuMWkofZXffsbncn
                                        RMhROfEgzUYAjcsTIeVEj15fnOQ6JHcneaJcecoha+Gh/nmt3JX+deNcJVemu3IIejn8geQBshos
                                        ldeHtkRjJywfI+ycVihqGszzVUj+0YjQ1hwhYtfl7kb8ughxAeICxMesMwJkVJ20db4SIOrzAS5A
                                        6kKAbFyFft1YyxgrR/3c9Db2Yajx6S9n9bBxHj8jOcrsYHfZvUcEt0HntqTWBjk/TnK5ctfUORbU
                                        7v+3SJ5P8oGcm6Ap59Gcs6NfJHm3ii3Ww+5YGu8fZyxRbfXL4nGZvA8nuRbJYTkuUsGIDhvz8a0K
                                        LB8L5gnETgiRBpIbyLrWlJkP5gS+n5PWhQsRFyAuQHzMOihA9q+jts6PAmQQyXtdgNRcgCxRpb7t
                                        5f+9HGnRrUfympyg3yQ8ZhviebE+b3fFQzfe3EF+oRfm7PCndl2adtlNG5YjuY2IeVOZ4MLxOcLK
                                        Wjs+U8zHrAzRPbKzpLoHBcimGQEwS+1vLSO2xudYLdJ7P9bYLVfGOtIowdKW5eM6ksO7Y5wyQqRR
                                        7mSP5Qge5rRp1+Qm5yLEBYgLEB+zCgTIizSJLVyA1KzfW7kAqbkAaWDMqNnTmEByoXpZe41w1OJm
                                        Go5YRDDlgJ6EOes4FBHrTTQi1uu4DMANIYTPk/WhO/Okq85DIYQwm+TxAIYj1gppBdCAWCtiEmIO
                                        8QLJCwCMA7AOYgG7EeZ0k8zzAYg1JoBSPY1i5u/sP6CXAHym9x+vp2kz7XsQwEAAX9H4DDV9S9XH
                                        oXEcrr+nIhZUTBgB4BdmzP5J8n4ATwL4UOc9AMBFiPU5xpjvtmptXAfgWyGEzzR/xS6ug6IRMq0h
                                        hH+SvAuxNsh31ZdWlIoajjHzfQOA00lepHzzDofD0RZODSE0+zDUHA8iFife2oeiNgghtJK8A8Ba
                                        PXypUQA2B3C9C5D5S3Skgm4jAFwCYGcjPEZkyGUDYgXzuwFcGEKYqHM09lSBphBCUSR2BskjACwK
                                        YJOMCJmKWNjwoMzXXwOwoD5j+9IsMTHYrLXs7vhdAMaLnM8G8DSAtzU2b1tiXOMfCOr4McmDASwp
                                        ATIaQH8AqwNYr4xwaZE4GZ7p/ySNz/KIBSCP1uu/0jmPlfiwOzItGst/ADi6u8RHGSHSGEL4GMBp
                                        JG8GcDqAHTLtSPM9EcCpANYleRKAZ6pdHd7hcPQavATgTh+GuiC/M0me6QKk5ni1Stc5muRN9VDs
                                        0wVIlQmsSPZSmNvqkfCJdiP+BOCxEMIs7UizpxeMESGTRbJvBrAiShaZIZh7J3+ACHQi2+kBlKwb
                                        UwG8rtf7ArgWwBsSGO8jVmefDWB6byCtIYTxEk33kuwLoA+AYRIKSwJYH8BOEmCjRNKHGoEZ9Bhu
                                        hN0MM54nGoEyKiNOZwC4AsDJmqdCTwm0EEKL3KlCCOFJknsiWmVOBzDSrIu0szIRwMYAnkKsvv5i
                                        Et7+C+BwOAx+6daPusJDAB7T/y5HbfBula6zOYDlALziAmT+EyKTSV6C6H4zQ6SeIqHvAbgcwO9D
                                        CNPkFxiqaQGQCGkIIYwn+U2JhdEZEWJFU7JyLICSa07CzbqpPtUP3IvqY0jXSh8U0W0kCV0LIYTW
                                        epxDxUmkfhZDCJ8D+BzABJKPAbgawPcRXZQ20I/6cAC7S6xYtCC6c9kxTW5NIzKfmwHgrwBO62nx
                                        kRHOyUVvOsmLATyq9btT5uOjALwJ4AMA09MpjCB1OBwOIFr3HfXDS74geS6Aq3w0aoZPqnit1VyA
                                        zGcwu8EPiXB+JJJJEfiHAVwi8dEnhDC7Rj9GrSLZTwLYHzHWYGEjQqylI1k5XpMYaUaMB3gNwMsA
                                        JocQpmaEBgEEXeNLi0mt+tuZ8cnOK0pWDduf8QDGk7wa0Q3tl7rxd0B02RqCkoUjxY8UMLerVrJ8
                                        /AXR8vFZNcRHjjBN1pDnSO4tkXW6WRPvSXSdjxjHAhcfDocjg1NCCB/6MNQd7vUhqCmqaRHcBHGj
                                        1AXIfIi3AdwCYEfE3e7+IqgjEH3o76gHkq3MTA8DOAzA3xF371NMSCLItwF4C8AzAO5H3AEnossY
                                        RdD76LVW444zzxDTZCXIE5wi560hhE8BfEry+RDCX0mORHRX2hTACgC2zXy9xYiaT/RjcXotxEem
                                        n60Sx9NJ3g3gJwD66SOzdHxasUTufuVwOLK4wYegLv+PfUTyx4gbZY55W4AcSPL7td70dQFSZQIn
                                        UvqZESDTJDw+QwxqXg/AAwC+qIP2tshKcQOi7/+fEa0209TGuwC8AGBSxspRQMyWlYRI1Rd5e+S3
                                        GuQ4EXYjRoK5dhOAa0nehBgfMk6CZF8JvBV1mqmIZvGTQwhTaiU+MkjWkK0lnlNA+nC196U0BHAL
                                        iMPhKOEeRMu4oz5xuwuQmmF6Fa81BMAiiO7SLkDmQyHyjMhaqmaegnlXAZB2mOthB7koInm9Fm1f
                                        xNiOD9SXYqohAqAlhMDuJsiprkR2LAypZ/b99sat3LkycSkppqXY1XnIWkky1pGPlLv/AQC/kQjd
                                        FcBYRD/Nn4cQmutBfGhNtmq+NzRCY6rWx3OI7nd1kb3M4XDUFS6uh+w7jrJ4ETED5zo+FFXHzCpf
                                        b0EXIPOh+NDTFwD8D9EXbypiLAUBfB3A70RIa76DnAlCvixLoE2Grh6xciggvrUSUm+/g+gWNDuv
                                        XSZz1YwkoPLOlUegrSUjvdQZcZKxjiShwxDCTAAPkHwY0TIyXQGCDXUSlJ/W5JKI2TSIaLFJCRWu
                                        DSFM8Tvd4XDk4BEfgrrmJ7NI/h6x9pijylyL5IPihNVAzYuAFnzaa7bYpgH4F+ZMwUpEP8CtRFBD
                                        HbW3qKxcjYmwhxBaQwhdtg60VTlbu+2DbMVcU5X8KyTPUpX4hc15tkbcxTkhnd9UkG8AcDZizEqq
                                        aXE4yctJHpAqgeuzS5NcmeSwdN1k4TEP2grkqVBkR8c2jaVpYwghfCrxEeowI9j6KMV+ANEtD4hF
                                        rbwausPhyOLyEMK7Pgx1j4d8CGqGCVW8Vn8XIPMhDDl7AHHXeFpGlW6maunFeiJyIsktnREcEgEF
                                        +8go/0Ii/0YsDCT5O5Ha643ISN/dBMDxAA4FcKJp1zDEmIrRZZozVo/F9fcuAA5ErK8x1oz5DwHc
                                        hxgonkTYSJK7k/wGyS1JLpDqp6TPJBHRGTFixzkJpzoL5E5ibieUMn5NRSn+43W/wx0ORw6u8yHo
                                        FXgTsRaZo/r4vIrX6uMCZP7Gu4jB6GMQs2El95YCgK+IePZaNzkR6AZjMbGWg6IRHFsgBrqn4LfU
                                        5xEAvgNgTQBbAtgvQ8bfQQyAJoCjSG5l1jUx5w59QgNKKW+TVaGvXgOA4yWI+knALJJuVJLbIxbZ
                                        uw7AlYi57F8guZuJhRluRETRZAJrsNaVCoUI60l8GEvMUMRYpSSupkhIX4Lq5jJ3OBy9B//zIah/
                                        aBPtbz4SNUE140BqHqPpAqQ2N7jNhnWTXp4mQjcFwEYANiQ5EDHtaa9xZ7HWDeOmRZIDSK5B8usk
                                        9yG5ptyrAmJVzp0B7CLin26MlTQmn0owfI/kQub9jyVW3tdaPlvX/ljfWya5TRmyPBjR8hEAvCtR
                                        MFznnAJgD5JL6XqL6PV3FXT9SwBLSHh8D9HNazSAv5FcFsAgzefDJH8pC8mwFL+R3KjkxtYb770k
                                        oNYHsLzGKKCUfvdxpd8tePpdh8NhcD2AiT4MvQZP+BDUBNXMGDrLBch8rUMCEXeF8rJhLQ+gb2/L
                                        JGSsG0HuSkeSvAzRNecZxLiXfwB4kuRJ5sduFmJF8JEm3mE1Ha9ArEcyBsABZkzSWD0F4Nf6/LFQ
                                        Fibkx9AUEC0ekODoh1hk8QPEwLuFAHxDwma0diQ+BDASwBqIJtITQgjnAdgMMZnAQAC7oVTNfAMA
                                        J0qovA3gZpI/IrkFyUa5sSVXrWQl6g33YhLOm2oMU62S5H7l6TUdDkcervZNiV6F1xEzGjrmXQEy
                                        1QXI/Ks+Eol+UQR6BObMhrU3gDVysi7VCxMN2Z18kn1Jbk5yG/2zWQrA7wAcJML6N0TLwbVaez9D
                                        LMD3JoAmRMvEGHOZDdX3WxEDx1sBfDcTcA4AKwM4U8LjFABboFQwMbf55jhE4qJVbZ2IWHhxaX3/
                                        c8TEAF/ovUEALiJ5kAj41xCL8b0TQvgAwPYA1kLJ33kQgO0A/ArAHwEMJ3keyT0kRr4M5q9ny4hx
                                        v+qLUvrdBpTS7/5P8+jpdx0OR8K+iBs8Xnywd/GT2YgbTQsj1m5xVAcDqnitmmerdAFS+xt9mshq
                                        XjasLeotBsC0m2knX2ltAWBPAPcCOIFkf4mrh0TuTwoh7C/LwT4A/qnvHI7o5vQyotVhVV1rAKJF
                                        oxUxM8RDiDEfKwDYX+Pyls6xoAohHi0Bd7rI8VjMHWhFlFy4ivp8I2IRoDcBXCjxcbhEYTNiHZCP
                                        EYsxvoZYMPIyAK8CWDuE8MsQwjUi6ZNDCM9IuBDRMjMOwMmINT7WUjvPAbA4yZ+RPIjkohnLSKHO
                                        xEia+9GILoLp9yOt2ZtsMUqHw+HQ7+GnIYQvfDR63dxN0dzN8NGoGgZV8VqTXIDMxzCE/n7EXWTr
                                        k7cAgJ1IDkXJ9aXL1+vsLrviGFJAdR+Sq5D8BcmNlTu8AOBxxErpGwJYNYTwOYA3JAbW1vX7qhDV
                                        HxHNjdsgujkl953ldFxeuy8B0XLyIErWkWNJDkG0ShDAbF3/TgCXI8ZpFLWbUMgQ6MGIWbJmSVwM
                                        RqmQHiSMJgI4JBFsVSBfUvO0GYDvIxYIXAYx/uN3ihEJ6uMiEhoBwGMhhJdDCD8PIVwskdaKWN18
                                        NICTJGYeUTrhr5Lsk3FlK9TRet1Sgi2JuLRmPf2uw+FwOBydx9AqXecvIYTpte6sC5D6wPsAntbi
                                        m4pSNqwWAGuJ+Dd05QImE1VLZ1xkFDC+kIj2SAC3AfgxgBtJfl2E+XUAjyLml95UZPR+nWJrAP1C
                                        CImwPiUBMAjR4vCkXl9Fx1UlyihR0kfn+gDRtesARKtFQIzjGK5xOhnRYpJiPbIWpCGIMQvNGusk
                                        aiZrfN4GcI0+1wLgDQXG34eY4WmhEMK5AFZHdL2ahZjCd2mT9Wo5PZoAvGSE32KIVc4bEF2WngCw
                                        uwTWSMR0wnchZtb6Ack1eqKyfBcQEFMWW/QF8BJirIvD4XA4HI7OYaEqXacu0iy7AKklmytlw5qM
                                        GGg9BNGCkLJhrQtgc7k4ddoVK4kPkqup4N5Ger2hve/p2EjydERf0LVCCBMRg9RadcP8k+T39LW/
                                        67iPyPiDiLvlSwNYQa5FjXI9Syl0hwIYr8+tLpEzVu9fhZiGdz0AX0V0aQJirMdYfW8AYiA41LYT
                                        RO4fwtxpjGciZh+bqWv3VT9eMX2+XMKiEdECMhPRXLkQgDNIjtV3n1Sbv0AppS80b/0QXdDeAVCQ
                                        1Wc1RBeydwA8EEKYFUK4AdHa8prO9ZYE1pkADlQRxq3l0lYTKKtVETEr2Djz1kREN7VrJM7ggaYO
                                        h8PhcHQKS1fpOnWR5azR57sedEhoJfm0/k7xFMmVZUUAA+QG1OGidCkFLMltAPxbRDulv22z0J0R
                                        SK2IFow1ABwJ4L+ILlRbIKbI/RjAuSQXBHCeRNSaJFcJIbxA8nmR7w1DCM8iFljcVIIrpdn9BNEi
                                        sTCi9WMdrc87QwhvSiyl/OSN+uwUxADvIQDeM2LrHyT/pXO3qC9JILyBaPUIiKmP/4WYnWuG6fez
                                        JE9GLHR4q17+EWKszi4AdtTnB0rE34hoxUpV2lOQ9rMhhNkSkK2I7ksBwIshhPcktIoANtbYfgpg
                                        V/Xr+wB+j5ie+G8A7ia5ewjh8yQIkkCsAukvqJ2bILqNFTFn+t3Uz4IHoDscDofD0TGo7MKYKlzq
                                        evEghy+6L60Mw0g+wIhmHYs6rmfIbUfPX9DxbJ0rFdVr6OD391B7JpEcofZOVlt3J3mnzn85yav1
                                        /Cx999f67vUkVyJ5Asl39ZlrSTbqc4+TfI3k9iR3IbmX3L4KHakq3tU4hHLfJ7kmyfNJjifZSvIT
                                        kheQHGE+M1hj1EJyt3Q+pdp9S30+TK+nfv9O43N75nqNJO/Td/6ovxuybexsxfVKxyIVk1TfSXKW
                                        WaNNJFfsjnF39KrfrTGsDh7wMZt/x6zK87NClebHM4J17v9QtTCqRn0cUaX+bekrypG3AE82pI4i
                                        uST5g24QINvrXGea9/YiuXo7pDsYYv2czvFDvXaF/j5ZJPUW/T1dhPp/en33jKBK+AfJYYZED1TB
                                        woYKCHEixR0O0k7fK/d3EmgKti9kx15tHEpysP28jpuY/i1m3l9P/W+xP3ASWJP0+b1SoL7Exo76
                                        zjSSq5q2LkDyYZK/JbloTwoRM/+DSD5l1mUSINcpY5nDBYiTaR8zFyAuQFyAdK6Py1WhbzcqprUu
                                        4DEg9XNzBQC36KVshcqdRXY7nA3LuOrcgViP4zCSV5H8K2J8xRFtrQW5YTUoZuMavbynCPf1iLEQ
                                        uyC6I30d0W1ogF5fBbFq9qOIcRefIGaZOhbAxiGEfUMIn8ptqhhCmB5CmCGXsQaR8JBtT6oqrucd
                                        DtJO3yv3t15rDSHMTufWODaorTOUonCaEUBpnMdrnE8C8KERUwcgui094dSk3QAAIABJREFUAOAD
                                        8/quiG5n7wO4T+1oUczIkfrOTSGE500mst0Q3byOAdBIcm2Sy6cg+EqtW5UOl44rIrqJEXOm373f
                                        0zQ6HA6Hw9ElLFCFa/xUMa11AY8BqQ8EEdyWHPJHHdcMITwoF6qKq2WmGBCJl38jxkzso7d/DuBX
                                        8t1vreB0/0IsJPgVxPiPuxAzTn0FwAohhCcBHEnybcRg8c9FXB9BrB3xPoApJp1vAQDN38GKjDqc
                                        pFbbztRWzJkg4H0AfzGfK0oQzEYMZL9WAquP3t9OhP7aEMIkpeCdTXILjXELYhHGNJ/9AXzXzF8z
                                        gGcBNJD8BYA/hxA+SXOPWMOkO2JENkUpFsTGf9xTxVgUh8PhcDjmRYzo4fMfI45WN3ALSI2Rdv9J
                                        roBYiXsqSrmgUzas1QDsqGDmYqXnNeIDJA9FzLS0J4A/I2ZuGikiGdqyrIgwhxDCy4i1NtJinioR
                                        EgAckCw5IYSzRKy3AHCFBMVLIYTP0g692lZszxJRp2qR5dpqa62Yz7WGEI4FsDmAq/XebImzvTSn
                                        N6fTay72QUxnfDuA5yRMWhErra8p4XEFYnriKxCtTmdKEBycRGU3jCclFPco8/4wFx4Oh8PhcHQJ
                                        y/Xguf8I4OJ667ALkBoKD5Med0PEtGib6O0h6WM6LqDnfVBy9Wnr3A2J+Cpw+m4tvgcBLItY+K4/
                                        gMMAjBGxbW8tJGJ8iQTH5iSXEfkFgGWsZSOEcGcI4SkR7TniLJILVQfHKgWip/iPLwPT82I4Kh3/
                                        zLnLnr+D4mSuWisak5dDCB9l7r8nADwM4L9aD7MALIiYBQyI9VZmI1o4Cogpe/sCuAHAmyGETyRu
                                        NkVMi7uaBOZDSt87wPSno2NU0JwujVh00QqN5Cd7H8ltslYsh8PhcDgcFWOTHjrvHQB+Uo+u0i5A
                                        0Lng7q6Kj7Q7TnJHEVAguugk8dEswpdS2/4OsfBem64uJu3uQJKnArgXwOKI6VyPRqyR8SBiLMJm
                                        APqTXC5ZOdpqtq77gEjzYADfQnSv2hlxJz8R8KLN2GReZ6XjY2JAGtM59WhFtBgwtakzlhP7PYmF
                                        5EpVlEAqGgtNkMtUQ2cDvTUmhWTx0mvPhRDWA7BXCGEKSvEWfRFrjhQB9FEbv5DI2AGxhsllmrN+
                                        ak9/rZVmAM8D2ADRWvVN0x92cK0HI4D7ouQSaDEVwB0kD1KVe7oIcTgcDoejYk44MnGobsYTAL4d
                                        Qvi0HvvdOJ9OdrI8NIrEttrXq3TtPohuNlcg7lwPRckHsCjS9xqAPwC4NIQw1Xz3yzoQZue5IVkW
                                        ZFH5A+Ju+O0AdpLYfBhxZ/1HEjT7IQaNTyW5dQjhqXJjYILRZ5E8D8BKAM6XhePmnM+3VDIWIrUh
                                        Kyigwn4i/f0RK6YPQ6xiPhIxcHsxZZoarf6tiBgMT0Oey+FlxBiVmYhVvCch1i+ZTPITxNomk81n
                                        ZttxMW1PRL3dWIscq0iyCH1YeokBMVj/fsQK679Q1or/AThD/bwfwP0SE6lg4q8lCm8AsD9iQoDv
                                        AriZ5AEAlgBwbghhZqWxIUaUPgvg24guXstqbmyg+5uIVrWlSJ4fQphcjXvJ4XA4HI55AKv0wDkf
                                        A7BvCOFtH946Eh869iX5HZI/JLmW3a3vKYuIufZAkv+ntGgTMmnSpuj4H5L7phSn2cxGqZ6HfU9k
                                        /VR9/zGS75D8gOQ4pdF9RO89SPIhPX9eqWGvyrtOhf1q7Miud6qGnk2Fa95bWmmDj1f9i38qBfBH
                                        VUzF16yaJP8ieSnJc0keQHIDkgtn223Gv7Ej6yebRti4hY0keXtOu6aQXNeuAZKH6L2ZJNfInH85
                                        1WshybtJrtnRdW7atJZJxduSadd4HS8huURP3keOuvgd9ZSyPmbz2pr2NLx1zNvm1TS86ttl3dyH
                                        u0mO9pVTn4u5D8kjMxN2Nsk1bI7kzsQWVCA+hpD8pREfzaYNidTdSnJzWwTOtKePCOdzJDc0dSpW
                                        MgLjeJJLkTxRfz8iYrwoyTNIvq5CgD8iOUrE/hmR/z4VCoiGDhQG/DLGIvN6g4j2OiS/LfL6LMk3
                                        SH5W5sZqyTxazaPYgYf9Xvacs9u4sd+SMHlCY7mP4mwWzo5duX53cJ3uofoqz2ketzFjF1RH5A21
                                        7Txz3T46Xq/3Zuj4uUR3/6yAaqctSeQOM/VfWk2tGiumr0k/4tVyx+rOe9XhZNrHzAWICxAXIFXq
                                        24rd3P7zU301R50tYh2/YXZtsyLgpyom17+7yI0RCYtpJz3P8jFLx6tIrpQsCzm70P3NLvTxeu8w
                                        7Yy/KeGyt4jycSRv0md/lGnTwiKpa+vav+qBH4zGHNHRT1aEE0heSfKVNm6kVrUtCYNiG9aK9GjS
                                        2JZ7NGce5VA04mS2HsU2Pv8fkheRPFo/KI051pGGjq5V8/eQzNimNfVjs55GJ5Gq9w40lpF9JEyn
                                        67U7tc5DB0RIoxFGp2bmKU+ErNTTlpCc9VWopvBxAeJk2sfMBYgLEBcgXejXud3Y9u8oW6qjTsXH
                                        VpqoVzMEtCkjCq4guRHJoV0RIua6S6hqdFZ8pOrYzbIALJYVHznn+ooW2sIkfy+SfrXcrLbRef9N
                                        cqzESKuqba8iYrwbyYl6LZHHM1SJe+POEjibUSpjBRhNcmeSf5L14OMcst+SY8mgERV5j/ZERKWu
                                        Vs0VXMe2tZixnhRz3JGeJHkayY1Jjsi4zBUqCWY349mQ+TutgzVM207Qa331uWXlgjdLgnWw3l9T
                                        FjbKta3QQRESjAvd4SS/yBEhTWZsV+1OEdJG1frFZS26VNnZXIQ4mfYxc7gAcQFSzwJk/W5q8+3W
                                        vbq3oHE+WbwpaHs1AP9BDDhePvOxFAA+UccD9Pg3yYsBPBxC+MwSm/aCbE3Q+PKIAcS7Iwbsjkkf
                                        0XE6YurUU0IIzQr2niuIOwXOK1j8M8QaHGsA+FsIYX+RvJN03kbEStmjEIOrRwL4bQhhK5IDEYOS
                                        AeA6Pf8BYoDzWQAe0vPWSscXQEFtTkHxIwFsC2BLxOxNy2S+1opSVe0CSkHNkxADq6cjZnUagVJm
                                        sHJ4GjFIuy9i4Pg7ZT4XEAPVG3X94YgZvBLaus4kxGruA3UdWzSImf6k+f0KgFMRg/+fJnkzgAeU
                                        0cpaFVrLBf6b8UxB3SmTFQEshZia+XUAv0+FD7VOzgSwpE61FmKa35+GEK5S5rWjECuvF9P9Uclc
                                        69ypzxcDeA/ApVpfKTh9hMZrAIArSe4XQnixI9cpI76D/b42B1YDsD5igHxCf5JHhxA+8WB4h8Ph
                                        cNQhLx0B4MJuONVhAP4ZQpjmAqQOlbNI1mgAFyGmDUWGPObVN5iKWARwVz1uUaD27amWQ1tCxIiP
                                        lQHcY0hZIqeJSL0tAne2MhTlViVPO8ghhBaSewG4SmR7OoCtSG6AmPWgn4jgpYgp2DZALAg4BcBX
                                        SR6pcXhBr00QqR6CmPp1sq7TWgkh1GeTBWABCaIDEFP8js0IDps5qkFjbHNTD8Dc1UCfQEwr+5HE
                                        4TuIWaImq/2fayxbzLi2lYHLmicLugca1PcBOi4iwbS4iPVqeti25bV9SJk1tZEeewL4mOS1AP4N
                                        4EUou5axELANMQIz3gHAjYi5w/soS1pB6+ObiIUDiwAOArA6gOMA/JPktgBOCyFcYM+XmVe0JbBT
                                        ljKJp1sB7CIBvXKOCFkNsTji1iGE5zoiQvIqzispw+IAtkEsyrizEYiQeN0PwKskf6l2ughxOBwO
                                        R73w0iEAfoa4OdhZnIKYjn+ij2h9T/YCcs1gjjtN9rWsr39zxmVqvLJTLZMnECxxUvapx3POkTJd
                                        PSQ3ln7ZbEhtnPsHcne5Q24nP9C5XlGA+0H6+xPFJRTlTrahApFfJTmoi+OZjU1ZTgHtD+a4Vs3O
                                        uOeksRhfxpR4EcmjSG5HcnW5bw2s8dpZSq5L26ltF5Vpe+pXc5lYliyuJnloNqtWZzOR6biiAvhn
                                        k7zAvL+tibfZNdVYaeu6lbTDXHecyaw2KzPfJPkiyVWy67mc8Mhxs1pMfTgnZ8wnlMnItX9WyDi6
                                        7b5wdyIfs3ltTbsLVh1vJM8rLlgkh8odvbM4leQKvip6x6ItkDw2J/YiiYAbRGx+IZLEMhl+mo1v
                                        eyJU/0dyyew1dVzFEKHmnOs+T3L/VLCvHEky52tUjAiVtWqk+cyNev1figE4nuRLCkQ/JQUlkTxY
                                        QeeFvEribcUl2Pf16Ksg5stJvpczbjaOw8ZTWDxK8kIF0a9Hcjhj5e5COVJa7tHFNVLxOfXeAGWf
                                        Wl2pec9VUDczcRDZGJJiZnwSXlJmtHGG0FcaJ2IruAelL24y593ZfHZJWc/aErhDlOkqVCIWrFCR
                                        IL4vJ01vkznmBqaXER1DlPr3JyQfyIiOcrE52WD4tV2EOJn2MXO4AHEBUmsBomylt3aiTU3a/FzK
                                        V0MvWbA67pzZFU0ioJXkPSQ3MkRuOQmR5zNpX7NCJLt7/225WqVrr2rETFOO+HhMoqfQ1i6zIf1L
                                        kLxf333W7J7303neN238VTmS2k0WjwLJrxnRk02Pmx2nrOh4iOQREi+jy/W/UgJepR++0N4YmnTC
                                        +xlrW3ZXvilnzOza+pix7smWmTFv6OCaH0PyWnPeC0kuWm6cdRxF8jckH5al5F8kv5Y9d4Ui5E5j
                                        TcyKkGvkDokyqZmTRW1vZYRrbwynlLEupaQSt5Mc7iLEybSPmcMFiAuQWggQkgsa75SO4DIlThri
                                        q6D3iY9xOSIguQU1yZUq1UxoMJaGxWRFeKHMzn42O1PCj7UD/WzOdRPRfITk1ikta1ukyPRjYZL/
                                        lQJeyLg63abzPiq3mnf0+gH63qDkvlQJiW7H4jFA2bPuz0lV29aYkOQ/SH6X5MqKEylrhehlP4i5
                                        bWYsNDlaWcUuLGMZac4Zx4T3JQC+qrTLFc8d5yzoeKCZi9eM6C1kxMd6spYlfG6e/0LrtCOWkEXN
                                        Lk+eCLk5u5Ojdb2xRFBThePVmrGmMbMe03l+yg4Wy3Q4mfYxcwHiAsQFSBfbvSjJPeX6XikuEI9c
                                        zGe+94qPhZT2Nus6lVLeniALQiFD2hoyu9rfk6Uku3Od3ZltzknvmpCK6t0nUtnY0V3tzGsrkfzQ
                                        WEQWzlh7Jsml5xGJlW06OIaFjOvXXoonKTcGeVahp2Tp+EpKAVvuGvPQD2Se61iD/rHtpJTJbe3o
                                        Fzl3EcRr05opZzVoZ/6WNRaZo0ybkrhczIiPl7VLM46xbkh6/cBKLTEdsIRcJ0vHyrrmsxXcU1Ny
                                        xuffcjNck+Tp+k5LjivW7m4FcTLtY+ZwAeICpKcEiDZqxype9JwKr3eNYkHXpin74Oi9C7WB5Ell
                                        XKCapDAHl7NAcM5Cb0E+8QfLdaq5AotIXszHU4x1Rdq1fLTTryBib7Gmae8p5vUPFXg+IwUttWdx
                                        4Zw1J7bKWDzK9dniPBHmhXq7laM7LCQ5P07Laf5ubSOmwRZBJMkPJETWM/NTqHQu9fdXskHnOv5Z
                                        13hD6aLtOfZTOx6QVSdUGpdiBPztZQQrc3aFKrF2NMmN7yKSOzLWWEkxTv2Ma2BrJulBUyX3gMPJ
                                        tI+ZCxAXIPO1ANlRYiDvsQ5j7Y5NxY920gbayST/VsG571UQ+R7ibV6xfB60fmzVTtD54ml3v4JF
                                        bwvI9Sf5dZ3DolyV7GT5eEJxIaG9a1bYv7XkGvNHEf6lOGel9NtI/kefPVFt2NqSw5xzN5o+r8ZY
                                        pM6SwGxQ8fjMbvWh2jlvyCOj/uM5lxhZWELt/MyamdCGpWmy5nuFrMWhEmtIznuLmPtiH0PiG+WW
                                        uJrE6weylIRKg9ONUFrMuAzmiZDmHGtHUfdOa2YsLpdr5IoZMdVoRMhouZtlRQhlCRrkv5ROpn3M
                                        HC5AXIBUEU9lN2Ud86b4WFI7q3k7yk9KuXYo1WmORWSgyONV8tdnjv950QScr9PWNXtiR1bXG03y
                                        dcasWQvnXSsTEzCM5M9Nn/JiPCxBvlFxISPaI9yO/LGRVWR17aC0ZxFJeIkxs9uQ9kRGdv1m7pVl
                                        Fe8xwVoEk+iW2G4l+QzJBfVaX5aqqlcamL4EYzrqPBFi+5jt53jFdvxK9+1CGQtQITOWya1sh5xz
                                        pXV7ONtIee1wMu1j5gLEBYgLkB7CndpEPE6xIZtoQ20R/5/U+xdpPxP025SxREwg+Z3kAtWFmyC7
                                        87o5yT8wZjBK+NSY27bQNRvL7VB3VITYwPkUXGseOzCmLT1dYzAjxYBw7oxDNq5gd5JPZ6w65WI8
                                        LmPM1LRQXl8cHRO15rVx2uFnGcGXtUTdp2C1BjufHRDrixoLx7CMaBimXRsy5ixP1rUrlBBhcfv5
                                        CkTIqiampDXTp8kZC+IrcpM8TLEkhcw911DB9X6TETx2Da/eU8LfBYiTaR8zFyAuQHq1AFmJsf5X
                                        e4+h2hRbhDGL5IokN2DMEnpyTlxje3hWsbv7y916UedUvWNxJhK/R44bS3KDuli7vIXOCpAseTTX
                                        7cNY9+NC7U7bgPOGNiwf6fsDu3EMfqzrz1TcwKpZssU5a4AsQ/LKjMtPMSdomLL4bGaDynuDtaM3
                                        tc8ErWctIs1lhMiHjHVIFq80RiOzhm/Tef6oH9SC1sQdxu1rLbXrz6YN/01ZOjrgjrWBuR+zaZuf
                                        lavW8fKNHZK3XisU5wXd6w9lREiyKl1DT2voZNrHzOECxAVINwahZ//vyctgH/O/qDOuWz9RWMES
                                        vmlWp+RNP+4vZvzJk3/7TSSX7QkySpOiVDfJkiTPZCnlaWM7pGxtuad8rZId5QrHYgjJ/llxkt0l
                                        lzvK22XcfCZkzIY75ZBCvxl6QEibv8eZZArMiZWw7nEPyqTbp5J1ZNbsKiwVknyV5F+NNa+Z5C5a
                                        45frtVly66PW7RIVipBGrZntc6w45zBmWlsgI8Y6lTrX9G1N9SFbFJMkD+8N4tTJtAsQFyAuQHxu
                                        en0dkL7ylrm9i227XUHvy7l1pH4WZl+SZ2QIRtolHk9y766S+wp3kwuW5Jcj6eZza8v95TO5qHSL
                                        dSa7G2zbqOfLMxYyzLN6WLef8cqEtHDe+XuROF3GJhPoLe3W8z6KIfpbGatUMbPDf55Mwl9mTatg
                                        fFaWxaPFrIfXSe6g9882bnlHy9z8sLGELFHJ2mAp/e939f2DZbYelF2zXV1nJp7l+1rTszNCronk
                                        GpWIJ4eTaR8zFyAuQFyAdEM/BmrjtztwnVznF/YVUluCuX0bWa/OUqBvVQqRpTiRNrJNJcvHKLPz
                                        PIPkd9sSLZ1oQ8i5ZkH+hR+Vcbey43dSshr1RpLGuYtR7tVbBZT54drZxGVMyBEiNvHBFnbe27iG
                                        tY6tr/WxpQk0/2nG4nKwXl/CmJUfZCx62W5wtxEYDWaOgoRW6IH7cLDZdcpmxbqu0oB6h5NpHzMX
                                        IC5AXIB0U3825dwlDDqLZpJHkhztK6X6BHOkgr2bMtYPMtZaWLxeCLSxQCyqQNv3FGj7sdp8Zp6A
                                        6OpOsI4Lcs5CeC1lgp1vVABUn+5uS6XCid1UM4Qx1e3tJtvS2r2RbGaEyOKMxTHzRKO1hrzHWGyz
                                        QyIk8/pp5ty3GOKe3JcWYkzXfBwzRT0rvHe7xdpRwf22qrJ9WZe1NG7fdAHiZNrHzOECxAVItQSI
                                        +rR8F2JDyuEnifM6qiNAji4TeP6qgn+67NbUzeR6MGNxv6kkt9R7+5q2X2BcVUIXr5fI51qMKYiz
                                        cQPZcTvMZraqJ1LWkfEwu98/Ni43JHk3yUW72rdaBd5nrBXrKV7DBlczJ8vUP9MPKiurGdJX6+8H
                                        5hx/0nu7kJym147NG8d6s5QZV6wf5mTFSlakFV2EOJn2MXMB4gLEBUi1BIj6tbTxauhOHEyvqt7j
                                        4mPlHJ/4RDAuY0wb2lBrYmFjREj+Q+3bWe8tIAvOTJLv6r3zu0J0OWfBuG9kMg/lWT2uIblWLYWH
                                        dtDXJrmhyPXyimXonzf3FayNrYz4aDVj+5OOuuPVU6avjDVkqERjudiQJESepql/005cSLIabENy
                                        EslL5B6VxOwucm/8ZVtZt+povGxWrAdzsmKRMWVvXxcgTqZ9zFyAuABxAVLlvo3Vhnl341GS6/nq
                                        6ZnFOICx/kYe8XqQ5LhKdn2rtQur4+/UxkP09wCS16fXFJCbduvPM5mDQieu1ZexqGDerrgdr+9Q
                                        ReZqSRwlQO7N3ECtjFXnD5UwadM6Y8TH4sYqMCUTfEySW7XX13KiQ6J2mNy7+teSWJvn68p1zvaR
                                        JnCcjOmhDzcWgUIFIm7Z1MdMEoMxJtGCdZnrL7evM7NxHrUWITpupPHISzO9fT0JJyfTLkB8zFyA
                                        OOZ9AWL+N/UUvk9PO9+9O8Daoc1zvWoi+X9ZklbD9iaidqza+Iv0ugLkSfIPmR/BVzKWkEKF1yqY
                                        nfGrDYnPS6/7KsmN2YlCiD04Vsdr/mzdi6IJlr+KsTr30Lw2mx3+k/T5ZPX4I8nXDOF8lOTI9oSM
                                        EXIrKTj7NAnDq2U1Op+x4OPYWoxhpp3DSf6oHZesJpK/oOrOVCJCcp4X2lh3iyirG8092FAnvxvJ
                                        rfHCnDFpIvkAyREuQpxM+5i5AHEB4gKkBn08sgf7dGOt+jUvLsahmeDiJD6KJP+t3elG1t71Klkj
                                        ttXO6zWGDO1nFsdEuZMlIjdO1oAdKxUg5lpjjCWhnMvVeSSXyiOYNRaVOxhS+AXJJ8zf401/5nIZ
                                        M+fYUJ95R8cfS0RsTPJNxsJ9RZIn5mVeMucZpExSl+nzs3OyhiUsUuPxK5h1tVMbAeqJdP+Zmcrn
                                        bfzoV+RexVJhy6/KdWuGWb+NdfCbkVyxRkrg2/GYkAmudwHiZNrHzAWICxAXINXs4wDGmms9hWdJ
                                        ruyrqetEdc+M+0RKQTqe5G5sowBgDUjhKsYN6BWSu+r1NRgrld8lMbWGJWsk+3VC6KzBUpG4rPho
                                        NoHmA+uJaJl5XUekcIKsFytLUJyhrE7NRlhQ1hC7O7+AlH4a74slMpIr2146x7s6rpo3DhKAfzA7
                                        5c1GwDUbK00Tye/X0xjq+WpGhE7I/AildXF9EqHdYaXIuIT9U9eZlIRinVgjk/vZwWXcEptIruAi
                                        xMm0j5kLEBcgLkBq0M9NerhvzSTX9xXVeZK6GGPqMutmkgjnpVKRNa3SbXZbh5J8nrHuhk2B+/08
                                        4tbWDnMb12o0C3dCjviYYBbeVp25RhXndhORwiZlChto3KrWZ6mew2emX4exlDL4APP9F7VWgo1H
                                        0Dw063PnWSuIhMpehpymyuMfyu3qNLlc2XHdpM7EnE31fHYZETJZx1tJLmfXUSevmdbgUMbMXLbo
                                        39NUoaR6iQfRnN+V44pFxa/09V9cJ9M+Zi5AXIC4AKnBJtllVRAhq/uq6hxJ3T9DqqbI+vFoUna1
                                        9js3JPBStTGl2z3IiKXzqQrQee1lZfUUkuVjc5Kf5IiPRKruJblSNcRHJljZZv8qm0nKzO2upv0X
                                        yw2qwfRzAePDP9msge1FuF/V+DYZS1hDRhQuIteu5IKzod4fSPIYne9DI3BvUIBYP31uHyNKSBX/
                                        qVNBN4DkESY4vTnHEvKM+hc6I0LM+C7DWE094RyWMr7dI7fIeshIl9q7PslPmV8bZMN6m1Mn0z5m
                                        LkBcgLgAmbcFiPq6URX6OJ7k8r6yOkaoRotkZmM/mhhTadaD9SO19Qgz2ZeYANfNTUD0XcYNJnTw
                                        OolI7W3GojUn49PfSC5RbULVyQxTBxli/DvFbqQMSza71wVGfDZpTVxu3KVuyMv0ZM5xhMjmFJ1r
                                        CZZqhrxhyOiBZne/UQT6Nl2zleQVKbtEmYB4K8AKtRh/lup3WDejbHD6MyQ3Yydr5jCmT35J55pB
                                        8ii9vogsUa+zVH+l1psDdk4uzoixJDr/SnKA//I6mfYxcwHiAsQFSJX72k9JUXoaj9c6frW3LcJj
                                        c2I/kpvH8rWO/TCZdsYyFmy7h6UCgE8YC83iIrIk+ZYCdztSaC+R4gNJzmpDfJxCpditBvmVAPyq
                                        sjmcwlgh+0i5Rm2sfjeUEylycUruOz/XjVjIjG/Q6zdkyGNRgmIiYx2RUM6ypHb+z8QNPWssHyT5
                                        iOIokohoNC51jxkBckzG2hNYR4X4MnEhG+VYxuz4/U/iuCJLSLrXZJH82Ii2HTJib4zGbQuSu6Xv
                                        1nhckkVujElKUMyMzY7VFu1Opl2A+Ji5AHHM3wJE/d2nSn09tx6SxNTzwksEb2wmENgGn79Nco+0
                                        S10n7V5TRHeYgnLTjv13jMpNO/n3qe3tFrwz4uObGfKdjfk4juTgapAos9u+iFzhmNlln63Hh4pL
                                        2CjtMJvvNshaM0vze0oeGTbEdnmJh+RKlcTDVbKSlCuQl9bTtzLCLX3/BrNb35i55liSD2uMW0nu
                                        kberr+uPlMVuRQXTL5Nc7molREiuZYLT8ywhzxsR0lDBGtwqE+uxcnrfjFkDS+mBJxiLX72IkB+W
                                        sYLcSdWdcRHiZNrHzAWICxAXIFXs7zJV7O8+vsIqI7eX5JCnRL5fY6nac2MN27m3yMs/lW0n7aCf
                                        b9p8kREHhxniVqn42JLkdM6ZStRaPg42nw1V/IEIjEVvxsv1ZoJ52B33opT3qub7w0jebfqzv+1z
                                        VoTocWbmnB+S3C5PFOQQz5EyQdqg7CdJLpa9riHTWzHWuWjS9TbLtGl5WXvOUF+aMjf6hSSH14LU
                                        mvW5nNpWzhLyQupXG2OY3JgWVCD7rcmUyzmrpq/CuYtL3mzc2WqdKKJBfXg5I8TSet3NBYiTaR8z
                                        FyAuQFyA1KC/11Wxz2N9lbU/KcPld0/OXeOAsoRs2llf9q6QGWOVIEupcEnyZL23ngjOF8bNZ4MO
                                        XCMJii1MwHme+Pgma1Bc0BDcDYy1J8UXXMOYRepx09ZEePcw1oV3jVvaJuVIsBERy5Kcaeb/QVZY
                                        M0VE+RxDvj9gJhVyztjvYbJIFFlK2bpG5lzZeXlW37mmmi5xbaxyO49DAAAgAElEQVTTMSzlG8+z
                                        hFhrRkM75+zPUhYyK9oOMValD0meSvK/+vsE254a/ZbYBA4fZ8R8SrX8IskFXIQ4mfYxcwHiAsQF
                                        SJX7fEgV+3xRvXgP1e0C1HFhkn/KESGtRoRsVq14ELPz30cE6zmRsm3Vps9IDtbOMxmrdKfg12Mq
                                        aachS5swP9tVEh8HVdvykdPWIRIaqX2nspT6dCn1+Q0RvERQd9KcpTl8gOSybQiQtBb6yeWKxvLT
                                        bhyGGc8NWaorcjdj1q1CTmxKIthHi5zOJvmUvn+EWX8pIcIEzpl1KrkN7lMHxLs9EdJixmOltkQI
                                        cyqky1J5Wd4/XLneTVV81Pq1GgsTS7QdY4rsrBvjqzp+y/1jnUz7mLkAcQHiAqQGfV6P1cU6vtIq
                                        EyHDGbMelRMhb8gS0tDTqs60qb/cwCZqt/8bJvZjmFytSHJdfX53Q2xDBYRxRUOMWnNiPg7oSTJn
                                        hNYcjzKf/Z4hsmcoJqLRWC/GmiD8JACeMv16lDHlbpuVuBlT595t3KdGd4TUan08LPL5JsmN8gi3
                                        maeUKWtWJg7pQ/P3XSR/RXJHE+PzmY7L18NuekaE5LljzTbuUsPbGlPOmXZ5K8WRpHG5UkLsC+PO
                                        dILefyn90FfZUmfd6aa1EUN1mIsPJ9M+Zi5AXIC4AKlRnxetsgC51C39lRP+hWU2yoqQRPZelsWg
                                        GiJkQd0gu4lETxIBfUKuPfuJoN6nwPRKCXIidovJN7+c5ePAnrJ8tBcYb983x41ZKuR3c0Z8NJox
                                        uywzZ0mA3NXOzntywdrGjMUfOpKEwJzjGHOOH+atFyNATjACJBHXRNwfU+aKRcz5DzeE/lbWUWrX
                                        CiwhSYT8WWu2LcGZSP2p+s7nJI/Qa7vqtYlaxw2MBSXfNFauasUppbW3qe7Rcm6MR7j4cDLtY+YC
                                        xAWIC5Aa9rkPq49lfbVVLkKsu0c5S8iGPRGYzjlTtD7CmN0piFgvKncdi/dSoI/IaaHC8w9iTOeb
                                        FR+pv9+uhhuL6Vd6jMwSakNEl1I8R7NcXPqU+dwwibI0Z2nezmpHgCQXmn8YK8oObX2nDdK8vuJI
                                        SPJfzGTnygiQHxkBkmIGJmvuFzSkvq/WxbGGzB/Xxhy3a1XqYRGyktZTE+csVphEyLlyd2soZ5HS
                                        oz9LxQhPM+//Rq/dLqvVCJZq0xSqtH4bjPhoasOSeKj7wjqZ9jFzAeICxAVIHfT7b1UWIAf7auuY
                                        CBmm3e9yvuzvkxzHdlKLdoHQHKnr7G/eu9fsij9F8jySS1e628tSlqEGY+WZnUOWTmKpmnrooXFe
                                        UX28QkG5TzHWjHhcxPtQxpTDfc13hskNLYnAZbLigHNW0H7TzFkzyb0sQS5Ddocp6DxdY0hHxsGs
                                        n4VI3qjzzCA5JnvtHAHyhZmTA20QdkaY/lL9aSG5vSXc7EShxh6+j9YyAdjNGTHfTPIYa0VoQ8ys
                                        YO7DnfTaIK2XCzPjOlcMSQ+Lj41NzEee5ePwWsdQOZl2AeJj5gLE4QJE/T61ygLkbtZRLbPeZAm5
                                        NEeEFI071grdJUKM+85SEjgkeb8IznG67t7aNR6YR7jaI0w6/3E5lo/Uvws7Sro7Ma5jK1iwRbXv
                                        UpLrGuH0K73/PJVuN8e1KfVzX1kVkgDZqA0BkgjidiYg/4LOjANL2bAuNOR71zYESIoBmSnXuiNY
                                        KsiXDVxvVJzLeJHdcTnXHyBXwpF6LEKyfw3uoyQetsgQchpLz9sa84Y24kES0T9Qc/mqifNIa3Vt
                                        xQXdKevXJVQ2uJ4g/Rmh+2oblsRv+Q+vk2kfMxcgLkBcgNRRv4+ogRvWaF9xHSdPI1iqjp1nCXmV
                                        sSBch92xzI52yATdXiJydqu53pUSIv1tbEQHA6MDYxatWTp/tkrzDSSH9fROLWP2rp8YUtosa8N1
                                        IpDjDalLu8pHipQny9CzJLdqQ4AU9MM/08QPLFaub5qHRhOPQZJ7shOpl42Y2Y+litjnZ9tqPndk
                                        Zte8MWvNyATI2wD7kYYI70jyO7Ig3ar3n9KYniECv1iNxPzeOSIkpVR+wsRtlLNONWhc0obATea+
                                        OctYjyxmkNy5uy0hnLOA5KttxFAd5pYPJ9M+Zi5AXIC4AKkzAfL1GgiQTX3FdY48LcO26xt02RLC
                                        OVPikuQpZkf+M5LP5+xyV2r5SMJmSUOOsrUJnjUuTaEKYzpULmStuv4FIpn9GLOR7UTyepZSz7Yw
                                        ZsE6Te1+0ZDLchaQrTMmwNzaC6ZNfVhKxTypnIWlA3O5nAnyfzQJixwBsqsRg29KZJRr47Jmd/0G
                                        WXkuMBaRSrBYNUkxS+mkj24jrupGlklXnOn/gnK7+oliYv5kzvUoyaMk1C/Sud8lOaK7+mvmdozW
                                        YDnLxw9dfDiZ9jFzuABxAVKHAmTrGgiQQ33FdZ4wL82YeamcJeS1Si0h5pxLaMd9tIjXQMZ6H68z
                                        potdUf7j75P8VATuDFkKbrLxEe3cYAVZTm7MtLnZEKb1ununuIL+L8xYRK9ZBHrNbJA2yR0UjN+U
                                        Q/R2KiNAUjzEAebz55Ls144AGS4XKEr8dKm4n9r/SvrnTXKpDIlNBHU3084nmZNG1ojIdVkqrJgI
                                        fIvZeX9V7mlPMNaPeUfj+4rG8NRqu2NlrDd5cVWT9fdJJtC+rViWFJ+0i4mZ+UV63Xzudr1/SHes
                                        bTNvy+t+z8ZQJXF/ck/HULkAcTLtY+YCxAWIC5BO9nuDGgiQM6vVv3nG5zmEQJIhhPA2gP8DcAeA
                                        EQAm6SMNAIoAxgK4FsCKIYSWdnbNU4aeEwCcAeBnIYQigP0BrArgBwCmAvgdgIsALAZgAQDnAfgh
                                        gG0BLAMgVEByCgAI4DgAOwNoVZsBYAqAUQB2DyH8V/0sVnFMPwFwMoCBAIYDODGNjcavCOA2ALsD
                                        uAvAdLW5onsMgPU5nAKgSLIhhMBsk3RcGkAisZ8AmNEFi1YIIcwG8D+9NEZjnYeZpl8NAPq0ceoR
                                        pr3NAD7XuDwC4E8aqw0BbA5gawCPAhgCYFE9/10I4YtqEmMz39MB/AzAY3prqo5DASyitb1NCKHF
                                        9DHvfJ/r/tlO83x1COEnAKYnVy199EGtoa9k5rlT4iOE0CpXset1v7cCSNeaqDk+BcDZamPIWWsO
                                        h8PhcNQSX9Tgml91AdJ5AlUIIbwF4CgATwAYYERIAUALgBUAXEVyZZGVhjLnaxUZegzACwD+qqDy
                                        nwB4IoRwg4jL2QC+DeBgADsA2ArAWrrOBiGEmal9ZUhTQdfaAMCPRJjS3EwSIf4BgJurTZYSKQXw
                                        isZ0IIDNAOwkEUS1vSGE0ATgEImQoepHm3xRfVnFvPaZBEFba3MZ8/wNjW+hk+OSMk49qb+XALBS
                                        5v5I530fwKtGgCyWcx8l8rykGYMFJCqOArBDCOHXIYSXQghTQwif63obSajMBHBiCOGTWhBjI0Le
                                        l5AfAeAjiZDUtyEATpWliCxfH6SgNZLI/7P6bH9dq4XkUABf1xh+2BUBku4jxoKPtwEYp/u9wYiP
                                        URLTZ4cQprv4cDgcDkedYmYNrrlWJV47LkDyCVRRROQNAEcg7lgPQGkXtxFxt3VVAH8iuQrijnuh
                                        nAgJIfwdwIYhhLtFIpcEsIpiI1YMIdwWQrgohHB5COHOEMLdIYT/hRAmhhCmtkOagkjcQgAuBjBY
                                        BCyozQMA/B3Apdpx7nFw7roUaWxulhAZAODb2sGmIZMNEgPHA3hR35tVwSUXM0T/3QzpRw6530Ak
                                        +F1dB5rTrmCCbY/WQ7YNxYyoCm20cXm18XMAvwSwG4C/hhCmmNiXgjJsnQygr+b+iBDCy7UkxkaE
                                        PAlgb0SLwRTzmzFF4voU3U+Fdiw1EzUuG0mozpBQCPqBHSSh8K+0ljqxZht07y+PaOHMs3yMAnAS
                                        gHNcfDgcDoejztFao+sOdAHSNRESQgjPANhVhGmIESHJErIhgAsBjEzCpQy5aQwhTFWQ7PEAngLw
                                        DoCjATyqNK5jzOf7mQxPoR3xkd4/HXHHNlk/pgKYoXb/PIQwuacJUxIcIQRmHq06TgTwF7VpaQDr
                                        JKtTEmuyJr0F4BwA09q6iUxfVtTxdRHFcgLkS4Wu42cZ4dDJ5RKIuMvfrNf6IrpXdUbUpPkcq+On
                                        AP4RQpgBoI/GtxXRYlMEsCWA1RCtApcjug7Wwz2Uxv96RAvfKJQsiUP1A7UTovWC7YixqxFd5XYB
                                        8AeSp5PcXmvqCwDfBXBwCOEV3TMrdnDdJsvHEhIfqyDf8nExgN+6+HA4HA5HL0CxRtft4wKkiwRK
                                        xORpiZDX9Ja1hEwBsCmA8+VaVc6dJL3+bcQYiMMArC+SvaAI1NOqEzEqhDBTpL3YDslJJHQzAEdq
                                        saU5+QjR/WX3auyIW+GhIOThJBc3jxEKir5J5G4YgN0kPuw6Sm1skoAajOiClCsqZAH4wnynuY32
                                        tWYCmANKbjtdvVFnGMK8MKJ7WFHzXjTtS2JqKQAjcwRli9ZSMp0OAdCk92Ybl7aizJyHIMbADAJw
                                        cQhhhglkr3Wl9BQfcw6AhzP3T0H3wvcALKWxasjcg626B1/RPTITwKGIlpNbUka6EMJdIYQrSW4B
                                        4BYA97dVCyZHfBSViOBKiQ9r+UgujH8GcJLHfDgcDoejl6BWHL1hXu5ctURIsoQ8jRifMSRDooJI
                                        8eeIriEsQ3Ba9d3vArgqhPBMCGEKojsSAPxRpOcXAB5XGto2s+sYEroA4g5zwbRpEqLby68A3F4N
                                        wiRivLgqup+FGPcyQY+JiFaf0yXYxkscjQUwWO5XBXsuAP0Q3a9GILojwRB8Oy6LomQpgREjxTJr
                                        dZg5zyCJAnRhfGjWxHRzrbwbsFXiCxJVi2T6leJQBpodhI8Q41po2pj6siqAdXTe6xDjjJCEa7lH
                                        JcS8G9dEigc5UXM5xfS5GcC6AE4ol7nM3INXIwajn4cYn3ExgJm6xvYkbwJwjz4zQuMyx5opcw+l
                                        wknXIAb0W8vHVJ3rYgAnhBAmufhwOBwOR2+hsTW6blX+RzbODzMoovKB/pyBGMOQCOybiG4vM1IG
                                        nTKn2Qdxx3tzkt9D9Fc/GMDNIYTvkDwX0T1rfwAHAbikgqxXRcTg8rVQynqV4j6eA3BBT2dCSoRM
                                        xQJ/CWBts/Anmo8uof4BwMdaoBshWgKezzn1dLOI+7SjtBOpt1mmymGQWbf9u5FMTgUwW89HlhEg
                                        IUeQ5N20CyJaBwDg2RwxlSxNu5ixuTyEME2CdKjaMFzrJMVKTNLj05TYoKcJtbHYPIyYoe1slFya
                                        UpD9jgBuDyHcICtIa845CiGE+wDcZ+7J9UheiJgFrA+iS90jAH4D4DGJrGLbzQtFkqsjZu6wAe+T
                                        jPj4SQjhYxcfDofD4ehFqBVHb5mXO1c9+VjaMd5BL6Vd+SmIu9hvIe7ItpYRLhQpPFHEaxCAcxGD
                                        0c8A8A9d5zUAh5O8CNHVZprJApQ9b/JZXwUx05DNejVD7TsuhPBBlQjmVgD+o5deE4GeprEZgBjv
                                        MU1j1hfRRamodq5G8oUccv6eIY8rGNHV2o7Sbm9nfzhKQetN3UjCG8z9sAqiBWdaBd/JEygjEa0b
                                        gNL72jaKNPdBDPDuC+ANAH1J7gZgPwB7alyKKMVXFMz5f0XyPwAekotUNe6jIskrEFNEj5NgG6I2
                                        jQJwDMmHyhF946JVUP/2RYwhSSgCuDOEsHcH5jS9/6DGcFkzXmmT4Q8hhI/a2VxwOBwOh6Pe0KdG
                                        160KryjMDzMo//BD9OdQHYeIYP5D7lR5Lljptd1Fwo/Q8dciOyPlUz6c5DYktwohPBVCeC6Rrjba
                                        FBBrLQxFKetV2rU9C8C9PTwmqTbJaImPCSjtsG+PGKC/h56vAWBjxPoVk0S8qccmGqNihhR+IXIN
                                        xODrckHdoULlnT43DNHqAsSg9e6CzXBVRPsmyGaUXLay99Mo049Pda4U15FEy8oSPCMALIQY7H0d
                                        gK9pLt4zoqgB0ZVrosb/RER3pR93tQhjB0RqCCF8rDU7QkLZisrNARxlRMZc600CoBHRtXAnRIvH
                                        JYhuVx8D2IjkUkr6QCVzGFCufyYBQjOAv2mNpDlMlrRlMnE8DofD4XD0BvSt0XU/dwHSdZKd+rcB
                                        opvTRAmPZvX9vwBuFUFpzSHoKej5GESXqLsALA5gskjlgSSvRKwhcYcIYaMqa5eL/WiQMPk6YmpW
                                        m/UKOl6Y0pRWwWVkU6N4ByBaeN4OITSFEJr1+CiE8FwI4WcijhehFLS9JclBOe18H6Vd6CKAfib1
                                        alZpJ1LeaARiubVprzOmG8ehH2LAfBJB7RHWdxDd92yb0i7/wojWtVYA4zXfISOktpGITZakIqLF
                                        6XPEoPRGxMDpM3X8TMJmuNbxEwBOA3CIKejXYzCuWA/ouiNQctH7XO3fAcA4zXNjnlhQNrBTEQPG
                                        twohHBZCuEN9XALAIYop2gXAvwGcrPu4XAB+ukduRrSIpcKY6Yf7UAALmvY7HA6Hw9Eb0L8G17yp
                                        Wt4C86wASdXClblp6zIk9n7EHeq8IOZEbFZDtACcIvL4EKLrVVFiZBcRn7MQd4dbAbSUCWi3NT9O
                                        zpDpKSJ1h4cQ3qmG65We3oqY1WuMCPgSAK4muWgScaZmRUMI4R3EYPwzzBpaJ33WnHcWSrEhQ7LC
                                        wnyuCdHlC4jB2wu00/QvUNrdHl1m7jo0FDouZO6HJ5Bfv4SZ72VdsJLQWEJ/j0cpS5fNftVP6yp9
                                        J2U/G4zoTrQzgDUR0zyfjFi74mN9PmV1WgfRIvUYgGKVYhuCanRcLvHVV4I5zdk6AL5TztplLIJX
                                        hBAOCCE8RbKvRNsZiHFa3yF5L6JFaFtEq+PwjIiz50ypn5/RI81TEkjbo5QEweFwOByO3oKBNbjm
                                        49W60PzggjUa0ec8EbdmEaa7ANwbQpiFnFgYQ5b+hxhkew/ibv3PRQx3RcwANDqEsG4I4YchhHsz
                                        2Y7yCFwR0f99VZG0BrWtL2Jg+63VHJwQwuQQwiWIFqIbEHfv10Us0jgYpUKDRUP2UvX3pxF38bez
                                        6XiNy8sjusxKiNmu8q7fgri7DwDLiTgih2ymMZ2IUkrl7qwSatfAzIzYSPdJqg+ShMPUjOBNrlbj
                                        9PILiK5Uqf1p/oejFBeTxMeTiGmedw8h3BxC+BDRxasI4KeILnFNiPElbyK6LR0TQnikLVe/bl4r
                                        KaPVOxJFWVesosTTxvpsY1vn0fNZ2m3ZTOJyOKI7V0H3wzcR3c/adGnUOS7OCMMkkPbsBqHqcDgc
                                        Dkc1MaQG13zFBUjXyVIiG2tLeKQd7UGIsR+fAng+1W5o4zwzVOl8qkj4b0MIF4QQbgkhvKTK1oX0
                                        KHceY/1YFNGFhZnxHwHgvBBCczWz9Zjig89IWF2HaPZbDzHtri2WmIheEhj/UT+WkVJvzVROf8uI
                                        wGUzhRetX//LOg5DDGoPKJ9+braZr2kkF86cqxNDwKDxt2maiznnHGr61ipBkEREwgCJBaid000y
                                        glSYchWty1kiyf8GsEcI4XrEOiIFQ96/iehG1KQ23gRg2xDCHT2dIa2d++o2PQZgTvfBoQCOkJUn
                                        z+XuywKcJIeR3I7kPRqDZTQmNyHGFu0VQrhF49ZWMF4a/7sRg9GT4EtzelwqFOpuWA6Hw+HoJViw
                                        Btd80wVI95DrAQC+oT9HJQ6F6MJzSwihGWXqf2TO02CCtvvo8WWlcwmTYjs70Wmsj0bc5U3ZelLg
                                        +bmIrj9V3ak1xQcLqnR+ghYgAXwfwHo5VeJTJflX1YftUHJzKcTThlYJi1TXYyzmzoIVTIrXhDGI
                                        1oiWDFlMY/sJSpaPFpTS3XYVI8zzaUkgZuZiOEq1P4ZIxGZh41LelYWtIdOHr+jYF9Hl6lshhAkk
                                        +6Q1JMvQihKBzbr2NQC+HUJ4w1SfZw3uqxBC+AwxGcMQlKwgQyXwNwOwubEIzXUvqJ9bS8RsoXXy
                                        dwDbhxB2CSE8JIFymMTJAelezFvDer0ZwF+NQASixWwqgE38f5nD4XA4ehEWrcE1x7sA6SJB0tOV
                                        Ed2npmb6PBnRBQvISb+bQ3BaTQrV2XpUUuk8tSe5pyyFWE/ECpVkmbk8hDCrVju0SWSEEN4CcCxK
                                        wc7Ha/fZ9jP1+2GJpgUQA/2BUvpYIJrykrjYFqW4GnPZQJQsINB8DclJ45oyHv0/e+cdZldVvf/P
                                        mpn0SggkQCjSIiBVKYJKsfG1IFYQCyCIChZU7GLvgigq+lOaoggqShMFaQLSew0loSQEEtJ7mZn3
                                        98da27tzuHcyKTOZmez1PPc5M/eee8rea5/7vqvOpxYXOQLPw0nEcrXUJbY7ZO/NC+LQVDn2VkGk
                                        AJ42s6V56FXM3X5BZiYTPS+SjmV5DIdk4PjjZjYz8muW11RG/fC8iEScbwc+Y2ZTE+ntAUvtNjzs
                                        aVAQ6fyh+cnoCF/vOtN7/w4Cdh7wMjN7n5ldK+lVks7Eczp+gye3HyGpf4NCBmRk7FI87yZPRh8G
                                        vEHS8JKMXqRIkSJFeols183nOyOqwhYCshZkzwCsaUDT9q/AzO4MdYrzHIWHmSTLcMpL+RYwYV03
                                        Ssti8/+NV1/aNMbwTQHcWir7PYVXQBJwJGHZzno+zMJzIATsCmyXEtor4P9RagnrW1OrzGUvvkRb
                                        DjwT/29JLZm7aXXnJcY8nXM2XvEsv75EIrfK3v9PnVCxZtyan67n3oxQJILycmCLOMZFZnZ/eD7a
                                        Ysdk4T8Cz4V4Js7xMTObUkn0X1d6ksryLgF+HQB/UHbfqXjDCnpTWQuY2SzgzWb2QWChpM9EAvqN
                                        wDExTqkXyzNB8poaGQnis0fycaeWjH4EnmNUpEiRIkWK9GgJLPCGbj7t37vzZE19cNJSZ+8NAgwO
                                        o1aSc2iAy4dYsfxrV19Pe+R+fLIy7gm0nRcW9x4hEf7z2wBumwPvCRCZW5+b4pqvDIA8iki+Tonq
                                        cZwLAkRagMActCevxvPAXRloPCKO0SgR/WY83AZg27g2rc7cxHYTaknojwaxSteXKj/1Y8UE+ftz
                                        chIEYjS1JolT8apOZKFIhhcvGBt//z0vAZ0l74/EK42BV9Q63szu7UGejzz06168MMMwal6QeXHd
                                        740qdA1zQcxsfjTvvBcvbHBAjN0P8dK8Q3FPywmEt3AlRR6WUusJkhcPmA8ctJLvFylSpEiRIj1B
                                        RrBiaHhXy/wMhxUCsrrYKLZb4NVvplDrfN6MhwXdEUCuO4BIsnwfjZd6zXM/huEx/pN6CjDKQlSe
                                        xMsKC9gHr5KVj2+61svxXIxtgHdlFvz0+XW4VXpoEMIReIJ3suQnInNDjInh3pIdYr96lZTuz65j
                                        LDCoo9CcDiRd6y7USsm2A5MzMpCOOTjAcVqoD8f1WzbHr6UWinZJIidBstrw/Ig9Y2xuBG6LYygD
                                        0MKbZu4Q758PXNSDyX478OcYk2XZg3M+Xulr/woZWEHdYtxG49W9LgqisSNwId4n52ngfVEMor0T
                                        lbAA/hHr3lgxGf3DqXFjkSJFihQp0oNlo24+3+fNbHYhIGsGoBNAeSUr5n4MDYA7A3guYu7bcjCV
                                        vdbKuGS5HyOAw1gxP2JZXN9FeVnSHjSOwqsKTY+F8KHq7cX2UTyROIUxDU/APe5/GTWL9M54tSdl
                                        wD7NwaXUyt9uH+ezCklMfz9CLTTnVUQ/EFYjDyTG/TXUwqJuDSv6/0KdYp+d8OpVxP1OzUhKaiaZ
                                        3KXzgP9kOR+JWOwXJMXwamPLQg9VqZJ2bFzLcOAUM1u8rsPzVkJWHwZ+jocTpuaEQ2LMDqNWlOBF
                                        azXu6TMxNoeb2Rlx31fgXrVjzGxiFH14uaRdsrVVd83FQ/T3Ff2aHnq1czanRYoUKVKkSE+Ucd18
                                        vku7+wb7ahL6EOD9uNUzTWJzgNZ/RB5BCr9pltSScgHi1b6WQEoCjW/BrfqK65gSpORn9IDcjwbk
                                        g0hIPz3ePgDYIktWT5WH2nEvh8U+++YEI8byL8B9rGiFbs9AbJOZzcRDblJI0hHA+Cy2PycML2SL
                                        ZQywx0pK9zYiHm14GFzKDViAe3RyspPG413Z1+/FKz81Z5+/FO+BIbxZ5b0ZQUljdVysuQnA3ype
                                        uNRH5UMBvIcAJ0WOiPXksKEgFxfGvyOy9SbgdaH7dStYxfefNrObcY/XMLxL+ljca3i7pCPx5od3
                                        Aj+NsK5G6zO9dyVeWSvlpCTvzCvXloGhSJEiRYoU6SIZ343nOtrMphYCsmbEI4GPbXGL6vwKmJyC
                                        x5ODx6U3RTWrVkktES5zkKR/RhO+prwE7+oAswBdx7KiJX9EgPHLs8pHPXUsL8XDjzbAY/pXyM0I
                                        8Hk57pUQ8MEIm8qT0afjuSCG9xc5AfeQNFfOdzaejG5BLL6azpeB8OYgDjdRywNpaGXvSPfjeNvj
                                        XgnwXJSHapfkuSySxlBLLn8UuDgjDynE6iN4HskCvKLZAmp5H4pzJO/HJcCzqT9I5inbOO5lIzwP
                                        4vyevuYyYjQBOCP+Tusu5bO8P/qCNNK1pjACtON5IK/Bq9RtE6Tj3DAozMZDslo6CMVK3sQH8EaZ
                                        uReSIESjSzWsIkWKFCnSg6W7EtCvpYeGefdKAiLpWEnzJE2Wy5zYfklS/xx4SNpT0nckXSbpr5Lu
                                        iX13rx47SIp18lpSV/BXS2pXTebF608dgbIeNJYDJP0irv06SSNSqFoGHvtJOif2mS1p//isOQtr
                                        20jSXZLaJD0i6WWxT0u2b5OkT8T4LI9xOypvzJcdb1TMVZukpyTtsirhc6kqlaTPZXPznYyIWvb3
                                        x+OaJOn32TWk+9sx7kmSbpM0OPu8SdJwSbfH/dwvadPKGCdd+ZqkaZJaJb27QgR7w7rbL8ZgYmzn
                                        xvaGrBFgcwdr5cux/3KtKLdKOlnS9p0Zk0xXTokxb6tc1169ZWx78Jxvre6RG8qYrb9j1s3zM76b
                                        5ufiMtqr/huj7pNxPeB+x3Tj/e5cNGztgaAhkn4TAzstAyzbLnwAACAASURBVDTTJH0gQGG/2PeE
                                        AHvKQG+SmZIukPQWSRtVztXcietpiUVzfhyvtQKCXt/TQVAGDA8KEDc5wmHyz9J2Z0nPB+C7Iuah
                                        OScFkg7NgPx1GVDPycwgSVdmYzYpA4zNFWLzrWy+fhlj3rwKD7TBku6Ma35W0r4VMmTxILg39plW
                                        Z58WSWdngPtd2efp9fVMxz5QuZd0nu0lPRHnuDglS/cyAjI8CNq8bO0l8n9co/nJ9OOCyvo7W9Le
                                        HZ2zE+R/XnbMdE3HF/JRwHQZsyKFgBQC0kMJyEHddK/vLtq16opoqbpQBn4se8hPDrAxL7PCni9p
                                        u+wYe8X7v0oKJ+lISUslXZJZtBOI+pWkN0V535VdYwKX20maHsdoq4DvjXoBAcmB5eUxlrfG/00V
                                        4mCSfp4B7S9UyELylPw08wL9KIHSClHZUtLd2bg9kFnQWyrk4P4gB49JemnyPHRyft4RpEnhkeqX
                                        Hbs5/j8l04Nzw4PWlJHYN4d+tMcYDY7P+8dxXi/pyfj+Wfk5svFpkfTrzPtxUG+z0Gdz9+4K2J8b
                                        Y3NRyt3o4LuvkXRNeJw2yEDBRyX9ODxU74scr4bjk43tMElT4zpyL+S/JA3MC0+UJ2sB02XMCgEp
                                        BKQQkB5CQL7ZDff5yZIP2THJyMnGysIuEmB8a8XT0JoBzOEZ2Dlb0m2VY5wlaUaAkw0lvVHSb+O9
                                        JI8HEOrfCARlAPfTlWuYHMD72F5o3T4s7mOypI8kMlAhIGMj1ChZsA+sfG6Shmb7zAtw2ZJ5jNK+
                                        e1dI4IPxXlM21ybpIxmxOz/7vBE4TZ8PDyLYHt9/RYUQmKTDgwC1S3pY0jaxz4DYvkTSQ7HPVEn7
                                        xvf6Z5/fl13/hhWilfTk4NCr1iA8/Xvx2h1T8TrkoYev7Iggxtinsd0s1my9Y90qaXxOXjrQ219X
                                        1mA63lYNdMMKMSlguoxZISCFgBQCso7udWSD3721Kd/vzThjbShTU2eIReV7AyRtIGmcpB0if+ON
                                        EVr1GUmnRZ5BLm2SJkg6vgKabwpwuGOA2bERAvPPDLyMDiA0XNK7JP1F0hJJl67s+sMCfkslBj0p
                                        1Za9kIBsIOmqsGjfFV4KqxOK9YbwIilyNLbLPRfx9/YB6JN36dhsXloyYL5feD+SPCLpvZV8kKGR
                                        v5PG97gs9KkeOUzf/Xw2H2dlxKQls8Y/lVnO31chF2OyUDGFN8cyz8io0KVEhl+Rg+8M5G4Y4zQx
                                        9HT73qIbHaztL1S8IG3x90/T3KxE18YEsUtyTYRV/jJ7//oI17NG8xyffaCSV5I8o8cGINxY0uDV
                                        fXatrySlgOkyZoWAFAJSCEiX3Oubuvj+fhlFlopUFKxfgIqNI5xm3/BofFTSV4Ng/KkOyViZTJa0
                                        Z5wnAcQEkpaG9XligM2jAySdIWl+AOS/VUJCxjWyvmYge99K2EcCYz/pbJ5CDyQhB2dekD9kXog8
                                        nKhZ0qey+75R0ksqnzdJ2j3CpxIJ+XpWXjX3Quwg6eZKGM3fJO0futIkadPwMCg8EW+phH5Z7hmJ
                                        z5dlJGmLLBSsOXTuyYw4fie+l1vnc/JxeeS8JPIyUNIfM907ImtImJOP/gGsU+jVe3s7+Yjt7g2S
                                        0f8RfU4aJqPHuJwc+z8bIW5Dsn3GSrojdOG1HRyrObuWuRVDQO6VuTQeyN+MnLBDg/juEOcanMLm
                                        OkFK1htCUsB0GbNCQAoBKQRkrd9nc+CbrvR8DF6fFal/ALjx8sZirw+A9pnIs5jcyYGcJunRADkp
                                        52NaZZ/2LOdiUAUkDZD02QCS1wVwbQ3y88H0IFetKtaDiupFnVAgC7JUL/l8/94IMuOehsR9JYv2
                                        1+qA+0Qkv5zNw22SXpMdJ+VH7FEhk38L4tZSIXObSDqv4pacF8D/s0FGjg/vlCTNCg/HoDq6d5Sk
                                        Z2K/5yUdmn0+WF4Va2Z2nl9lXo/mCAP7T/b5nZK2ygDvSNWqhs2R9MWK56Mpy4f5ZoxjW5xnUG//
                                        kYjtsEhGT+u0PdbBxPAk/q+qWYPvp+pmb80+65cRwBTa+KVOGAKGhycyX4taBRf3ozE3Xwjv2wGS
                                        dpO0zap6TwoBKQSkjFkhIIWAFALSwX3u3YX39SX14MqrXT2wCRDsk+UAdCQpUXlaEIycZMyrAyDa
                                        s1dbWD2nRujFSUE4Oqqcc6Ok++PvH0taHOBlRBZHfk5unW+wSCwA2D0Z6EnXe5WkjXsrAcms/w9W
                                        SUh8lhLEWwIwfjWbnycC/LdkZMDCe3FVtt+TAV73DU9CXqb3HRE2N0svLm08IbxZ+ftXh7djtKSX
                                        STqzoisT4kdnoKTXVq6jVdJXsuscG56Q6dk+d2S5I01BRC7NrulnlfyW5oz8fj32aY0Qo017s/ej
                                        jp4clXmAEhmTvHJZ/0brJ7aPx76bhh61VBL/Twz9+14jApLpTJOk38V8L6/zjJnWwTNmZfKv8J58
                                        OUK6XievBjesEJACpsuYFQJSCEghIKtonO8q78cH6hn91isFiu1HYkAequPB6OhHvz1IxdwAM8vj
                                        1dbJwW+uTkAWQrSlpIWSFoSF/x8RonNAtu9PkkW2A8CTwPLrJC3KEpgTCPtMbwaZ2RzunCVfT4yw
                                        uB20YsfyBLw/pFoVqHkRurVXApOZ5+EHFQ/WvPBMfSk8ZK+KH/Dx8n4tynRAdfJ+lmUW+JmqVbtq
                                        zeZFQSjuyXSvNXTsyCAUbw9C+mzlHJdmpGFk5J48ll3717OwrpbsXjfOPH1t4QHaqS+Qj4qO7Fjx
                                        NKTxvkvS6Hr3mxkpfh/7v7/O8bfPwu2OSESjEQGJ7TF19CPpzpwsRKsjY0giKRPjudXRs+qQjp4T
                                        BUwXAlLGrBCQIoWAVO7xLV1wLzep0tNufSYfAwJozmsQapV7MRLRSGSjvYP8jvvkvRoejv2vCtB4
                                        UgDJTesBlcwyfWQcf3Hl2M/Kq2UdkeV9dNh/II73/fj+sgoIe3VvB5oVEnJDjNvEmIMfBRHprxUr
                                        ZO0SzD6FSE2KHIlXh7eoOb6zi6QL5VXHqvO9NDwWV0dyeFVv2oI8tHZyYdYjr+m7CyKB/O46n7fF
                                        tW8W+QXfq4RkPS7pw1qx34yF7r8nwtES+bhF0QSor+UOxHxeWoeETI5cIquzHvN+MWltf0DSruE5
                                        /XoWPvewvLmlaeWVsMbHvDywEvLQlpGSORlRba+jj/U8tA/Fe5/u6/kgBUyXMSsEpBCQQkDW2v29
                                        RGu/8tUPJW3Yk+e1u10yGwD7x98j8vEHLF5Jhle+Ox24E5gDLAWa43t3Ak8D04AZwFRgeXzHYp92
                                        ADNrq16QmUneFHAJ8Gpge2BvYCvgDcDR8ULShcCRwFJJZmbKF4iZtQfwPjjeTgBrGHB/vMi/19sk
                                        xqvJzB6QdBhwHHBy3OtLgEOAZ4CrJE2POZkMnA5sBLwy9nsJ8DpgIXARMDH2OwNYDHwQaAUWAEOB
                                        /sD4eFHRHQE5CH0euB1YlOY+kw2BPeJakrTGWkjzNSSbw6QzTfF5O7Aj8EDo2cbx+WzgeuDLZjYh
                                        dAJJm4ReHQ1sHfrVFuNxipk9W9WlviBmtkzSBcBbgbmxBhTz+Gbg3/F/5TksA/4BnAscBfy+zuEf
                                        ic9mAk311nWmqwY8Fnq3ObAZsE3M4aB4RgwCtgD2jHke0cGttcdrUOju6Ez3psR9bgsMMbMFfXFu
                                        ixQpUqTIWiMfw4Efxm/H2pArgW8Ct5lZeyEgNSIwAtgHmBRgLP/8IWAAMCZIxe1BOmYH6ZgVwHJ+
                                        kIUlZrZoZay5QmqoEIbWqLCzRwDKJuArwJFmdpekDwdQvBzYMgDtMknNdUBPusfts3trinvYGPij
                                        mc3tI+CyPcbvuYjDvxL4EHBMRhJen31laYD1tBjS3xvE2JxUAXjzYqsgAwKWxRg3Z2S1PcbYgKeA
                                        vwE3hn49HwCxKsOBscDuwOHArnENbRkByYkHFXLTBOxWIS8G3BWgeRt5Kd1tg8iODX0YF/dxN/Bt
                                        4CozW9QXAWoQ1Hbg3nhrWWwXxFhvBowysxfytZQRhlbg4/H942P/plijfwR+19m1lI3tjHjdk13n
                                        wCBEw0MXx8R2I2BUrOV94jm5NK5hZEY6q0Ql/X9AkOYF5ee1SJEiRYo0+K0cBvwYWBsdyacDnwAu
                                        M7PFveH+u4uAJBCweeX9eQHe/gWcEmRjavzY56C+rQrSsqRUZedoz/eLv7USUrQZsB3wtbi+nXDr
                                        6F3AbbHfX4G/AC1xzLYGxwO3nA+n5tVJoOumjPj0esCZwKKZLQdulXQX8MsAbGfE3A4KUD8gXkma
                                        6+jH7AB4/YDBsU9H5YoTYXgUOB/4TSxArWR8FwLPSboP+B3uhfkCcGCmK7aSc6uyr3AL+/ggV/0D
                                        jA7LrvUvwKXA1Wb2fF/ShQ7W+3PABUH0pgMD47ME7l+oGgiy8VgI/EzS6XXW/qaR/L9DAP2fm9nC
                                        jsYziE1TNl9NwDIzWxK6OgV4IPZrzshwIh2bZs+KXUO32+P/PeO4w3Bvy45BZJ7PzlekSJEiRYqk
                                        36SNge8AH17DQz1Mzag5qzeNQbcQkAwU7Bjbodl2KnCFmd3eADQY0Cwp/xFvDwvrmriXEvDZIcbh
                                        JtxCKuC7krbGLZkDgGfD6t+6EoVqiu8k8LIIt6bej4eJ0ZcASZrXsHgvB+6TlKzVSwO4EaB8eozD
                                        owHM5uJhc+DerbnxvQT6xsbYJ7DYBmwCnJoRm9vxELAHzawtgcxQlUbk839esbC8XynpFuAzwNcr
                                        5OY2PCxsJ9wDNiP7/rg6a2lI9v9c3PJ/N/ApYIKZzcv0mr4ampN5MubEHB2eEfE5eBjmbpJua7QW
                                        Yi31BwZEnszLgFfhoZGb4yFTSf6Me70arq06hoO2LE+jqbI22zMi207Ne3I/8M+4vkGhn/vE+RPZ
                                        TGV5N8NDxQr5KFKkSJEi+e/bK3BD7Z5rcJh/4xE615tZr/S2d3cOyE6xHVQhAU9HQqqReTsyD0Z7
                                        FymBAfviOQcPmtlsST/Awz++ESD622Z2U8rxaASWAgCn+PJ0b3MDqP4Tt/bSRwGJAjAeDvwhyMYY
                                        4HHc8v9nYAKwfE1iEiWdG6DPgKuBD0YYWD9J7R14p1Y4TOWYzWY2T9K3A2Ceh1vqExH6GG4hHxwA
                                        eqMgVuNDj8fFvbZTCwsbG2B5Ph5+tWuA0Tw8qa9Lyom6r2J0sAyg96vnKk5jJOlXwGHZ8yKXCbjX
                                        YgoekrnKaysjgG2deE7U854slnR7g+foVn2ZZBYpUqRIkVXGMC8BjgW+vJqHmI7ni/wbeMTMWsuo
                                        dm7gR0YFGtVpKLdV9kPfHdeSl4u9IaodbZFVbtok+lBsE/+3rKT6VfreAVnlq7z87geq5+1D85oq
                                        Db2n0vfhjEjAftH+WePClkoH8vyVPhsQ+5+U6cwDkjaPY7WsjXvIeka8I6p1pQpZn+ysXsa1Dgtd
                                        emP0jUm6fqGkl3annvcQvdi8QXPQ+ySNqjceWTWsH8W+C6PS2A+jSeg+sUab1uH9NWXNOe/Mqmil
                                        +T61j89vqehUxqyv6XSpgtWDf096axWsqNZ4YPSMWh2ZGI2V9+trPaa60wOyIR5CAx6uMA/PlfgD
                                        Ne9Adyhyc3grhgPfwi3VhodIPS7pGjxs5B5grqSWzrDMAFG74zkMy2ObklLvT7v1tYdChNu8Bo/1
                                        n4R7Bz5sZmdm5KyeV6uzILYNj78/EfcuPAF8BLd8N60NC0DynMS1XhrWiW/gIVUfBc6XNJNaqE7K
                                        74EVq7ctN7OlwHxJk4Hr8FyirwLvAl4q6e1mNqmvV0fK7u054DK8GtZ8aqFKY/Hwx/9SC7Gryi0x
                                        1r/Eq4u11vlRWkG/ulP9Q/cX43kfL6/o9R6SBoQ+9MS1+1o8xG11ZZNuutQxkv5vDY/xZKpMV8as
                                        e8esm3X6DXScu7cy6a7yq5uuhfmZaGaP9aK52XkNx7c7jXavkvRU/F4txEPpl+DFUdrSKwtBbwks
                                        PTh+30biHv6t8ZzgN6/i+acAfwrs8EDM9VKKrJEC7l3xfqTOyF+JSlRdbhnOGpNtExbYZJG9Ovoz
                                        VGV2dEj/baqn3EEH9OboGaJKL4rJkjboixaJ2L4kPFvPx9x+Kd5vWlMLdWYJ/342np9L3da7yMrS
                                        HJ3Rr8z09XPJM9OJ71vWDT55ek6IfhGtks5L+rA+eELiPj9S8Y6lBpYfyh7g9eb9ZamZUlq/mces
                                        aV2PX9Lx6AWTesuk59ujkWTYU+fkX1p/5LAyZutmzLpZp+9aj+bn7b1sbo7tg3MwbS0c46rob5Wa
                                        LW+RN2nu69KdHpBk/cl7ApCYZVfHxmd5GvvgfSeG4HF0+wJfwj0eG+HVefYC9gsGuxfwUhrE7GVe
                                        gH54Qmpi68na+/e45z5FPuKe++Nl37bFk3SvAH4UQL19TazSAUIlaQs8ZlK4Z+rnsUvb2r6vuCeZ
                                        2RJJJ+MerY1w6/3ZZjazI89F9r6A9ix34Ne4xf8o4L3AY5K+3xX30BP1BM/XgFo5XsXaOjTyehrp
                                        yVS8p8x4SSNjHeVlmIncn3WVU9NsZsslPZ3dV/LwbI/3CJlezE9FihQp0ueknoEp5SXOjt+rZ/EI
                                        n5l4sZ0ZsZ0NzDGzhWUYuweMfCyLZ8u7hH80rMb9uvDcubV+ZnQ43zZiyuc0slRKGiTppZJe0cj6
                                        nVlrt4vu7apYe9/fF4FlbA/Mcl2elTQm/3xNjp+N62nZmB6ej3lX3Vsq8Szp99m5D+mo63YnjjdQ
                                        0l9D/1sl7b82xqqH60maw22zNTEvWycX18sDyTxJzZIui333azRW6yoXJPOovqXSNT1Zxl5VnvxF
                                        ihQpUqTIi6VbfrjjhzqFIfXH8z/64R6ICauSF7A6gDIs24PxakwDgXeZ2RN43PYI3CJ9raTfSDpe
                                        0qslDTSzxWY2wczubNRtOZNtWLF7e2qS+HhfAprZeI4APotbeIcDJ5nZtPA0relcJoKzHZ6DITwW
                                        846uvr+49iY83jM1rRPw3tW5ryz3ZQnwedzrsRA4WdKGWcnaPslBYjsXuJYXxwC34RXEVngWpTmI
                                        NXcHnmOxPHRiF0mvjddBkjZNjTHX4X2mppfpGpKnZ3T5iSlSpEiRIkXWHWgdKun0LG4uWUD/LGnH
                                        jKR0FflB0rvjnO+O/zeM6lezJD1TJzZvs5Tk2tG1Zcf/aqUSzrSw+G4Rnzf1kblM5OC4sORPk3RJ
                                        VIBqWRtAMEK7kPSDLKb+4kZVk7pQZ/aT9HCc/35JI7LeEat8zPjuIZkX5IS+RE47uPd+kr5b8Qy2
                                        SnpI0jtjn5YGerZhVNB7eXhD5lbW6eOSPr0uxjHz8Gwh6alKfoskfZgiRYoUKVKkyIuku0DxYFZs
                                        HJakFfeGdClOiO2rgaeASwLsjMBr9f8S2BnvUZJi1b9FNMkzs9aVeD8S6NklO99iPD7wNrwBW34d
                                        vZp4hMX+tcCvqDVu/HJUaVjtvI8s5MbMbJmkA4Hjs3FbTPfnTCyklr/TCozPPCSrJKFDTcA/8KpQ
                                        i/BO3/vGmDb1xQdMzOfyWHtQ8w60441Jx9Uj+GlMzGwm3njwn8Bb8ByLe/F8oIfx/KOfSPrUOiD6
                                        uYfn2ey9VClp5PpSaKBIkSJFihTpiQRkYIB88KZiQ7L3F2WApCtBwnA8jKM1ynkODTDzHzOba2YP
                                        A+cCx5vZ1wPsNq/E+2F4svFAViyxmEDWw4lg9faSqwEIWyS9GQ+dewEPn/mOmT20ukUEUsUoM1OA
                                        9GZJx+PhckOodZZ+A7UE3+4CdQOolVLeDe+GvibnT6GG3wwQ3Qx8R9IOEUbU1AcBa7qf52KbwHla
                                        90NinNvq3HsKTzsNLwZwNXAQcABwYGw/EWv1s8DGaRy7cU001SHH/yMgrFnZ1iJFihQpUqTIajOA
                                        WoOfiZUytTeurWZyHZw7hdN8Ns75mYgj/0z8/6XI+dhV0qbRWGxQZ4BgFoKxiaQJdUIwjsuISm+e
                                        P4s5/EkWRjcvGutYVnLWOng1ZWVpm+o0n9swmhneWSccLunLm1YnEXw17rclznNk5fxHpc/X4Nhp
                                        nHaX9GAc915Ju3RAcnu17sR2twZluH8c+VkvSkSP7QaSpkfo1RYNzvGvSP7eL1/z3XR/Ldk1KAtL
                                        lKT/F7lSRYoUKVKkSJFMuqsMb0rOTtbAVKb23rAidilGiO3f8HKu1Q7F38v+XoAnVb8AzJA0A/eQ
                                        nNOg/GoCTGOpJdNadp/PZe/1Og9I5tXYEXgw7mE6bu09wczOi11bK6Qs3atlXhHVOX5/YG9qzXp2
                                        jY/acQv59bilO3lBPot7X9pXpZHfqnhnAvgK906kBkLLcM/duLi/1SYFYaFvNrN7JH0h9HFX4D9B
                                        WP8LTEthf32oWeEMvDzhuFj7aQy3iPWyqMH3muI5dT8wLXSmLeaofyT33wu8EfekdPsyie3EbK0P
                                        ir83x728faoMd5EiRYoUKdJbCEi99vFzgSe7+sSpQo6ZPRmlTw8JUPAa4LV4DsgwvOfDKDzkZjzw
                                        igChzcA5KyERY4Jkpc+T1fP5RuC7t3CQ2C4K8Cg8rKQN2E1S6kw+Fc+XWGxmi1fE8xoYwHAAsCFe
                                        GWg8tTCajTM9nBN6sSVwAp4r8QAeptOGh9980sxODS+FqJN3EiQivdqzKklGdLBuRFSyeX4/8M44
                                        byoRvWUA4rawsmt1ws6iH02zmf0jyPd38BCvCwJMT5Q0IQjsZOAeM3u2NypQNtazgryOqxglDo71
                                        N6cBGVwe+rcLMNbMns52WSJpbKzpVF1sXcmsOu9tQwnBKlKkSJEiRdYRiq1VoJqWdR+fuDZCWlbh
                                        GqohP6dKerzOfoMkjZW0s6SDJY3r4Jj9YntspbdJku3qnbuXzuGxlSpGuUyMLrTXSPqDpD9JukjS
                                        hZL+KemWqCa1vPK9eZIWxPtXxHh/Pj57bVTWmpKFtrRFv5EP5ToTVZZa4tUvC99Jie0vrc5b6mye
                                        v+KzZkmHSZqa9XVIrykxDvk5WlY35Cc758sk/T3WR3ud8X1Fb9ejmIuzKmFY7fH3HhkBrBJCJJ0d
                                        +18t6c1RoW47SUdlIXt3Shq2ulXK1uC+mirro72yTrYvvwBFihQpUqTIitJdHpCRDd6fmX7Hu/oC
                                        soTR5qjKMxgP5dkGD/lZSi1h/Hnce/HASg6bEl5Tvf+8A/pjdH2Fr24BjmHFvgi3NL8Vt8pvFmM2
                                        CO9q3Rl5MMb1Fbgn4TDcs3IzXjHsWjzZGNxjkutn8mBsAnwfeLmkXwOPAsuTpT3A5wBJG+KhYx8C
                                        9pR0PXB67L+sjtekWdLWwIfx3iPDs/Mm2RT4bhzz15L+AzybwqXq5KZ0pNfmX1GLmT0Y5WiPpxYS
                                        mMJ2bgMe6e16FOtvUvy7mJpXdDG1HkGNDAffA16PeywPiudGP2qexinAR8xs/uoWQ1gLUg0hS4Uo
                                        +lGkSJEiRYoUWScEpGkV3+8KIN0cQLFd0qHAm/BwkFSNKIWI9Jf0QvzfH/i2md3eIOcgAZ16ndRn
                                        0QcqYKVGeWY2W9Ln8HLFG+LhLrcFqN8G+FSMxx9jPI+O8fwtsD1wFPBFPK/jrCAf1wQ5nUstVCVt
                                        lwJLKiDesvE+HjgCz+2ZLunR0Kdt4vp2w/NLEhHYBngbcDneePJBvNRy/yA1e4dO7LAS0rBxvF4Z
                                        uvMfSVcAN5vZgnp6UsmLIW+8GVZyw3MhdgtgrhiTccDRZrZwVXJeerA8VwHn6e8RdcheHj75hKSD
                                        Q8felxH+B0KHzgoSt67IB3iZ4fkZsUp6vGH5mSlSpEiRIkXWDQHZJraDMqDRPwBqd5APi7j7gbg1
                                        9RhqMeNPBuAbhVu4hfcW6B/XeXZ2zaocM3lVNqkDoKYFiO71kpGQRyW9HfhLjNFmwHbAz3DvyFLg
                                        RzHPr8aT+c8A/g94BzAlwPRjcejBHejgGOArMbbtQS6mBeDcAU/cHol7IxpJW5ChNC+jgwgRujcV
                                        zwfKQ7RmA3fj/Tq+m+kswHVxHfvHsXeL19uB+ZL+Cdwq6Ym490X1dCBCrwbilv9t4/sHZevk2SAf
                                        3wzC1lfkhepQxDrbohO69xBwnKRPBMgfDiwKb+WLSN46kEbEp3hAihQpUqRIkXVEQBr9CLd2E/mQ
                                        pN0DDL8cr5jzFbza0Ptiv0EZWN0g/h6QQFMHltUWVgzBSuEl99PLmw82AIL3Rzf5M4D9gI/goU7b
                                        APfFPbcEIBsYc59C8FIyeFsGQC3TBaNmHT+dmvU4jeNzeJPIJtz7sgjv3bIZbhlPx0qW6GY8FO7X
                                        eB+RN8ax2uK7u+LJz7/AQ7PeG8D2GDxU7BPASzIC9As8Mf6HwInZ8CQAvVP23qO4h2QO7slpjnts
                                        jnNsDbyqQlrb8PCicXjjvTPMrLW3ez+y60+J5stW5zkUFbDeA+wVxHSQpKnA1WZ2YeVc3XZ7Gbka
                                        WufzARQpUqRIkSJF1gkBadTBukuTRVPYlaR34Fb7ZcBbzOw6ST8DHpU0JMDl8nhBLfxKZja7E+Rq
                                        TCPQ3peUpUJC3gd8GS9tvEkQr8G4F2lOBszaqFmH2+sA7iW4J2pDYM8gAfBiD9nAIBVbADdRq5z0
                                        tfju+4EbcI/IxsDH8XyVbwAX4p6ENwL/CYKxCDgz5u4U3LvyMtxz0xJgsjp/I+Ie/gF8OkhYCx6O
                                        tWOQiyTj49WR3B5E52VBdKbipVuvBz5hZtP7SOhVknl1wPvGeEW0U+o9D1JYVVS7+lPsW5VjJb0R
                                        D8tbuo7GrFrFK4VgjS0/M0WKFClSpMi6ISCNktC7GiQk4DsJt5gfF7HiLQGa34mX303j0BTAdDRu
                                        VW+WtIeZPdZBfLlVxjFZd6f1RYXJSMjTkk4K0P87vFTua4G/BoDeCi8f2yZpSXx9aIDJREiHB/ge
                                        CByHl96dH/M1mhVzaxJ5+REeGpVAXmtGHBeZ2URJTwPPxHszY17bMxCcepnMCj3oH7qYPHXJGzMY
                                        T3AeFuSjLe5nSOx3Z9z7m4BLg5jchXs2DsA9NrOCnnRJWwAAIABJREFUlC0H/h6ftQcxuhEP5zoT
                                        DwV8Ce75OCHKRvcV8pHCFxdm47vS50NWaawZD508AM+NuSB0hCBsx+I5R0+Y2ffWUThWcwODilGk
                                        SJEiRYoUWScE5D2xzfuBjMCbk+VEYa2D5djeK+kgM1sS4KQ97n0InsOQAEs7tSpMj8X/KwsTGxrH
                                        SAQmyYy+qjQZCZkP/FHSLcC7gR/g/Rp2CZC/p6Rr8TCUEcD7JL0J90zMD8A+EM+zmE3NIp705NfA
                                        Vbh1+XvAPnio1+/j8wVBaBJxaM4qUSXd7p/CmDJSsTRIR79s3pMMwPOBfhD6kTwh84GvSJpCzdMx
                                        IP5eGse+Ak+wfx+eeP+pIBlXxflOwnOKtgrC8QXc47MwyMcfgK+Z2VPrOKG6Kw0C8+s8d5aHUUAv
                                        VjVrj1LY78Ybhb7TzK6pEJUbQic+JelUM1sXuVeLghRtTf3CCUWKFClSpEiRbiYgwxoA924pUxtg
                                        eUkO6iIh/ewAhf3i1Y53vz4PuNDMvpYhoUZgsKnBOLb0ZcXJSIjMbBLwQ0kX43khn6OW2J33UTmq
                                        ohO71zn07/A8iwnAo2bWGvP1fuA3uBX8qQB6y6Pc7qwM4FY7lS+ukFwFIRmQAcVEKJbhFvUz47qH
                                        4Z6KDwZBaAEuBh7PCIiolWDtZ2ZLJS2LY71gZi+EB6gprmUpXnHrVtxLMy6OcRJwTlQbsz5GPtI4
                                        L4yx2yOIiHAv2BxgVAchZ4kIXm5m12R5XakZ5F+ip1CqbDdxHXiP2oJEp/tNxQu2KD8zRYoUKVKk
                                        SM8CyS2ZxbrLwEIGlnNQ9wBuiR6Ch9akniR/kPQW4GRJf4zKTx1Zo1vXV+XJe28EEXkUz6u5BPeC
                                        HIh7ArbG8zuSN8FwD8l9eE+Rp/BwpgeBmWa2KCePfiqbKOkjwE8DaE6O412Ml+KdHwQgeTuSPk0P
                                        HUt61pTpXAqfWxjbYUEQhuIhYKfhCee3AFcGCXkhQO50PPTnDbhlHmAzSZviRQz6AxtJ2jbA6AbA
                                        JXjI2eQgOtviuUk/A26N8C7ra7lDucp08L46QWBSeONhkk4GPg9cEfM9hi7ypHbGwBH3UK8h5Yjy
                                        M1OkSJEiRYr0LAKyIPNIpBCM9q4AYHWOOSuA7IPA/ZKOwCs63YBXyDosPn80gEUjcDO6wfsvrIdE
                                        pMnM2oPMXQdcJ2logO/hAcqTl2J+vGab2bJ6gC6OJX9LTdEP4kjcI/GT0JdxeI7FYrw54aF4vs/g
                                        eG9hhPH8L/8g/k/VsLYEPomX9t0t9tkWr3j1QzNbAlwl6WV4Evup2T1sHISCIBVvw0sOJ7D8nQCm
                                        Q+M6N89u8zI8xOy/ZjY3J3LlsfQiXZgK3AH8X1Szm4on/e+I58x8FK9uN707113e2DS8XvWKbbSV
                                        WSxSpEiRIkV6DgEx4AhJ1wRwWJx1lG6mZvVUF4Gy/gFkUpLwpniJ13eY2Y2SFlMLI2qUfC68AtP8
                                        AJl5GdmF6xuozMikJWJiZguoeQg6AplVQqPqsWMsZ0YFs38FSTycWh7PlCAIzwexGB06Nhn3XgBs
                                        J+mXeCnX4Xhy+OezU03Bk+EvMrNFmXfnIUmP4JWYxuOVr7YPUnFgbPOywlWZFCD64bj2CWY2L9eR
                                        Qj5erE9BPBeEx+PPwNV4Z/jlsYZ3D7IIcK6ZzeuqNZfpqWX6nnKQtqC+B6RIkSJFihQp0oMIiPCY
                                        /jbcGnyXpFvxUJy5OYDoIu/IELyp3TVBPKbh3pAjJW2Mh80ka2oTjS2ZHeWGrK/AUXWAm9WZf1YF
                                        eFdC6R4BviHp97j1+824Z8TwkK90jm9XDrMNXq41l9YgBX/FPRJPVMljFob3XLyuD73cEPfwbBiE
                                        ZhS1qlrgVbhmhX49Z2YLq4C2EI/GgD9ISErgHx4f7Zc9v5pi/s4Dvl4ls2vpOlIIX1vukZO0HV75
                                        7SDc85VCDJvK7BUpUqRIkSLrnoDcj1ug82R0C/DeDBwar9nAE8Ajkv4G3IN7R5Zl1vXkHdEagrfU
                                        hXkgXor1WLxm/y54Z+p2PO6/I5IBpcpNZwmJ1uKxqCTAT4ou5CfjfTzOw70uw4NULsFDsrYPfZuO
                                        e0n+FZ/fC0yuhkLlulX17sR7rUEsOl1yufL9Qjw6R2QVc3oLni80K9btg3g1sd3M7OEghGucwF/x
                                        dFh4ZtslWeT4HAgciXvZtu/geTCf9ThHrEiRIkWKFFnXBOSmAPapdv9GQUaSpbAtQMYGeLLynrg1
                                        exFwOXCfpNuB26L0aw4WWvAwrVWNtU4hVFPwCljfAW4GfonnA/wbuCk1M1wJkSmyjsBp5kVYACyQ
                                        9FjM7Qy84tKRQT62xKtbpdyNN5jZ/fXAZ0fEoIF3JweeqnjvmvL3C+lYrbleTq30cj15WNLhwDuA
                                        I1jNZPQGng6LMsCvA16D5/mMyr6Wng159bXpoX87hnGjSJEiRYoUKbIOCMgjeD+EV2fvTcE9EKlc
                                        5TAyz0bIYLyHyHtwi/VTkh7GqwndE++1pfwAav08OgP0lsfxr8FDcpYBF+QhMhWA0UhKuEXPISKG
                                        V6VK/Vx+bGYPxeebEc0E8UpaD1YIBKtDECpW+nqft5dZWntSCYsbGPP9BWDf2OWwVTlWTh6z4gSE
                                        p+M18ezZjVoOERWC04x7OsCLHizDCw6kJpqLyqwVKVKkSJEi64CAmNkvJP0F9yyMx0Oc3ljZbVIQ
                                        khHUQrVSk7h2PDxqLN6M7kN4R+S/AQ9Iuhnvur2sE6AjEYbHgE2iytGv4rPhksbHNYzAE9MfMLO7
                                        O7CMzylq1DOIiKSRwDEBCp8Ers6s2vsH6d0EuCxLai8eiZ5POlqIvi/AzAjDPAgvFnBgBv5/XyUp
                                        HRCP5tRjxt9Sc5RM3jeO+TbcI5uTjhQymp4h0/FQv60zIwp4dbMb8DLTE8sMFilSpEiRIuuAgARA
                                        TLHy10v6cwDBPfHGcnvh4QpJVuYdsSAIR2f7PyPpJuAiPPRmTp1wmbwR4XJg3+hZMQ4YiXtEhsc2
                                        yXeAu3lxr4L09zTqN1os0n0ANQHOHag1fpuA53W0SxqEdycfGKDwsTJq62aqaOxRtA7mdSTeL2Uj
                                        PLSpJeYavKrY33Hv5YOrQFbbIrl9XBhDDsXLL29dIR1JmojKdtT3dFyAe2bvpFJsoEiRIkWKFCmy
                                        jghIpbfDbDzh/GFJf4gf8u3xngrvpFblJklH3pHUC2IcsDPwMeD7wKmSllerGEkagpddPSqOeQie
                                        KDorwM1E3KsxNa7xrxXCsbIx7B/bjYp6dbvsgVuoJwE3mdnSeP8VeEWzHfEyrtPLUK0T6RdreH7l
                                        /VTJig7ISXsYLfKciiXAucBPOpMDloVcbRqE47V49aqB2W4pH60zno4z8Py2e4GJuQe2VDgrUqRI
                                        kSJFephEYmc9i2eTpA0l7Szpg5IulDRNK8rkeG9e9l67pFZJs+PvUyNsYwUwIOlASU9IelzST2Lf
                                        10vaOs7bbxUJFZLGSlpWuT5Jem+Z6W4jtkgaIOm0GPsHomFd2uebMS9t0ciQrijXWqThHDXFdtuY
                                        n0dj2xrb62LtNzf4frOkzSXtIumVkg6QdEm25u6J58WQjuY1PRMknVh5prRlL8WzZV48ZyZX9v2T
                                        pPfEvQzp7LOtSJEiRYoUKVKTddIHpFGfiAiPmhmvByT9Ca9eNB6vonUsK4ZI/O+Q1CyWKRk9P3aT
                                        pB/gvQQexBNVvxf73mVms6L3x/aSNge2wvNNxuOhXB/Lw7cqMh/vlv4yVgzZGF7Uq1tlFLVO5oOA
                                        CTH3/XHP2Djcyj6hDNU6k0YFGwaEd7KlwfOiDe80Pzl7+3pJRwBfjHn/HfBaMzuygxyQRAx2CF1o
                                        Awawck/Hz/EKecnTsbxKgNP5isejSJEiRYoU6aEEpAEhqZZVVfzQPwE8IelK4KwgJPvgoROvon7+
                                        RTWcI+UH3IInr/4wtnPxUrvCwzJG8OJY9KckDQfmNwA2wpNjk6QQrHElybl71CfmYBRetWgK8Ayw
                                        JGL9N8BDf8ArEj1bhqzbRRlJzJ87FqD/usp+Lz6Ae1HytdluZudLugo4Dvgq3gyyw+uI4wyr8+yb
                                        j+dzpJyO84GL8Wp7U81sUR2jSSEcRYoUKVKkSG8lIHXISPWH3qJizfR43SHpzACc/wrwkBORITmY
                                        CevqUfHvl4BP4j0DTgti8hye+zEfT4p/EresTo3Xwg6AxlI852D3OGdKnN+KFyeuF+k6GZGN9Z3U
                                        utePxr1T4MnDMwtwXGcyuMH7szvxXGivwyaazWwG8L0gIps3mtswBrRGmOWAOqcYBvwWL8t9LzCp
                                        4uloIivvXfSnSJEiRYoU6UMEpAEhWcE7Eu8vjvK7ZOQjbQ/AQ7LawgpuZjZD0gjgXUE8rsI9FxcA
                                        n6ZW2eYivLfAXsDn0vfrXVe8344nsFMhG+Px5NbSB6BrJY35yNj2Z8XO5Jvhlvd2vKnl8jJk68yo
                                        MDqboyTL8AIBUKcS1kqO25YZKO4M4rkyGQiMyc43BQ/P+znwlTqNTq0RASpSpEiRIkWK9FEC0gDI
                                        UAfwUwGdrRWy0IR7OPYMYrJU0kxgkJk9nwGOC/EqXB8CXibpg2Y2vUE4VYodf6bO9WwSwHdRCcXq
                                        Fp0YmI1/3ptlGF4taRDwFKvZJbvIWpGNKgQkEY7ZHa3nrJdLMkZUPRFpfXdEFJI3ckhGhHJ51Mzm
                                        Rx5KW/F0FClSpEiRIl0nvb2LdxtwWfydWy6fJcIxcgtmvBZl5OQ54BWSNpG0n6QTgO8Cd+Hled8I
                                        3BBdtPMmhv8bv0iQnVkBvPNxq+qGRcW6TcbGdhArhr7l1vbniyV7ncrW2RzlMrMjAhLrttXM2uJv
                                        RdWslqiQlcKjOprbRHZGZkSoKdOP6fGsaCuko0iRIkWKFOlaaenl198OPF/n/aW4pbMj4tWGV8Q6
                                        FM/zSDIX+JWZ3RRVdj4PtAboqR4nvfF0bPvFe3ODiIzDG9+VXJDuk8W4x0NR1nUDPLG4tczBupPI
                                        vdijDikYR4O+LMlzKOnQmMdHY99pESq1OmRyFF6hrqoLsxuFWxYpUqRIkSJFCgHJpRUPq0nAc1hG
                                        TFJOQDMvroqVgMt98dl9wA14IvrVZvZogJ8/SbrCzOZC3XCMdJxn8CaGowPYpIZkm1SISpEuxLix
                                        XQbMKGCyxxCPvJv5xtlH84II3EjjECwL0v89ap3PZwCTJc0GHgkjwtPA43jxiPaVlODdKJ57rbFN
                                        3pjZZbZWaV5TVbJU9jwvgZ62LbhRph/uaapu++Ohk/3xwgADs9fgeA2J53r1uwOy19DQr+Uxjwvj
                                        92Bh6MtcvLzyAjw8cy7upZ4f781LfxcPae98xmQ62FTRyeZM16p6U9W3QaFvQ0PnRlT0c0DsM4ha
                                        U+TpoU/z8FzQabhHd05sZ4ROzgFm5YUtihQpBKQXSyShTs+AZwIxLdSP866C1adi3++a2d+zB1pz
                                        SnA1s7kd5HCk9yYHeakm2W4pqV956HSLpPC4EcCmAZDa4sdhOm75LoRk3clovBM98cM9L/6+C/dY
                                        1SMu7ZKGBSiYFUR/c7ziHHgp7SSTgAPMbHKDnj2JkG5c59rmh570daDWL8apr0o/Glda64wsj8Im
                                        idQ+F8+OF4CZhZx0SscOAM5bj255s3h1Vr/+Ddwf2OMpYLKZzVsP9GI48FBZIb1OfmdmXy0EpD5A
                                        EbUKOjkBGQhskXhKHeKSfkgewvuJ3J1ZURR5HWQVtBrFpqcwn/nUql0pQDDA3rhl7oWSiN7lkvII
                                        Ftemx9olLQndEC/2hBXpBjtBjH0C/tPjb2X/q4PvbYp7Em8Ajgjy8o947wy8L9B74znQUTK7Yr1u
                                        WXkuJK/p7LSmy5T1OHk4ntUz4lm7FPd2pGaSwr3Rwi3eLdS8L8mSPSp0ac+VEJj941WV5yX9M8jJ
                                        U0FQphd96TMyD4+EeIqax2xxvJqoeUyGA9vgVTJHrQZBflO8cixzXTzf7saLYSws01FkfZDe7AFJ
                                        AGVG/J/AZTuwPbC3pF92eACzxXgfkSRt9UjGSi/Ege5twIEZsJkCvD4eWC9Q8kC6mojOrzzokyyN
                                        bRMwfGVEsFHYVgEaaywvie2CICDJCLActww2J+JfIQhbxXw+EdXoFsaaegr4MvBS4DA8F2xhSkiv
                                        P7WyzDCRy62sH+Wy24ET18Jxvkit6ENXy05r00IcBqMUYjMq7mMc7p17K409KGOBoyvvPSDpH8AD
                                        uAd8anlOMAX47BoeYyvgE910vScDfwYWr8rcxbNkBO792DpI62GreQ0Hxot4Fv4O+A9wV7UseC+W
                                        ZWvp2fPTbiSkX+vmMWqmFuo3OAwmO1Lz+BcC0kMtF8SEpcTUEUEmhgILGoHOeIj8r1/I6v6mxfbh
                                        +Nvixy15ZsbFj1MBsGtINFZCRBfH38uoVTkCLzCQYoG3oVaAID+uERbyTpCT/+1bZqUTVgIn583U
                                        whT6x3wNjzXzbJCQlooBIM330Ng//RBvFwTmjvBobBdzOin+b6kX8pjmS9L47PjJG/Nf1gPvWBC8
                                        i9bCWjyyGwnIwi4Yg7nxmoKHw6T7+nLc11bAywNQdhRes3O8ktwh6WLgniDMi9fD9f4E8MQa6teu
                                        3UhA5kdlzFW9T+F5HXNw79xlkn6Ae9g+UdGLVZF+wLHxWiTpZ3hz1Md7cwigmS1ZS8+e7iIgc8zs
                                        op4wdhE6Ozqw5LZ4A+639IXnRW8uw5sA4HzgsZicXNqBAR0BxQCcrWsJTN6BW3ctA1rgDQmLBX0V
                                        iEZ61Zmreq/0UJ6TWVq2zPRjZvaD+Cqgf6WhpbLSrv0lDZM0IkozbyZpI0nDJfXP961eb5m5Dknj
                                        cGCXbF3MD0L4RAA1rYSgG3CwpP8DPhnfHShpDHBwfPehynOh3vUMxr2jZGQVPHm9hOcVsrzMzJ4x
                                        sxvM7LR4XhyAV0K8rxOH2BMv434FcK+kL0jaU9KgMrrrhf7MMLN/Au8AjqFmhFxdGQx8CbgaOEPS
                                        y8OYU2T90qvlZvacmd1hZn8ys4/hFSWPBC7pzffWFzwgs4HbA1gsxuM0oeZin0H9SlhrmwilSljD
                                        WDEP5GBJZ1XCS/o06FyZF6FOhaq8V4vqgNh+eC7N4Bjf9iDPS4L0TQ9Q24R7P17Fik3uUn7IrsAo
                                        M3s2jjsMt3a+BLd0boJbxAfgFqyRuPfqabxPxOQguxOIniKZZT3lDxWiueK8Ci+h+x5qHofktVyC
                                        W6HhxeGPiVjegyegvyyAXZI3AFfhXi2L/fLv1dPJTfFQq5EZWQV4rsxbkTo//K2x/idK+nMYk94K
                                        fLyT4PHj8Zol6bd4nP9D68tvwXqsN0uAqyTdi4ejHbEWDvvmeF0p6dd4eFZ5Zq2/OvYCcC1wraTT
                                        Qjc+VwhI901AWnwLWbGPRwKouwSofKybrmMpcH2A2XZqya1vD2A7ZX1IRF/Z/TXoMJ1AfDNuLR+K
                                        N3HcKYjAvjGXG2XjmmQS3h/iaTysYkQQiCGSUnGAtuw8r5b0FJ4IeDD1k1KXxXcszjug8vkU4BJJ
                                        V+Hx389Xwy064RVZH0K50r2lMJaU/zEke/7MqZe3EaFbhnsnjsDzPcbFWv8VHrudvCo/NbO7U+Ws
                                        DojQNtRChywzSkxPJLJUOirS4LnVhocMPizpHDwE4qusmG/WSEYBX4jXHZLOBv5rZqX0c9/WmemS
                                        TsY9IZ9aS4d9Y7zOkXSGmT1fRnq917OJwOmS/g4cBRxXCEh3oBsHDK2SnsmAo+HhONsD4wLUqouv
                                        I8WvPxhvteNel2Tx3S5Aa59ORJe0QYDLJdRK4OYAsH8QhNYgGUPj/9QjYtMgHfUsRvNxq2I1vn80
                                        tQ7bSQbiDSbPN7Plku4A3hXX8YeYmyTTgFTdJvUImJrNkwFj4hrH4oUF9gdOiBfAKZJuDYAyycyW
                                        doJY9HnrVTYGKe9iaDamU4CbzGxxB6WqE6G4UtI1QWSmmdmSqEj0etzDde1KLqUp1mTKF1GQoeQJ
                                        mVV+xoqsCrAEzpZ0OZ4n8vlV+Pqe8Vou6XTgUjObVEa1z+rKsrBQGx4+urbkaOAwSV8ALitetSJm
                                        Nhn4djyXvsvq5yEVAtJZzBvbRED6Z4ADak3HlnUH2JJ0dwDkfhnI2RjYSdL1fZR0pJCq0cBpuLdi
                                        QZCMmXWIwZggKGOp35OBIAB3xljeiyeKPhPHSwmDbTHOm+KW8f3wMJ3xQT5/B7xG0s/x0LxpcW7w
                                        mNon8aS424PcGF6MoL2epyqs9E3AT/Ack0PinFsDJ2W7XhuVce6m1qRqedyz8CZWTQHG2/s6+Ahy
                                        /vr4d1BGQKCWANwobKo9ElKPibldBswLMnKRmf25AeF50fKM7W6Z7hD6d2tGlEtIQ5FVJSI/l3Ql
                                        8GlWLTG0Hx6e89nwqJxvZhPKqPZJPWmT9Iv4XTp4LR56MPBz4OWSfrw+9BMp0il9u0fS4cBH6b5i
                                        DuslAUkysQJwUpjOjsDybghzSYDmETwZdrcAVcni+3JgmJnN62thWEE+BuLegPcHmN+6E19tj3F7
                                        ilpH62m4u3oSnqDcmeZfL+AJov+QNCCA6puADwdwfQ8eQtU/jvlz4K9EDkcH99QcBEGS+gdpWG5m
                                        S/GwvlOizPMOwD54U7zXx/agyiH/i4eJCffwDCbChySNSzkpfTQcawzeayety1QpLnUyfxEBSaFQ
                                        kvYH/o7nkOTybuAzkk4ys8s6Cp2KMK7WIEKjM0KyOK7nfqKAQYmpLrKaz8DHJH0Sr1Z02moc4mjg
                                        aEkXAOeY2cNlVPucjiyW9K21TECSHIUbOU8q3rQioW/zJJ2CG1p/UghIF4Hf+PP5CvFIFs9D8MSc
                                        2Z3t/1CtcBTHSvH6KwOsM/BchN0yQjQ9HhDfxZNv+0wYVjamh+E1sycA3woyMQj3cgyI+20K0Dkj
                                        yMAcPPQlNQpMzR9bOzjf4ACRy2Nc8yTwVE75Lkn34KFW38GTRpcCv43/p1fnMea5P95cKs3jw3il
                                        paGR8LWCnsR+SyP34D7gbDyhfQ88QXpk7LMb3pByz0yXlsQY7RTA4/t9zYWekYLxsS5TOOJ8PM/n
                                        X9QJfco8H6OAs4J8/A2v9tEa4/lWvP/HHyUdEHPQiITkx9syez95RZ8xs4WlUWiRNfwtWg78NZ4F
                                        p+EFL1ZVDgcOl/SbICJTysj2KR2ZHKWev9cFh98T+Lukw83skTLaReL38C+SngP+VAhI18mCAJzJ
                                        Ap+IyHO42/M2Kv0fGpGZjHQ0BRjuLChRAJ2rgLfF+VI/kI0DiD3R18iHpAMDKD6Bd6a+cE0SebOO
                                        9INxz9FeeO3rbwTA/zIevnAn8LVwNc7Fu2P/7/tm9qSkbwCvjUOfZmbPS+oXZGUM8D7cW3JuAOJv
                                        BHF4CPgIXlnimLCePxig4P4Ix2pPPS6CPLQFAZsAnB9kaUyQsEHUEp5b8MIJe8S9fAuv7nR3HwPB
                                        6T52ydZo3oDw+QpRISN2rUHitol5fXe2z/mSfoInoh+Ke96OAazB+CXCuEnoEaFfKVzzmWy/QkCK
                                        rOmP/uOSPhBr+/DVPMxxwHGSvomHGpZk9b4jl+Ahu6O64NijgAsKCSlSeSbdFDjpgp52bU19ZIyX
                                        AzfG33k890DcUpoDkUbAd4CkIVmvh9boC/ESSW+S9A1Jj0l6dwJODQDX1bilP50vNcU7MMBWrwc5
                                        GfkYH+B9Jp7I/csAgk3Za7ikLaKfRnpvtKRNJW0uaXD00thL0vHA1+M0XwW+j1f82BO3Xk/AXYpT
                                        45zNeM31HwbJPCHAfirzO5Ca12FICscBXg3cArwz9h+Cez0+jXd5/jfupZgOTA7wuhuwg6RDcYv8
                                        qZJ2ifjerSSNlzQixqfFzBaZ2ZNmdouZXRu9BW6Iv28D/h9wcwDzj0sakhGovqIfI4JoQS0ccTje
                                        M+fxKFfZ1IAw7BRr6vzQqYGhO/2j8ss3Yi7HSxrUgQcpHW+7uIbWeC+Faz5aWb9FiqzpD/7seH79
                                        cg0P9XXgckmvqfN7U6R36sY84NQuPEUiIePLaBfJ9O6/uIG+R0mv94BkYOfpeCtPUt4eOEjSH1b2
                                        feAXwFJJXwuwuT/eT+Ll1Hp6QK2RWXWCE4CZhOcI7M2K5Xg/Gw+e53qzpTsb71HAt4EtgMviBzeV
                                        2G1PlY0kHYs385oWBGE5noOR5uliM/tNxMfujieFjwb+GON4j5ndnV3CJyrX83ncWv4ePOTud0R5
                                        W0nDM3CprP/InbHfDWZ2VQb8HzSzvDPyjWZ2Q/z9Ujy87g0xr5sDW0qagId2jQYGSLrYzH4mKeWF
                                        tOLeuWnUrOxN8f73cQ/BkcAlZnZJH2lqmO5zM+ADeMWrcXgI4vAgkfevBPinSmWbBMmzeM/Cg7U0
                                        vrsMz/FoNG7pu9WKIGldPlkaSRbpgh/8pRGDvZBVq5JVlS3iWXiupF+Y2bQyur1ersZDsruShPxC
                                        0nvNbEYZ7iLxTPqPpM92MQFevwgItdCq1O16cGwXBnFoAkaa2cwOQjQUwPgEPCxnZAaOnorjXAkc
                                        i3s3qBdmFFaqNuDyjIA04Zb0Qbg1+B99gOwNwj0F78Y9CSfGeFvWvyGB/ecDfD+dHequmKdW4KnY
                                        772412FJzNE04P7wlOwbuvpIjP/uuNdiFjDRzH4l6UxgqJnNz6yFG2bz2F5bhzYP+GpY1PcIUrkz
                                        MFTSWXi41ReBUZKeAO6I3JIhwKUxh8qA8WV4MvquGbE6GA8fa4rrTt9pD1DcgifPXxB6daqkW81s
                                        Wm8PxcrWxk54SGSSIUFClgURb67juUjfvTnW5ueC5F2Zl+qVdBgeivdQEN2WevlDWWjlPtnzAmqh
                                        msPM7IXU0b7kgRRZi+ugVdKvQu9PWMPDHQUcIukzwLVFT3u1XkyVdAUe/ttV8lLg65GYvrSMepGQ
                                        v+LRJJ/sCRfTawlIAgsBAofjYTVQ81Ykq+ZwPPY8hey01iEgaWI+FgDyYjyk53bcevv/cI/I0pUk
                                        rKa+JP8JMJ0a2C2La3iVpKsa9DzoTXI47tHSJcwmAAAgAElEQVR5APiymU3KwWSQlLYA++fjYTS5
                                        fLaa9C9pSYzxHpK2A04PEvKzIG4bAR83s99HV+IN8VCeFkmPAuea2c1ZDg/Z2I+mVqggeTuODNKz
                                        AR7idWsQxWGhJ2OCVBwHXCjpY2G12hV4HO89cUEQqYti3nO9+CFuvWwHptQhrAl4/zx+iPbCE9J/
                                        TJ2ytL1wffYPgjqsYiyYgXu9lgUJq/44t0nqB1yHh/X9XxD6SyXdFgRmH7xXTFumW+0dEOaReEU8
                                        KroxHU9k/6yZ3ZyMCKUZYZG1TEJOw63S713Dw43CQ15/LOk3EcJYpHfKZV1MQMBz5B4Cfl2Gu0g8
                                        j9rDKLJPYI5CQFaXfEQoxh54h9l3smIC+nDcq3EAXqKuUY31BBgnBEk5z8y+WDnfiXhVpA9GAmw9
                                        IgO1cI+H8BCTvQIkjYhrewOeqD25twGdStL5bwJIngnckMhHVj51B+CDQHOExi2IMbvFzB6RdALe
                                        L2RYeDd2C0JxYpC2zXCP0wMBQi/GvQVPxPgeEiz+FcBr8H4ce0v6uJndmHmi8g7oSzIAqtCP7QPA
                                        fhIPC1qWJXx+KvRrY9xz0SppCh6W9wZgmaS/4GFUR0lahCeSfyfA7F641+sZYKsgZE8m8hlj2WRm
                                        s4J0/AQP5boy6nj3Smt8dt0vCQICK1anW4SHwOUkrPqQXI43ant/6NrbYs4PyXZbAnzCzG7pqAJW
                                        zPXueAhYe0ZA0jXtA/xX0tHAX0pFrCJd8KO/VNL3cKv07mvhkJ8Ddpb0NTN7roxwr5SHuuk8X5F0
                                        k5k9WIa8SDyPFkj6El42vBCQVQU3Ad42wcOlfhwfpzKfSeYFAByOW6L7U6chYRYyNC1A7gGStsST
                                        XEfjITdn4THn22Z5BPUmNpGi2bj3ZK8M7EwKsrQDntis3jbukQfxW9ybcHGyrGRhNKnj9EvjPluC
                                        GG4dBO4H4a0YiyeIL8JDk/rhYU+nx9g8TK3E7tl1LumBeF0e17cXHu5zV3yewOiWQf5SZS2y454e
                                        rxw0I2lvvGLZBngVtf9Gn44RZnaKpFNxb0wiXVcFwRqLh1pYWPZTTssLeKJzO14B5beZt0ix76V4
                                        Mv1b8P4Wx0Xd+N4MhPcK0j2XWv7HsLD8Pdeg2WPSsyPCGPBvM3uXpD3xHis7h948AvwzyKZ1QOTT
                                        Wn0cuBAvF530I1WpS9d4TpDYn5rZo1W9KFJkDX/050T41HVr6ZAHA7tJ+pCZPVBGuNfJs9Ry4rpa
                                        vijpqI5K3BdZ755Hj0n6Ah6pUQjIKhCPQbhX42u49XJKgMxEPkTNwj0JT/j6Jx13Q28OC/c1eGL1
                                        HdSqV70+wOEGeJhOuqZGVtd0nefiYT7J0pqOd5ika3vLwyADhRsH2dsGuB6v0FItU5w8QP/CY/jb
                                        gvglYjItCN8PYv+lqdoY0GJmV0h6NW7h21FSqoh1XYyf8A7jR8UDfB9gspndHoSvKmNi/B+rN/+S
                                        xuBelEMlXR5E4Gi83G+65uExl3dKWhw68Hcz+6eknYDrzezyuO/BZrYwjv22IEDbBQHuBzyTyGs2
                                        rqniWiIsR+DN9/7W2x5q2T0NxRPwh+EN/xLofzbmIhGAtjrfHYMn3QI8Juk8PNTtB3X6t3ToRUzG
                                        AjObIunIIK2fwUNZ2jISMiyeIx8F3hf7/iPCxAoJKbK2fvSfCG/6T9fSIccCl0g6wsxuLSPcq3Rh
                                        maS/B0boatkfeCW1SqFFihA44114CHohIB2Bmvh7pwCIn42PU3WdJMmikEDwHwMsriysIoGYK3HL
                                        dTtuLX0G+HNYm64GLk7VnarXlj1Y0rHuwS2vuwdwTtbWDwXrfKw3gJuM9H0Kt9A/ARwfoUMrlBXO
                                        /l6cAc98LkdJGhk5I6OBT0jaHg/XOVPSjdQqQ92Ee6Dux/NzRsa8zsK9Cq+PcZwTzb9+HQAzl5R8
                                        91wGdk0ScbzfBIl5PsDxZXi+z3g8qT7lIjThlax2jx/9zSVtjntQWiUtB04xs+slvRL3vN1vZvfh
                                        XrUV9JmsgWIQsiYzmxCJ9Cfi/U1u64Ud0lPI09ZBEvPqVyPxvJmbg3C11FvrMU/fiXW+fRgEvg3c
                                        Ft6mP6dwgs6EMGYkZCnwXUk3x/H2o1acoCmuMxWL+BvwbUm/NbPJjdZ6kSKrIZfGs+vNa+l4/fBm
                                        Y8ekin5Feo081I3nOlbSf0t+W5Hst3GxpO/i0SyFgNQjHgEgNsBDeX6bEY8RGflIQGJ4AL5LY9+p
                                        QHuDajuNSMMcPA7/z3EdPwqGeKKZzY33huHlQR9rcO3NcT3n4mFX6fipR8mrcUtwbyF/R+B5Ng/i
                                        JSUnZPkeyXK9UdyTxf0uBg7Ecysm4L00BgXx2jsI2dtxj8rzrGiFnhJAdHF4ik6qc2034h2Hj8Xz
                                        Ms5JeRXZbsn7NCCf69hnUVgA7gDOymKp7wHuiTkeAPQzs2XANwM0W1Rd2gb38rwR93SMjXn/UpCU
                                        3SUtwxNPr8TL/jbHeTeTdIaZ/S3pSlzTWXiew2uA94fu9aYHWtLz1wXZTs3+BgcJmY17gZqrHsAs
                                        tLEVOAXPldohyP9r8KpyewOfjDC+U83sz53JpcqO3YR7794ShoYj45nRFnOzcfZ8ORl4s6RPAzfl
                                        ul5+uoqswRpZLun0tUhAkpwl6ZNm9vcyyr1GurPT/UFh0JlQhr1IJnfjebBHFALyYuLREuDj8wH0
                                        5gewzb0erXEfzbiV+mw8bv9/VXY6Ih/ZeROgvhB4e5CeeWb2i2yfPQM0vxHYVdLWZvZMA0+IJP0b
                                        j2XfMED5iADF745+ETN7KqjJiMXrcK/Ac0Hqroyx/l/eR4DogXhORmv83Q9PFG4OQjgKT1yfYWZz
                                        cM/F4cCsjNhtFiBwX7wK2YOSTsbDpBZQ82oNAYaY2ZmSzg4y+GxGMPrF9aXKR48GyE+61Y57R86N
                                        824j6STgv3HeE/EO6oYn0v8fbjE/Oq5pCnCFmZ0ciaDKxu1neFL9v/FeIc+Gfs4FNsWb4c2Pe4Ba
                                        yF5T7HMqnoT/XeCq3pKQXgnV+wa10CZCB+bh1cKWVL0fGYnYHM8J6h/EdQ5eBjtVv9ox9GOvICdQ
                                        C5VbGfATUf444vFPxD0y34tjpQR1i+fLlDAe/AcvSHCumc0rJKTIWiAhD0v6LfDhtXzo0yUtNrN/
                                        lVHuFfJ8N59vn0JAitTBqb8tBIQXhVttg5dATU2cUpJ5AjXt2T1cg4fp/CEy/JviWK2ren48Ufj4
                                        ADu3SdoFLwX6DmpJ5cvwEKGhWdnXPBSpLUD5YwFy3kWtKeGkIDA749bYngwmdwjQPxO4Am/W2AS0
                                        ZSFEqdrUZLzpXDrGIDNLYVifrhx/CzynZiM8/+LfATivDQIzE28A+VG87O2+Mf9TgmCcCHwpQnLO
                                        Bq5rYAlPeR9PkuUcZGTzlbh35ZUBODeNqkoz8LyNacBdse9ucU3bBxm6JUICj4xeIQ8Cz5rZNZKu
                                        peY5Sff8Cdzanrwvi/JrTlXEAoC/LXT9U5I+1ssS0vcNPU/rVbE+7os1Aw2qXwVxe1n8vVXo1KFB
                                        YGaFzvSLz/9QeQ509oHbmq3ZS/CKXN+PMR/GiiFZKUH9Z8ArJX3LzB6pPquKFFkNOacLCAh4kYv3
                                        mtlNZYh7vMzp5vO9T9LvSxhWkcpv4hOSfk6lyfN6Q0AqXo8RwFuB8+LjeknmbXHtkwJEnIN3sdbK
                                        wq06wQZvxKsw/Qi32OelP/+Dx8tdm3fMpn5FKwVwPRMvR5rGeqMANu+NmMwe1ROkTqfzZjxM6aQ0
                                        9lkJ2fZIGt8+iEMTbr2+w8zuDqIwBrdsDwqieCbwJ2DbmNP5wKjwJvwL95pMAe6M83w6jr0BsDCr
                                        anRVkLgfAz8ys7MyQJ88Cqmbdv8GtzsM90o8AVyUCKGZ/R74fR3AcGvc60jcI/QO3FPysdjn+qjg
                                        tDfwMUnTAog/Afw/M5shaViQ5EaV1Noi9GqfIHR/oYc3r8x0Zkis3VzmxnhdAyxpQBTT+vk38BU8
                                        /Gk2nmNzIe5ReynuSdwSmG5mE1dSAavDdY57Q5ojQf2YWNsnB/FsDd0ZlhkNDgcOl/QW4F952eny
                                        E1ZkNXRwchSe+FoXHP5Pkg4xs3vKSPdomd/N53spHh48tQx9kYpcuF4SkAy8tOC5Fp8OwF4v3CpZ
                                        J1uCCJyDh6kskdQcFYXaVucaYtuM96/Yglr4zr14IvqVwMOp+VNY8d+KlwOdVAUj2d834InUO2eg
                                        dz7u3fk5HtLTY6yp2VychOfd3BVzsoDodB67ptCXd8e8JZD/LLChpHsCRG8dwHEI8ESExt2E5088
                                        FeP7ZHz3xP/P3nmH2VVVbfy3ZiYJKZNAICFAgBgIhC5VLAgqSkcUpAmiggiKiAWBTxApgoBKb0qR
                                        oiAISJGO9F7EBEILgZDKpDGZ9Mzc9f2x1ubsObl3MiFz752Z7PU895mZO/ees88++5zzvmutd60i
                                        qWwT/Ne43v3Nqnqnb39bPz9+Wizy5WA4rIW83iBEHR5U1TeAJk8Li9dDTUwkRWSOE7EXo8/d4Oti
                                        oI+j4MB5ECakX4AJ5j8L/FlVvwHcoKoNWHTlaVX9P+8TELrI12GRs+v8hvAHVX2pi3RI3wQrshCL
                                        zwdgqXmPho7lRFGL6PpfC0t5utyv7bOwyMOBwE9F5IFi943lXOsh6rTY0/lewCoUfSl3vxnuRHKR
                                        H8uvVPUqEZmVIiHJlsPuLBMBAbhRVXcTkQ/SNHdaErpAVT9wvFEpWzcRkGRF1uJ4Vb0U+PEKRUAc
                                        fAzDenqc6W+P84d+SLeajeXO12CeygeAaxyU1SxP1CMMw3+einlBZ2Ae+7NE5Dcx6FHVrzkwP8jH
                                        9wdV/VUJYlOLaQ0u91cQuwYx+n4uqO0UJXkjAfd3gBOdIJwoIu8UmePw+x0OpoPNwCodqaqe7QB0
                                        JjDeCSUickIRAFrrf9eRpUuFvHyNCE8L1nF+Plah6tHcWpLonAZgOJksFSjWa9REVY56YNGdvEdb
                                        fGyBlIRxLBaRmX5sOKEK270KSxFaC4v+zHByMc/Xrvr6GkHWqyKeV8EqdO1BJkj/Uye+eYVj2Nff
                                        CmRUnWxPxZpItiq961brTRoPxqKO07AI2dVYROTnwDN+czzHt1XXUZHDcL5dGzLKIxwn+Y14FZYU
                                        qI/zcW6lqieLyLsdRYiSrXAP/QbvSnx0GTbfH+u7dKQ7T5J1TnutwgRkbeDZNO3Jitg/VigC4uVd
                                        93DQvzlZGczhEYAJPT3GYGLUC4C33Gu83CkQUSrRrj6Ou4FjfF+bOPhcE8tF/wFZJGOyg6QrHIAV
                                        3bz/vA/z8g8jE6PjD54bPJ2kqukckQd+Rwe/k7BqRI84OFuiapH/bEUCcp9ZogStg9CaQAbCdiNy
                                        056CAUSkACJNSon5r8mTjwA+A/Ehpw9pzzgi4hJvN0RX5mOpV2Oj/d3vupUBTqgXxTqRGMy7UPps
                                        XzPnYE35RnU2oBuNZySm12qKwHp/JxT/9LSzuiK6rIIf8wSsIsfmWGf6Y7GKZG9hVbR+iuk0jgD+
                                        0wFOh/xabfZzP8/7zzwL/N6v95ZoDQ3HIjwHAtup6hFYL5hEPpJ9Eru7TAQErNriMap6bkoV7LQ2
                                        o8L7G56mPFmJZ+B7ntVxaLcnIK71OIXSPT0aybpY34Llwt8TpVtJB91UA3A4FtMWHCoije5xPh2r
                                        lBQEqoFM/BO406tYbaiqfURkXpETGgDuBCxS8HMyMXo43t1V9ZIqk49AwkZg2ocpPud/9vlvaeO7
                                        tRE4q4k+X3CC0ZIjLaFkMn4eV8HSs8K5XhPL+Y/JwxQsBWwOMC0St388fj+GeJx9/NXWuDUPYn1b
                                        gSCsHJFgfHy1DrKbsDLB80qRAidbQTTdHOZGRGZhqVqlbgRh3TyMRQH2dyDx084oSPeo1f7RdVtP
                                        1pPnP1jUkjz58KhJ0H3dLiI3q+r2WKW5HTEtDdH8DQOG5SJdHXkDLkQC9fuw1MmzohtyXqA+3I/v
                                        CFX9O7AgEZFky2hjsOjp58q0/R9jXvZ70lR3Sptd4f2tnaY8WRv2jxWCgDio+zwW9SBHPtQB6UtY
                                        U7CrMEG4FAGayws6AmDYETg9lITFUmXOAQ7BvLDrOig5IGpEONgByO1YU71iXtng4b0E6zuwqh9f
                                        ADG/w7xg71cDWEaRjyHApVg4+H5MgN6SA4tEQDw+VwWi5noRwO/hWox+WFPBdbC+HxthnuWBWF59
                                        iCKsVMJD0+Qkrhlr/Dcdi7o8A7wBfOT6giA8X4xF0gL4n+djDBGYkP/fU1X7+z4/g6U7jfTvr+Tb
                                        asa0HPh7QcOwAEsfEmCUqr6CRbkmYGlCjVj6XUsMvEPKYDR3McHJr8kWTGS/Leb5v83XZWchHiF9
                                        bgRWOS52IvT1v+8BFpeKWPj3zwF2UtUzgFtF5DlVXQnThByMVaH7FFY15o5obsrhBQoC9ZpIoP4/
                                        TBy/SkRCgpZrmt+f+ojIxen5lWwZ11uLlxL/XBl3c7mqjkp6kERAMJ1esmSl7DXMYbhjtyYgXlP/
                                        Jkz3ke+aLVjE41wReSkA2o4kHnkQ5SBjR+Ac73J9iY9jItbo7odYtGaoqk51L/x+mMf+mbYAjYPU
                                        952o/MBBTK0f92Cs78gFVToPodP5z7EOve/7742+PpqLkKJi3v5eqroqpnsY4URjENbDYyOyqkKx
                                        TcJE7h9hoWhxsjCPLGWqjwP/Xr697R2Yfs0B4GTgLlW9F2sYt7hIaeRG/7vG/9/DU812wVJp1o3G
                                        1Ij1A5mMdUNXf0jUOqgORKm/g+0tsNKx+TraL2Cd2Sep6vuYp3MSVsFpUVvr0UmSOoF6G+t98gus
                                        O/d/PXe86lGQaG0f4Ou4IXqo1mNpTI9EZanj4wxRtw2x/io9Md3Maap6PfAXEXkG03+sBOyOlUme
                                        WYljj6IhzVja56vuLPgMmZ6o3tfLRDJdV7Jky2ovVWAfP1fVX5TjGZpsuWxBhfe3XpryZEtxiFzf
                                        rQlIBCCeiR7ikHkXnwR+4iLzOsyLXK4bZwCqlwPXq+prDiwHYB7nfTEP7EXAacDhInKyqn4KE62P
                                        Am4JKT0l9lHjJ/ZSLJ1rEJkQuckB/788B69iwDLa14FY1at3sd4b75EJiXtEnd17+iuUr13Db2jb
                                        Y6HdHv5e3FF6HhYVeM7P97vAB1h0gOi8q6/HvljqUxD/hl4MgbSJj2EYlqqzF3A8Fl16TlV/j+l3
                                        5hW5sERVd8KqeoVKR5OxVLMHnYRO8e2r76+Hk42eZCldPZycFHzMfXxOVsaqp23v8/MNLMqDH8c7
                                        Nu36vnsZ3vK5melkdDGt+1oEQfpfsJK/n3Gwf3G1yUe0djby6yDWfvQj6+syvYT2QxzgH+lze7/P
                                        2eZ+nR2hqrc5ERnj5P1j4lNhgoX3d3kTq9C1dXSvWoRF0F7KzUuyZO1dZzNU9R5gzzLuZl8sGvlw
                                        mvFOZRUnhOVy5ibrNvYcWQp19yMgkY33gx1O6+7QAEM81abcgCOAjH9iaUE/dPB0BlYm8Q3gaBG5
                                        wTtGnqCqs7Byo4OB77fjYi64V3sU1hX8CL/xxFqQAz0VpaLkQ1U/j4np38NSpHZ3cB6IWS8sbawG
                                        8/YP9b/zNgvr9fAEFkV5DRNgT/NtrerkZISz65WxmuTbOiFbJdpWg89PP1pHTab69sdi1Yj+BJyM
                                        pS8cjFXv2hs438cyxL+30BsJHgMc7u/d7KD2HtdV9AW2dIA/HIuOrNWOqWz0dTzax9eEVXGa5CSr
                                        F5bWtQbW+2R7B7D7Rtto9vl6DYsGhbD8It9Gb79WG4ALVPUhEXmz2mDXnQMHRCSxnqxi2QQn8C1F
                                        vhcI+ZpYvuksLAryERZ5/I4T2uOciNzhJPFZvCxyBcFhSMnq4WR1QXRtxDqQD9NzK9ly2P1lJiAA
                                        56rq10RkepruTmPVqICZChIka+uZN1tVf+7PtrKWbK6r0gFqBFrvwoSe4xzANGPVO3YGXi83II+q
                                        Ds3H6vtfCMwWkSYnJqdjkZGtME3I57DqUC2Y5/c+B2KXYD0irinSyyIWzV6AlRwOQuugBTkLuEtE
                                        Xi83sIzIx+pYZGeaE4D3fWyDo483+VhnOjCeikULxmDRjBmYPmchFhWox/Qem2De7a19Ec93Rr2y
                                        f+5lLK3lXixaMcM/08vXRQGLCPT1ddrDicqmWETqWCd0fYA/YlWSLsIqF/3MQewA385ZTmbWx8T1
                                        F2FRkgKwnqr+0AlHs5OW1307b/lxx9GZWBwfKpr187Ft6OSqlwPVxZh3fwrWBfwfmM4mpHOtimkb
                                        vuRz9hUnKk0sma620AH6XAfrJ1SLfETrZxMsYtZIpv2Y7XNzi6+LtopF7OXzdrGTK/H574FF5L7g
                                        hPJQ4EkReSrfR6SCHsPFqrq1E2h8rIF03e/nhhT9SPYJbVQF9jHIr6Xz03SvsATkzXSPStYOXFwR
                                        rWk1q2DVeOnLV/ytkPIz10HdMKBnW1WGOpoQ+X4m+e89HHTciXmzTxeRPVX1qw5CGrw/Rg2WNvJD
                                        zGt7naqGClAa7SPklI/BGij+iCzNKGhgDlfVkzDPdyUI4HwH21s6mPqLA/MWsjz34O0tOLDugaXK
                                        BMAdztXmZALyV4E3nazcipVXDaLsUGBgLf+5AdYtPaQ7beUkBScA4/w7M52YjPe5nkWWhnW8k4xz
                                        Ma3EJU5ig33af/7ayeNiJzLHYY0UX3UQ+TcnVb2xaNhGTgxC9GaziICE8/aSg+6P/LsvYd7wHv6Z
                                        TZzQbev76+dk6wU/viYf77TovBd8DtZwMB887Sf7OXi+yjcn9YjAkSyp/ejvToV/RkC9KKj39VMA
                                        3vDrY0+sLPcjIvJHT0v5GhYlvMmvn2qkDoR0sZ18rTbn7p3/TZ3Rky2nfeD3zJFl3s/PVfW2JEjv
                                        NFZb4f1NTFOerLNYtatggaWdhMaDTWRe672AKxwgL9HDoYzAqsbJw2LPXZ/tJXn/qKobez56g6pu
                                        rKqfct1GECCf76SqtgQQCcdxPhZuH+rHOthvDD8D7hCRJysUBZmtqmdiPU7mYJ23d3OQXOdAK0Qh
                                        cPC3sr/fB/Pyj8KiGXc7iA7aiHpM3L0xFq1ojojmQCdxz2PRkVEOvsc7eA3NCGudqKzmJGkT/9wU
                                        B+ITfI1cj0URfufbCKlXNwH/xqoU9cI6koe0n/19LN/08bdgUZOrnFj0888ucILyqpOGIEwOZXVX
                                        xlLTtsA0GrW+nmf63NVhkbGnsQpOC5y8remf39QJyaxo/YcGlrN9XC1OhlbCqmA9Gp3DalRNUyw6
                                        8SMnH7H2Y5LP+Uygtoj2I27+F/pr/ERV+/n21AkZTtj6YJqXOdUA+BHpqcXS58J13OTX7zgHjlCh
                                        9Mlk3dLj2KKq/3QnQ7ntICyan6z61qvC+0upol3cvPrqQKwZ8ruJgHxCsO+/Tsa0Fj/LfWRdzGv8
                                        eoXH1UoE7ADk78BvgZ+5V/ZXWCrWNFU92oHry1gu+MeC5yKpWKG/w7tYxZ//I0snGeCg5hgvmdhY
                                        7vn3Mb6tqodg4tppmA5kjAPiKQ7yezhwfhuLDsx14LiKA+l6B+CbAds5YZnnoHsmJr5+zc/l61hn
                                        8DleArePE4EBEfmcRFZ9aqG/1MfcF4to7ImlVF3j6/giLO3nBxGx/ZWvrwIW3djTQX8jFi35u4/3
                                        QiclL2PN757DCiFM9OPu5w+Kegejq5CVEJ4CXOf7mOnz08vBaSBNq2KezY18vkb7fl70NVPjZKUf
                                        WXWlAhZRC3McepLcJCKzqkk+vG/H8WSRD8iiHy9iqWYtbXx/NSxidh0WRdnIz0cA8Ruo6i5YCewP
                                        nUhWExyqqq4D7EpWnCBYiJCm9Ktky2tvVWg/x6jqLSLyXpryFY6AvJ6mvMvbAY5tHsK0yImALCeg
                                        udcJSMip/thTo6o307piUqWBR42ITFXVa7EIwRH+7+cwL/6NmGf6qIhgtCWUDe//ERMib0AWMWjA
                                        PPN3AzdWIvXMCdb9DsJ/6uSih5OIrbEyuqGxYKgEFcoH4wD7Qyz16CHgSswjPMHPW51vs8VB55eA
                                        L3k+/UdkHv7e0bmf4iAv6C4WYh3ZH8MiEc9g0ZNaJ0x7Ylqdfr6ttzBR+iTfxq1YJOZkLPpwNiZo
                                        fsCJ7htYes0YB9KDMT3GTk4iZtG6H8ggsp4gQd8i/jCpc9KwwNfIGz6O+f5efyckQ6L5DT0lFjrJ
                                        C6lYA8kE/wN8O8+F00f1PO5fxyJl+ejHOCwa1YRXfssvOR/zQVgq3J4+vyf63I3y93/v89XHicnM
                                        KlZuCWMOkcECrfUf90ZkPhGQZMtjEyq4r0OwQivJViwCkkhnFzbHa7t0l+Op6yTjGOOv1WhdDWsA
                                        sImIvFyilGclT/qFWAWl+cD3ROQeVf0Dpjl4ABOj94iaFNaVSD9RB1MzVfVcrAJVAC69Ma/7Sar6
                                        rIi8W6GeB4u8RPDBPvcjHeg3Yp759x1I1zlIDtqFaWRpQn2cuPT28/glrETvupgeYzPf3bMOVP+L
                                        pR694QRmKlmp3RrM6/8pJ2j1DtSD5uBOrGTua1hZyUucCNzk4PAP/r/QSFCwhn5fwETiZ2OlXp91
                                        ojHX3z8Q+K4f89NOPF7xtfm2j7fWCVKIdqzl8yJ+vAP852o+1uF+HCOctEzAKnS9g5XFvMCBfE8f
                                        x8AcsQjagz9gqU3v+zmreCqSr93hWOQiJh+NftwP+rEJxYXi4bhG+vHeAnxVRI6M9lPvzoj+WNTq
                                        khxxr8Llr7VOmoI1+fjDfStZso6wKRXc15GqerWITE7TXlXrXeH9TUpT3qVtNSzbJBGQDgC+AZBM
                                        w9I2TnMAHqphfQrYVVVHUx3xaZw29R5wA1Yl6nFV7UnWS+Jir6KFqq4MnAB8RlX3FJF5JUBNjQOs
                                        Qx1ghrK8jZi3/geqegplrpIRRUHGYd7m8zAdxdpYGtVCTAz9Rf/9NSw1ThxUD/PfZ2Gee3FguooD
                                        7qexqMhYB98zsEjA3OicDnXAKVhUZBMWRpwAACAASURBVJqTgCCED9Wn+jqR2QPTC8zASuvOxMTB
                                        4uTkeicKLZGuJ3Sd38r3NdrB7dl+DEOdFH0Xi65McyIUmhHWOcgeTNaxveBzEqIbL4rIAp/PGrIo
                                        SS9/DfY52xqLImzlxGaKf663fy+2Ft8vwCgRWVgNb7vPYy+f96YcqajH9DHXevW4UhqoQOZP8Dnf
                                        HfiXqu4qIq/5937rDUr7+PFWrV59iLp4tG7DiBCGql+X+jpJ6VfJOuIam6eqD2MVICthO2FpqMmq
                                        Z4MruK+QmZCs69r63elgqh4B8RSnxar6uL8VV8MajIl0e4tIYzXTHByAnYtVYDoXy8HrB9wqIv/2
                                        buL7YWHtdTFR97revIwiFbFqHEyejKVcDYjAeIODtEdF5IEKHLf4mP7j4HJVrFLXOMwjvw6ZOLpv
                                        BMSmRje0BVhUYpqTkTnRORxG1rBwGKbDGEqWctVAlnbUkywdq8FvmqOxKjHjsDSdU7G0nQFYsYKT
                                        fbuzsdS2gh+T+sEFLc9/sIjJN92LcCWW0vQnTAMT+pVs6iRwKPB5B5/9yPpd9IwIkvrfAgxW/fg0
                                        feBz85ofx3Sfr4mY1uT3ZKlnQ7GowAZYalZI81EnWd/wbU6v4jVacBL6C7LeNficD/A1/Ero8VFs
                                        G36/CeWVw7lfC2vk+WVPdawTkbdiwlLlXifi878aWfWrcI96wu9dqfpVso6y5ypIQH6sqreLyII0
                                        7VWzDSq4r+uqlUWSrMNsq0RAOvgZ7z/f8Jvv9mTVgEKX7iudoFQl7z0qsfmeql6OeYHP98XQQ1V3
                                        dlD8Bf/KVcDv26pQEEgIlgZ0I6YvCdV2ejtovUxVdxKRCeUEYhF4et/Hs4vPeyhJO9PPT1gz7znJ
                                        CM0Eg17jG1h0YTHmyVf/f38sIhIqSd3gxzcH75/AkmlHA8kiDptg2piFWLRgthOhO7HKUo9ikYun
                                        ffzFUpRC345LnYD0cOLxVyz96hYHxXVOQob7th7z8c50AtDiZGlaREBWcoAqPherYxGPQT7+rzoB
                                        W8lJyIdkWptV/L3/+rbG+1hDFGVLJz9K+xojdjgA97U61EnTxIgsz/Y5u8XXfCBOpdbYIt/md7C0
                                        vCf9GD8P/E1V9xaRud7rQ4FClXudtLjgftdoDYWO7087MSaRj2QdaJWsarMOFo19Ok17Ve4xdVQ2
                                        nea5NOtder3UOnZJBKQDwW/wUjeo6u0ONueTdVUWzMv9RCdYAIL1mzgQq4r1O8wTf4h/5FHgDBF5
                                        VFXFoxstInJ2GwRCgTOBL2Ne9yBIn+8g+GhV/Q2VT0G70sexqYPqEf53L79pNpPpNeY5uJzvpGKs
                                        A+l3HLBOCl62ZSVS8edVtY/PyRcwTci2WBWI0BzudlpHD1ptyqNYL2OanV2wSk7nklXnetXX2SgR
                                        mdJB6yXuM1Pj4HUtLOKxvnvAarAIjkYEbmE0t09hlS92VtXL/FqpmNfdU69+5YS7gSx60ddJ6y1O
                                        qpYouxvGqaojnEx9gEUJZ/l1tNiP78vAVar6fVzsX+W0prCGdsCqrhX8fIR7020iMiM9FpN1sE2r
                                        8P4OTASkatavgvu6tcLkNlnH2zAqGzHr/gQkBzIfcEDYGIEAsJD0GsDkalXDCVoQEZmkqudjVZe+
                                        hnnL33ZCcrOD3K/4/z8HzFbVaz29RIqkYtX6Q+csTBMSvOqhN8hJwFMicm+5oiARmN3QQWID5t1+
                                        FfNS9ybrdN6XrApUwcfa6L83O2CuI4vkbAxs5uBbIiAOS49mhc8v8nke5uB0IVZ1qwEr4XqSj2ss
                                        WfSgUOT89cA82KEZU28sTepaJyAL/bi2de9UWH9Ft9mesQOFKC2r4ERysY99Eiba7o2l9RT8OBb5
                                        58TH1N9J1+eBg1X10lDsoBLXparujUXo8qlX/bGGg/fZFC9BPsR+aB/gZicwi7HIz0xMbP4SJrD/
                                        rYOhacDPw7x1Am3Fj3N/h1TBBz8JoU6WbCk2s8L720dVzxCRhjT1Fbf+FdzXn9N9qsvb1t3tgOo6
                                        2XjGYn0dvkVWZacFS8fZB2s6J9XlSlrj4/gullbza+BPLj4eqqonRqDlESw1a3opoBLSuxyg7Y6J
                                        3EMq1gAHfWeo6usiMr4cgMfB+QBM3xJEcdcU+WiBrFKVdJI18z5ZTv5wEXlMVWsjkhNbiNqs7n+3
                                        +EPg7GgbndXCOT8f6Keq54vI3AqQj62wCEdDRD5ClO5J4DIXz9aUIGGCFZOY4AR2OBYBGgj8Mre2
                                        wHRUv/UqcTVUIeXSnQIFVd0SS88LxxII2CUkb2Ky8thHVdjnpngPq2QVtUoJ0K8SkTfTdHdd82fh
                                        txIBKYNFdfTnqer9WFrNNL9A5/hD/7PA9V5lpypexygKMt0rVP0dE14vVNUfYelYa2PpJb8Abmin
                                        6Cscy4mYl3tdWqdibQWcoqrH+hyV4/h3w9KCHsA81JDpJpbFwndqOmhcozDtRW0OjNZgEajtMXH6
                                        IOBEF/0/X2T/6sd1DJa6NcHPFZgWpAnrU7JKB4+/PbYsc7wQq5z2oapeJyKLykg+1nKy3URWLlL9
                                        73cxwf+kNkpOh+N6HfO09iPrAr+uE5NNsaIEg7H0vtOcfNRWswKW20F+3MEhEOw+dzgk8XmyjrY5
                                        mCZsSAX3uWMiIFWxdSuwjw/ISpkn67oWivgkAlJme8EB5XBai9H3Bv6M5ehXswlbEI/fgvWluMYB
                                        716Yh/1lLGf8daCPqq4uIu+0g4DVYik5/4fpL/pEXpIGrAfJU5houhx2rx+TdLL1sIQQOWgrfJ6O
                                        wVKw1MHiNVhK0LjcOhmKVXEaTBYBeQA4BUsDgsxj3+kdImQ9TspFPvpildi2pXXPj4Jfkw/4q5AH
                                        4dH5ESdLz4nIWyIyxwHWe3jeua/7OicmawP/8+9XBdhH+x7qBCRoipr8vVf8HkUV70HJuqn5tfcc
                                        FvGvlH1fVf8gIk3pDFTUtq3APn6WtGrdwnbsjgfVaQhIJEYfr6pXY9GAWIxej3VGf6oTPCBqPHXq
                                        JCzNai+svOupTjwexlKqPgRWV9WNlta/wbdXi/VD2c2BW/DED3ZAfa2qvikiz3W091VEZnelh7T/
                                        OllVT8M6sB+PVSsSsp4NDRGJi8H7OCzqcYuITMv9r6tYoYzruw44iuK6DyFroLiwxGbC9fFdJ4Tv
                                        q+qvfb6b8+seizBMJNPmVHl5SUFVv+HHHaIf4V70FxGZnluHyZJ1pI2twj5HAi+mqa+Yo6MeS7cu
                                        p50iIi+k2e7ya6UvVnk1EZAyT3QA6PdgFabmB1DgPz+DiZpfr2Zn9Kgs73OqehVwLHCuiDzjgttX
                                        gSOwFJNG2p/OEwToJ2JpV5tEJGQQ5oW9SFX3LXdp3i5yYYqILAQeVdUXMdH/Nv76LFYaFyxS8BBW
                                        6nYU8GToAJxExK3mM5DagzBheIhEEjkBXgQu9Upcpa7BQI7mYSkAw7ACC99R1eedyCwm6yEzH0tl
                                        /NCvr2pGP9TBwTFkVfiICO39ad0kK7NNq8I+N0kEpKK2aZm3fzFWPj5Z17fPO/5LBKTMwD480N/G
                                        cs+/TZb+0YiJV/fz/1c7Pzx0ED8Ti1is6oLdKx0AL8Ry2p/z35fqMY2qYk3BPPp/w0TSAfw1YGHb
                                        k1X1FyIyZ0UGQlF5W/H0ngdV9SFM4NzHX6Gb+Xzgo7h6VAKRS5C5gqp+GeskPzEiH4FUzPCH2jNO
                                        VprbOi8i8g8nhv+HpRDu4q+8LQK2E5Epvv7bQ5LKYbUi0qyq38RKJKuvnxAFOjmQprRukpXRqiFE
                                        35bypfcmW9L2L+O2/wpc2Ak0dMmW/7ncA8tG6JZW0wknvMZ7RtzmoHtOwDXOAkMef6FE5Z1PDMBU
                                        tcYrKNX579IW+HUQMh3TfDyJpU9t4wBuW0yv8lDUdLA9oLoFS2G5z8lMDMhCad4jgcN9rlZ4IBT3
                                        2fDzMkNEJrju4A0R+UBEpoWu1fn+HOkm97HuY3PgOlo3GwyAKKQHXk9Wlnhp260VkXEicoQTdbAo
                                        x5mY3ugBLPJxgoj8r1QX9TxJj+8Vfr3WtnWttncOgBZV7Y1VsYv1Qz2d/N8bVa1Llqxc1liFfe6t
                                        qiulqa/I/XZ9zJFaDjsf60W2MM10t7AvUhmtUCIg4fr0n887QBnuD//+mBf2S8C+ywsec4SjhwPX
                                        goi0BM9uqM61tDkUkXlYmGx94CwROUxERmPe3svywKkdFnpWnOxzIGQRn6EOEC8g69CcLJpjP7fh
                                        /NaEv8NnEvFYksA5qN7d11focB4sFILYAUttK5BFANsk0xE5OBernDUQeEZEDvD97YylC5S8RqLz
                                        2VtVt/Q0x4/34S91x0Ht0pwHpYcrodjFtmTlphuw4ga3AaNDpCitmmRltGqJwYekqS+/swf4QZk2
                                        fwIW+ViUZrpbrJU+WDp+t7VOR0CikrxNWIO4Vv92IHSgqq6yNBCUIxm1ee93RDgWq2pPVV1DVT+t
                                        qrsBP1XVPYCapXg8AxgJYq8tVPVpVd3bIzkLPuF5acbE1ENYMhe9p5OQf6vqptGNLVl2bsP5LUTR
                                        qmRtE/+LMD3Txg68G6LrDizSdxFwdLh3LC0aEEX0mrAO6D2AP6vqOlh3+untSBUI+/8N8C9grKre
                                        Chyrqnuo6sbexyZcz4U4PW9pUZJI+9HbH+L5tVIP3FgtzVmyFc7mVGm/66SpL7t9Bji4g7c5BthD
                                        RP6e0q66lR2AFYfotlbXycf3MJba9GnMK1SPRQIGYzmUV/vnmiMg8XF6iAMGjQF65O0dikVXtgA2
                                        wwTLQx309/PtPgW84rnpRXPPo+2Nd/ByDpZW8l40nnbdFKLPF7AeF1f5mDQii8E7NhT4nhORlE6U
                                        bLlJGzBPVS/HhOP/8n8FDVYoTzsC+D2mxzqjnf0wwjXyT0zcvQ0W3fuRWpv4klGp0A9EVbdz4hNS
                                        w/YjS2OYiZX1bXSR+4vAmyLSGMYdEZLa6FgCMQ3aj339XhOutxD9uAIrYJCus2SVsLlV2u8ILG04
                                        WTk8PKpD8GhvB9p5wHV+r0vWfdbKSOD07n6cnZKARFGQGap6HZb6MZFMEzIc2BO4FZgVQIqDgxY/
                                        gTUewlrFwfo6wIaquol7IXo60RhQZAjNDlC+AJygqse3RSIi8HWuql4JzIk8Ee0lH6HxWouq/gxr
                                        8hYiPsFzG8Sw84GvichD6VJN1sHXXjNwp6p+Brgcq8YW1l3oTN4XE5avrarHLa1xYNBAichcVf0N
                                        1nPm01iK06KlEHJV1V5YCtcAv57COAIZGIiVwgY4xAlUjaq+7g6M11X1XazPTlO+EAGW8hhKHcY9
                                        SOY4+bpVROanxoPJKmTzqrTfYWnqywYoV8a0bx2V5vYv4KKl9RhL1iXXygDMydftra4LjPFBrPnX
                                        CLLGhAUnIN8FzncPaW9gDQc2I4GNnLBsgnWRLJWiFEiLRK+66P1dgX+LyENLK/3rpKkxEKD2gpXI
                                        yzsQOBsTmUPrjtyhJOodwKmuMUmVnJKV4wYoIvKCqu6HRfS+Fa2/cI20YL1qVlHVXwFvtnV9OAkR
                                        rIzt3zCv3cKldDwPlbm+jTViCroMctdzISIktWSpJEPJqm7NxirSTVHVN/z317HKXuoE5rO01n4M
                                        Au4mK0+arrNklbBq5fCPTFNflvvpqljfqS93wOZux6pc/S85Q7rlWumBZdJsnQhIFS2KgkzwXhuX
                                        OSioJ4sM/BwY6fnkmzt4WKvEJptzJIMIyMz31yInOGEfc7GUrJ+q6svAR0tpJqix2Lk9QI+sadtG
                                        wF8wMXvw8tY46Wp08HeWE67pYRyJfCQr07VXIyLvqepRmHj8RLLqWPVkndj3BNb0/z/sKU5FU6qi
                                        NKgjyUpTt5S4Nmrsh66FeQ7z11NIRQypBz2xdKn6iCho9OqPpTUG+8Cv8Q+wZqL7saTWqh64RESa
                                        EtFPtgIQkO2r2V+rmwLKT2PZDBssx2YWA5e48+aNdB/qtmulDvgp5thbIayui4zzX5gntjeZFgQn
                                        G8UqShT8lY9qxOCl0W/0zX5zqC+ynf5OBvYAjhKRsxxgtZWOpe1cbGIflxZV3QXLMx/m46mLxlnv
                                        r8OBv3vOfQJDycpNQgq+zmaq6ulYBOTPZML0el+nLVia1h1+87w+atRZKLHtee28Ngqq+lssshk6
                                        kpO7B9Tnruu3sf4vA3L/U7JISQ1ZlGRtJ/2xhWO8BXhmWa7rZMk6yAHwHtbIttJWD8xKZ2G5weRq
                                        mE71pOXYzK1OOl4QkY/SrHbr9dIL00f+dEU67k5NQKKGZlNU9ThMdD4xAhaaIxr4z7j5XPAmxR7S
                                        +hw4mehA401MlP7l6GYcROGHqeojwIvL6yUK3l37VY/H0q4CsamLxjTUgd+RIvJIAGcJDCWrIBAS
                                        EZkP/EVVpwJ3OdAP4vRavz76YjXo11fVM13vUTS9qh1rOEQFd3XirRH5CNfFN7DIzGeAdbFUy28U
                                        cSQ0RfeBtqIkcW+ToDO7ZkVv9pmsajapSgSkfyIgywUk18bSRU9xR8iy2LvuyHkZGCMiM9OMrjBk
                                        9VRgnxXt2Ou6wMkJD/+7gf8Am5J5QCUCJg0OMub5hT+U4lGNBkwE+xzW1fhDrIpOo3t71wfeobWn
                                        t4BFSX4DHAjM/aSgJNJ79MXCqt/1f8X57SHf/gHg+KT3SNYJSIiKyN2quj1wDVaqNy9O74c18VtX
                                        VX8lIhOLkfW21nAkCh+MlfyVyMnQ4Ps7Dbjbyc3o6CZ+IhYtGYH1Czq4iLOhrShJuD8MAv6OVdZK
                                        lqwaVi3wOSBN/TI9z/v6PWl9LB11z2X4+p3AS4433gemJF3HCrV2arACS2dUydmQCMgyAKBpqnoF
                                        lhbxNubVhMyjOTj31Vew3hwf+sU91n+fDDQX6xTq+xmrqocCN5BFW4KXd3fgOCxi8XHFrU9APoZh
                                        FYZ2pbTe4yLgXBGZFNJZEvlIVq1rMNwwReR5Vd0HuBDYLSIhQZfVBzgIGOZRy5dCxK+d6zdEHE91
                                        IhFSr5rcwTAGuDLuSO7XxnRgut8bHlfVG/xaXce3szFWjOJgSkdJIKt8dUmKfiSrolUr5abvCjbP
                                        66rqZm3d/rDeRT2wCGpfd1CsielDd17K9v+DleWf6venqcA0YEZqGLjCEg/x59HhWIGXFda6hAYk
                                        AgAPAw8BX819ZBwWunwDE5VOdSA/va1885BrzpLVbW7HquccQpZqEoDRMcDTIvKfZUnFCuJcVd0R
                                        E5uPYEm9x3wHcycAV4jI7FT6M1knug5DOd13VPV7WL7qSTkSEsTpnwWucyLxz0jYXmjLI+TEYi+s
                                        ElxcBa7R97Gnp2S26kgeXcuBkCz0B/00LKUBb156GrC6k5FtsdK7cZRkMKZ1eSV370mWrJJWrV4g
                                        PVawef6Zv8pl1wGPpWd4Mi+vuzmWRbN3mpGuI0IP0YlZLkp9BnjVwcV7Dk4WxfX9c8CkGJkJv2uR
                                        /cxT1bOwqjmxl6LJvR8nquoY4MP2gCr/tQB8B7jUvSix3iM0PBuM5QHe40BM0o0rWSckISIiH6rq
                                        GVhE8WJaV8iq8/U+0v+3qar+3q+rUrqQUPVqINbzI2wjTr06ByvLvQQxKHUtx/8XkVlYfvvbwJOq
                                        ehPWEHGoOwTWw7yaV3uJ4BT9SFYtq1Ylqp5p6jucgExV1fuA17BsjEnAh6naWLcmG3X+PFzDnyvb
                                        kKXbJ+tqBCQSpD/jBKQkUSGKaiwrgIhSvt5Q1WOBm8k8vKER2lexLpU/ARaXAipRylUtph851f8V
                                        V/QJ234bay74XESENF3Imu/fIuXaVSmimqzkNTLf0yI/xFIjA5mOI4aDMEHmhqp6goi8n48chnLU
                                        /ucfnLjEqVdgqVeXi8ji9l4b+c+UiJIsdFIStCR9g9MhrYFkiYB0exuNib/bffvDHIghitoeofkQ
                                        4Hu592ar6p3AKN//B8C05HDsNLaaqh69DGtiJV8L/XxdbJ+msBsRkLZA6dKiGp+U7GAisYudaMRV
                                        f1qw8r+jMSF5bf6BEZGPlYGrgH3JPLp58vF3rLng2O7e36MIoWgTNBaZB+0qY19BSEgzcKuq7oBV
                                        qduAJcXpzVhJyjW8E/oTsX6DrLHhQf6gbo6ukWmYJuowERm/PMS81L0hFymZS7Jk1bfFiYBUxK4W
                                        kduW45nQA4v6ro7pQtYDDmDpfT/6s2S/hw9U9d+YZmQsMDHdj6pmfYD/S9OQCEhVgJ4DnQWqeh7w
                                        FWA1supbc90LcgTwX+DpOLUk0nts7qBsG1pHPSBLK/kNcJmIzOguUY8I0MXArrAs505VQ8nUGrLK
                                        LDXAyj6PYTv1fi7yTeSKbtY/04hVSwte92ZM9Bn+v4jM8z4/pPYta4+XmDB1R3KSI/5PqeqeWGTw
                                        QFp3Tg/9QnbA9E8XAFd5mlMPj2qMxLoFh/McUq+GA78FHinX9RFvM0Uek3USa6nSfnulqV+me8di
                                        rGLZTEyD+oiqXoNVxdoeON7JRntsHeDo3LPkLuBRPH1LRBakWa+YPfQJ8PRArKJV/zR93ZSAVApc
                                        ub5jgqr+CHjMQVW9L64CJig61z0eE90b0uKRj/2xDqhDc+Qj1nscDNwmIou6GvApFQ3IRW+0iLeo
                                        hz/kevpcruwX7UD/fQ0sZB3KpNZhfR7Cet2gTIf0NllRgEaskAFAo6rOw9J0JvjPjzDPfKhathDz
                                        WC7CtEhL9bRXkkxXaj24OP1of1ieSVbKOu4Xsh5WRW6kR0M+UtV64ErMixiE54EAPkeUetUdnBvJ
                                        krXDUgpW18UOzVhPsTdV9W4s+vtJvel7kwmW56nqVcAjwOvFKnkm6zD7QES+vxzPwzrHM6s6ptnG
                                        ceKQNLWJgLT3RlJw0PMEcBTWrTxOL2nBqv1ciKWINKlqnar+Gqu2I7SudBW+2wTsJCKPR+CtUwOf
                                        IvnzWuJzIWLR31+D/OdqfiEOxpo97vAJhxKXTAUrm7qsD+tAbuJSzstDbMZhJZ/HAZNVdTowAyu7
                                        +JGTlI+W0v8iRGO6ZPpdRNg/UtVzgNexynSwZEpWH6ya3OaYh/CbwBdprfsIqVd7i0hDikwkW8Gs
                                        WhGQJIzu2PviDOByVX0I07dtvRyb6wMc669Jrr+7X0SmppnulCQ0lIZ/C3hMVS8ENsIa5h6RZikR
                                        kHYBKweIN2Di2OMiQBW8ujsDp6jqRVhE5CCyLu1xpauhDspOFpExwaPbmYBVKS997NX3z/TBIhkr
                                        O6tfBxiGhZ4HY1GLzdvY1cTo92Jet97FhodFTfqRecgHlTqU+BCKkBjFhGP49maX+Cw5whMsro42
                                        3F/FbAwmMmxQ1Yn+9yR/NQHzRGR+XnzYls6psxN2v/n+S1W3AM4C9mDJUr0FJx33uJco7nY+3+fz
                                        SOCFRD6SJQJSMUte9fLcG8eq6nexZqnf7oBNroU1sDtDVS/ASp2PTzPdqdfAYqzowChVvdafb4cl
                                        ApJsqaDcS4ie5wx2SzI9SI0D2F9iorIhtG4uSAS+zgPO86aKnQZU5Rq6FUsdqsdSpEJ61Fo+B/tT
                                        vNt8DPSnkUWBevqrt89HnjBoRCzCA7hvbr2GCmdLy7FsK12nf5F9h/di8WcQAIa86HrfbjFCMz8i
                                        JYv8mNfAGg5t3MZY/qSq72LpXVOdqDaIyPw2zlWnjZJEhF1EZJSqHoZ1Rz+NLP0wXDeFIgQyFHu4
                                        Avh7ELunu1Cy9GxOBKSLA9CPPO10IfD9Dtz0ccBxqno6cKuIfJRmu9OvhQ9U9RTgLuB8zIGbbnLJ
                                        ioMqB1STVfUkrEnZxAh8B4A0xEFVrPfAwfYPgBtd2F418lHMs55r6NbXCdWaZEK6tbHc/a2KbHIi
                                        S0YwekfA/lPR77EVcmQhvAa055REgL2ULSLzttfl9hfbKn6cweJGXCuX+E5+W31zREkiYvKxmL3I
                                        +AYAP8+9/wowxknJKOAdP845+UhJZ46SRNfMDFU9G9PY3OTzEZfq1WjO4pK754jI3BT9SJYISEUt
                                        decu731xkd8P+2DFOjrSfgMcrqq/FJGn0mx3flyJRfj3wRr6rnBd0RMBWTZAVSMi/1XVbwG3Yjn/
                                        gyIioiwZ9QDYRUQeDKCx0oAq6DeKRThUtZ+Pc6iThc9RumHORKx6VB+WjGTEEYzeRdbX0rzYk4Ap
                                        mIBZMQ0F7i1q9tc4LEJRi2kr2iIgDf5ZwVJ8VipCgpRM+N7if2/gx1br36nBoiO9sajPQNovJOvv
                                        2y34z+D5l9w4F/m8ruwkrxjRu0hVX8LqxU/AGlnNLXKuO02EJCIhi4GbVXU88Fef47hKVrDQ7Xx/
                                        7xeSyEeyFdWq1ZE8EZDy3xcXeBPXjTA9ZEfaWsBNTnKuSVWzusR6mKaq/4dVUvthIiDJSi2UIEq/
                                        AxOCXeQAMh8JCeTjSeAnIvK/Suo9inSAjvUbIZ1qJLCd/zw4t4m80DsQiqER0QhWIMvfLxbBGI0J
                                        xXv7Z9/APNwTyURas/21GFgQgXawqlLL25yp4RPOYc/onIYKXr2dKPR34jLIidtwYDOfu4J/99M+
                                        L7W0jqa0RNtdLbd28nMf7Njo97eBl1T1NeBl/3u6iMwpFSGpFpCPU6hE5FlV3QtryHkwrbunh2vm
                                        hyLyeCIfyVZwq1Y1qkRAKnNfnO3ZFPeWaRcnARur6kki0pRmvEuQ0nMwR+uPEwFJ1tZiaVHV0HTt
                                        GLKUEsg8uxcDZ4vIlEqAqVJRDu9JsraD5BFYxaFdimzibV8P/fxY6iOC0YRFPUKJ1GLRjBYHw/9z
                                        MjHLtzkei2ZMLqVrKHE8IZJU68dAjvgsbT5j0lKztFNa4vfFZNGE2JM0qdj8O9juj6V1rYblda6D
                                        lZfti6V67UDbupnePpf9aa03aXAih6+7fNWuW1X1QayB1XtYGUEtMqcVj47kdCFvq+pPsMogQRcS
                                        Kl5dhjXlTJZsRbdqRUDmp6mv2H1xtKqe5g6ZctjX/fl5gojMTjPe6dfDYi8oMARrXJ0ISLIlwVQk
                                        Sj/HQf2WZKk0w7HO6X8VkTnl7mSfQwAAIABJREFUJB9FPNzB21yPaTi2B7YFvkDrilQNRUDviAjY
                                        h6hGENLHUY1RZALxx5xwTHBQPtPJiharUR6RipKHFB1PoQiR+KTWsjxznNNaSFuf9Rv9bCdeL0ck
                                        cFV/uA92cjLCScQXsIhUi78XeqPEYxf/ThBsF4uSfIssh3QU8LiqvgC8BEwGmopFRypJRqJrZ6an
                                        CLwG3OZz8jTwu3JfM8mSdRGrVgQkCZgra7cDP6N8jev29Pv9z1I6VpfAlwuclG5G+XqeJQLSTUjI
                                        RFU93gFfsH2Bu0SkuRxAqo1Ix+q+YDfDNBzb5r46zh9qA8iiNepguXcErPMAexTwvD+Y3nbC8baI
                                        NLYxxhpvOhg3JCx0QCpVVc51KZLUxvn5OHrjn98M+BtwhYhciJXlfT76Tl8sSrU5sAlZitwXKV2i
                                        uDetK62FimP4dmLC+SJwnaq+CrwnIpPz3b/DmqrgtbMYuF1Vt8VKU57tRR5quuI6SZasg61flfab
                                        POWVfb7MVNUzsfL95bI9sVToy9KMd4k1MUtVf4lVyEoEJFlJIFXjYdR9sFJ4vxKRFwOo60jyEbYX
                                        RTp6YF71LbG0nm2Ar0ZfacgB1uFk+o1YtzEg+vx4THj9MNZYbywW2fgI02K0xCSj2DB9bgp8gshF
                                        iXKry1qCdXlLtrZK81rWc+ifb/HjUdcNTcRK+V6gqqOwxpahkSUuJg+dc8U/28/P73BgU2AfLA1u
                                        FbLO8ETnsm8EWvIRkm0jQvq0qj7pY3gFa5C4kNY9XsoaGYm3LSIvqer3fcwk8pEsGVC6v1G5LekF
                                        Km8PlpmAAJykqmNE5LE03V0CX/7XM2xO6NbHmU51h5CDOmAVEZnWkYSDIl5pVV0Xi3TsAJyS+1oc
                                        5Yg1HEG7kScNMzER3CQsXehV4N2ooZzmjjEA9MInAahdMbWmrTFH0Q6NCEVerxLmfjust8V4LDe3
                                        lTaCTFsjQHM+QuGEdxWsasrnsWon2zrxzFuzbydsswmrMBVSBGM7H3gE02SMy6VplV0zktKtuuT9
                                        7i53fFTChsWOjxVojh+h8ikYL4rINzvBsW+BNSithB0nIrd1gmM+BWtMV06bCnxNRGZ14etiQoV2
                                        9YGIfL7Kx7qKk9NSVTcfEpHv04UtRUA6hq02Ax3SXDDngQ6ajoGYF3xnTEQeGtvFnu58lKMlAqE1
                                        WIRjiv/+D7LqSR8CC8JD3jUPNfFYHIQ2t3fsOXIb61Ra2vhurY+tFosACObRF0yQOTw6rh6YoFsj
                                        kB2OdzhZT46WiAiEeQiELPQI+Thi4X9/gAno+wCPicirpc5rHO0gi/g0lwDZz6rqIcDdWGRjRkg3
                                        ym0n1p1I9B7+4HgMeExVA9EcgaV47Y11ol+NLMUuzEHfaC7za+Zn/moCLlfVx7HIyPRwzssZFYlS
                                        shIJSZYsI/7VyP9+I81+1ey+ChCQIcBBpFSsroIrZ7ke5PLueoyJgHTcQ+MTg6gY4EVe8QHAhpjn
                                        /OLcV97GhMqhWlUAsMWqVD2ENbP7L/A4llYVA2hUtS5UmnKSoO0cs0Qkp5AjGMU6qveghHcfi9yc
                                        R9Zro47WDQKrYe+o6jZeMvFjbUJEtFYBjsYqjL2M6Tx2dYA/zUnfrOBx8nS9/wHbish9EcGsjUhM
                                        HHHQInMeiFSzR9ymqeqzInKlqg7CCg/s5GPag9YaEnXS0ZcsGhaqaw0HfuUvgN+q6sPAOyLSUIIg
                                        dxgJSXeQZMk+tmoJ0N9LU181e42sx1Y57SRVfUBE3k1T3iXsUSxDZa1EQJJ1KIjKgzlV7eULbSfg
                                        S8Ah0ccDCOyNecfyWo46zIv9nv/8J/AsJnieLSKL8sRBVZV2RDciwC3Z4bYiKiF6Epr39fPjGIZ1
                                        UF/PycQQ4DZn9QTvv4P7+ao6DjgqAuTTsfK375B1Y3/UiVQQYR+MVfw6z0lWH0zUvD5wPPCMb+uX
                                        wDeA64Ar/ffjsZ4kp2FRlY2w+ulzgKt9fgdgwsz4/NZ4KeajgDOxiMG+fryDgO/552Y5QWjEKoW9
                                        4uPeXVVfBuaJyByiqIlHP2ppLeCPyWkL0BJFqsSJDE5I7lbVe30ehmEpWt/y+YgLEISI0SB/Lx8Z
                                        +a2/7lPVB3ze34lLKafIRbJkZbGVquVwSVNfNfywQFVvpPxREIADgLPSrHeJdTFXVc8DLkgEJNly
                                        W4loxxAsxeqbmEc9WNB0DHWQGACo0rpHxPsOEEcD/8aiHPH2a13DocsQ4Qiedo0iG3lNyBAsBWiE
                                        g90NME/6SLLmhbG1APsBf/N+EBI3ScQiPfcC9zvh+HbUQf5irOfKUyJyejTG3Xx+7haRpz3KcriP
                                        5VURec4/O9GP5z0ReV5VN/a/p4rIP/0z2wC/xvqWnOoXf1se/4H+c38nIvthYvF6B/ZhTsD0GiG/
                                        +qt+nl9zIvKGn7PR7plqKXI+wrVaiNK2SkVIxJtPjVbV10TkWo+O7EZWsODT8VcpHRnZzV9g3cz/
                                        BowRkXE5DUuKZCRL1rUJyAdp6qtqT1eIgBytqteKyJQ05V3CnuyuB5YISBWIh//dE/NK74yVyQsV
                                        rGJPdNA95CMdoXnbaOBfmHj8/bj3hpfCzROIpY4vAFD/TiECvwMcTH8aE0Fv5gB8dZZsmrXICdEb
                                        /lD7NeaR3x94Cpgbz0UEXJtF5E1VnY5VehqQSzuKwfjnMBF9fx9nvygiEI5lpUhb0svf6x0fZynH
                                        A9BLVeeXIGshdeoaLJJyn5OOs0VkNPAtH8uumN7mSCwacjSm1ZiNRXY2xUTlwaaq6mQsHP8M1sNj
                                        HBbBas6RQyHqSp+LkMSRLqLoyPWqerOfsy2Ar2FpWqH5ZCCJ+chIo5//A/3VoKqX+nG/LiLzEhFJ
                                        lqzDrFoleBMgra5VMgL1eSxLIlknNxFpUNWrgCMSAUn2iUhHRDxWA7Zy4HpU9PFxDvrq/dVCVlUp
                                        AOq3HZg+S1a96mMhbxzlaE8507hnRURSAoBd28nGFg72d6J1VEOdSPRwoHw55rk738d1SOjr4MRj
                                        K2BxrCcodq35mMZhWpChAVR7ZAOfj5FYGtb8aEyh5O3BWORBsbSrQ7AoUvD4z1PVDbBoBcD6qnqq
                                        XwvrEmloQjWwYlPnnxmHVY/azUmDeBrd/lihgD0dTDSIyCOqGrqbXoClN22CpX1tiIkDh2NRpa2A
                                        7/hnZwL/UdVnfV+jReSDIucyrJOWuFxz7lzXOsmboKoTReQeVf0NsBeW8vcZsgIHOLHrQ2sBe+ha
                                        fpq/7lPVy4BR8bgSGUmW7BNb/yrs857UqK7q9iGwmCUdeuWwg1T19lT2vMvYA4mAJFtW5vqxyBtL
                                        KfoK5gHfyz8Se5eLRTuCV+R94O9Y9GBCiHQEL7f/XNZKVTVOOgLh6I1pLL6KecZHOpAnAsKPAc9h
                                        zQlfxVKdfg28JCLXqOo6WGngNf0hOtlB/P8cVI8I3vtSUZmob0aNH1sP4FgstQmfxxABGoTpJ150
                                        EoSPf00sCvOlIrtY5MB/Vz/2YU4GYpsKLGxjGoMG5CAnHy9igvRfAndimotwjp8Dxvq8bxTIppPG
                                        MSLymkfDvuznfT+fq9P9fPTz9wJhGq+q47E+Ho9jjSE/8sZ+H5/jPPD3v0NVqzC3BRH5CLjBIyNr
                                        YZ3Z9/U5GhERrhYfS31u3YYUrTHupXkQa1S5uNRYkiVL1qatXIV9vpCmvep4YZGXuN63Arvbzp+l
                                        49PMdwl7vYLkNBGQ7mAO6jfG+j7EPTuKRTvyFazux1KsbnLAHzz8IdLRUkwH0MZYahw4B5LS4uPb
                                        FotufJPW6UBhnFc68XkpCNl9e6uRaRVGqmo/EflAVd/BdAY7q+pQzLsfvOrr+TEsbd1dBnwbE4Tv
                                        i0VggvXykOTRWAj5ReCrkV7j1w7gR2Ie+v/4RXusk79+InKHqv4bSz8aR9YE6rPAYU62FrdjWrcG
                                        ponIdrm5bsTSGb4qIq/7ewN9XJBVm9lbVc+PiN4TnoL2EaaHacRSnpqBHbF0ve2xSM0XgZOdKD2u
                                        qk84iHhZRGYu5UFXyBHSUMXsfSc3f/PztrcTkr1o3d+kWFRkY+BP/pmLVfUWLFrTmO4EyZItk61W
                                        JYCTrPr2aoUICJhDLBGQrkFOm1T1WiqjEUoEpBuQj8HAGdGCCV7jnmTN4OJoRxNW9elh4HbMoz8z
                                        Kv0aazqal3EsoYRsAP8bYpUw9qR1Q7EFmOe9pxOmaSJyrm9jTVXdHovibIHpQUK33hGYBmN3zHPe
                                        4mA0z9ZHRiC2JDAWkbGqugPwAywycCbmFfwRUKeqdSJym6r+0v+3L3C9E6z3VXU/LFx5hYhM9fHv
                                        Q9b/A+C7/t27ReTf/pmZWOpText03gIcqqq/xfp7bIxV5fqCn9MfOzFYG0ux6u1z834038PIKmSd
                                        6YRgG0xf8wbwgBPNh1X1PfdcPY7pT77u5PFr/gJ4S1UPFZEXVbV2afqfnG6kJjoPb6rqW04Gt3Qy
                                        sg+mHwlNLktFRX7ir7+q6s0i8kC6IyRL1m5btwr7TD1AOodVUoezPeboTNY17NFEQJK115occI7z
                                        v4dHwC1YEELfg2k7/uZgNOg66lxAXFieXE2POqzhYP5wWqcm3Y95zn/i4PE6TNvxE+AzXhlqDJZ+
                                        NSL63gd+QWyNpe6s6mB0oBOM6VhVj7cxj97hQG9V7e0ld9vsMC4ibwPHB/KkqntiVbBWx8Tl80Tk
                                        j17N6jpVnSYi9/nnX8ea64X0t0D0aiLyM0NEjvLP9IrAtPh1UdPGfLb4fp5Q1V9jupdTo4/8EZjs
                                        P4/Off19rMoWfq4XAceIyF0+ln6YhkQxXYWqai9Pu9vdx/WgiNzoFalWc0IyEutFsiWWXvbiJ1kn
                                        MWl1QjdHVZ/ComC/xyJlu/saGhB9vT5a36Ec9HfpxhU8kiUrk21a4f391avmJau+zajgvvZW1TPa
                                        U6QmWaew0d3tgBIBKYM5gJ7vlYIOjUjIxx/BvN9/A27DROWzg5gcqPH20M3LOY5aB8v7ABdhnniA
                                        N4FLnSDMxwTxKzm4/b6InOk9OVbFUn1GO1gegaUmHQPcRaYL+SywuetAPoX14XhSRL7l4/g08H3f
                                        3gDfp1A6EqLBGx+B4TFOlEL/D3Xh9dFYFOEkVX0Qi/LUknUmDzfX85wche3Wqmr43yLf5xOYtqLB
                                        67LXtDHGgp/nS1T1afcm1WH6kQdFpFFV38Q0KYuwcPeemJB8oZ/nsX4O7vCUpYVYdbGQqvWfcAwe
                                        ffqC//1KNE+r+/FPwqJavcOxL8+DJYqYxSlaM4C/qOp1TnT2wiI7w2hdfQxMTP80ViwhaUGSJWvf
                                        PbuHO4oqaY+mme80NrOC+xqEOfQmp2nv/OaY4h/+nE8EJNlSbQwWUfgmMBHrVxGERCdglaNaomhH
                                        S5wS0wFWiIDs3x3cXoh5x7fDohyH0drbvweWmnQ/lgq0u4j8SVWPBC7BUq/+HaU2veHb2tLTbU5R
                                        1XuAOVFlpll+Y10HK637YQC1SwHAMaEbp6o7YilH6nOmLtzbFxjgZKuUwH0CcIiqrhlAfa5IQDOm
                                        XdkUmK2qw32fNUsjSiLyX6wJYp6E3hsB8D/5XLwrIs1ODheq6i+wdKoDc+dNyKIYw5ykBs3PMaq6
                                        oRPJ7Z10vIT1ONEOvunlS/vWuBboeVV9AfgD8DssPa7Z7ykhFesfwIeJfCRLtkygsNKW9B+dx+ZU
                                        eH9DEgHpUvZEdyIgNel8loWpOjaWJkwnEKdeBTHv5xxk1jqIbS4TeEREZovIiSKyB+Zlf9UJxvew
                                        SMwfgB86uN3QS/De7eMbqaqreYO8vYBdgCne3FAwb3wtsHEEyJ/3NKiCR3E+wHQar4XPOQiXZZzP
                                        BSJyf0gXiKIQH4nI+PiY8xbpGyYX+VwgLHdhKUNbYeVlh/g+2krHKrg+pzb6KT7mWieWNcCtWPWu
                                        SeGr/rn/YlGmfZwMXuzzPoYsctbg8xxSyfbCIloPOpFVrNoWqtqrrfEu73oKJM9Jm2DRrI1z95MB
                                        vuYfSsQjWbJlsjUrvL+7ROTDNO2dxuZVeH9D05R3KRvTnQ4mEZAykhD/9RksTWkAlhsfPOoHAlsv
                                        b5pVe82BsDjYftWB7lis9vjFwF8wL/oqWFnV0VjUZjDw2QjAjw3pOb7pB4FHgO28ElYA5BIRB3UQ
                                        vRlwu6pepar9A0hflvnMg+uoB4os5ftBzC9tELWZIrKP35RvBP4c+o+0tX3X6LREP8P2WsL5FZFn
                                        sVS3J/xrhYiwNYnInSJyvT+ABNNczHbB/WysoEEtVqBgV+AsX1d9nVQ+6PtdXO7a7qH6mu9nFzwq
                                        5Wu7wcnHqSLyZlukMFmyZEtYpQXoN6Up71Q2PxGQZG3YeKzqZCIgyZYK+sX7LFzooCwsnAAQf+wC
                                        aNobDVgO0BiA8FMi8nURCb01hjqQrcNStRTY0ZtSPYOli23nYFMiIhJA9jtYBaavY9WzAiDX3Ofe
                                        xBov/gJLKbpdVVcJHvVlOI5CMUDcXpDb1uficYjIGViPjdPJGg9+0rkvONF4xolIXPErlFbu4WTs
                                        DkyI+K6PNez3Lgf7x4nIAyLya6xSmWKVU14rNT/lWNf2Q+swPVC8pkOp5jsqsa6TJetmtnkF9zUJ
                                        K1yRrJOYpw9XUmw8LM16l1ofi4GbEwFJ1q714j+fxfL5+2Ee4hAF2RITJ2ulzoVHJ1ZR1e9jAvnF
                                        wKewXNCQdrW3qvbHStu+AHzOIxaLifQQUYSjICLPttV/wj/3VxH5k4jsjGlSrlDV4csDVEP0Y3le
                                        xciJE63f+Pnq1UZX9GUiIcXSo5xALcaiIs9jKVYfC9AjUvegiExS1Z4O/kNJvntFZHEFwX6tE50v
                                        YlXQQg+biVik71ysgWaKfiRL1v57WQ+yhquVsEtEZH6a+U5n4yq4ry3SdHc5+ytW3OZ3Xf1Akgi9
                                        vGw1gNZpWM7+DQ7SBBPqbgIc4h4PrYBYV3xMWwNXR+//Q0QmqGoDJpo/GNhHRK5X1UcxYXahGKCM
                                        K3e1VXUpqmwlDrSvUdUZWPWsca6XKJQgxlLi946oFFaTa4wYhN6hStcFMUFannO0tOhElJL1bLHv
                                        RCWFW0IpYB/nI9G8lbWkYkjj82jNIVhlsSA+74lF+m7zKmJJfJ4sWfttLb+eKmWp+lXntEpqcjb2
                                        NN/mNO1dBlc2YI7RLm+JgJQfrAUichcmIAqC3f4OcA8GLvIu4uX2YAcwOAoTxw8B1ge2UdX9sTSf
                                        72HC5lUdDM/DoiBtAudiwDc6nrhEaygzLCJyZ7SN+Pst7Z1fVe27PNcy0OzpZstzjuNX3J1elxWA
                                        R6J3LUL2mqPjrsNKOG+Ep19RolpXGW6A6v1Xvk3rRpqDgctE5IV4fhIJSZasXTa8gvu6WkQmpSnv
                                        lDa9wvvrizlEkyVLBKQ7EI9Yl6CqgzCdxEoO1OodrBaANYCjVPVkf69sHuxIj9EAHOD6k7WBY7Gm
                                        eY86GP8weGHaE92IP5cjHC3uwdcin9OoyWANmQd9DUx3MsTfWxUr39uCdUNfj+XUZOTAuqi2wseT
                                        ME1FL6x6VwPm4Z+KpatNwXQOzeRS54p5kaLoSthJYWmAvB06jrDP39K6t0klrMYjVT/081WI9t8E
                                        1HuE7X8xYYrXX7JkyYra9hXc1w1pujutVZoM9EkEJFkiIN2PeAzDukb/kNLiQsUa1F0LjK1EODQC
                                        hAuxSljHqupp3miuFWAs0gcijmZoJKZeIgqiqiup6kruYVkZ69o9ENMJDAZWUdVN/P0NHdQ3+vYD
                                        qO3nn62GNZDVZQ9Eqr9fN+9gFSnGYj1OZqrqNOAjLOWuEesov6DU+cyRNm0n+Qjz3qKqV2BNH/+q
                                        qjtQ/vSr0OBxJNYvJiaCodT0of66TlX/CrwmItMTEUmWrM1rayUsolgJu9LLqifrnFbpXiC905Qn
                                        SwSk+xCPzbCIxx+ij4VGhLHVOFDdDMunPx3vPl1OkJYrXRtA4Yz4/zmALAH0BqAcf9cjGKv68Q1z
                                        gDoC85D3xJprfdpJyNKsGNkoRCA9Py9zl3M68ilcMcEa1Ab5WZXSHsvXgXd9bAVVnervveekZaKL
                                        ziUmcRHID6lcRaMlUf+Ty1X1n8CdwB4icqc3OGwp85I/wM9zc5F7SJP/PMxf96nq37AywdPCeqlE
                                        ta5kybqQrefOjUrYjWm6O7VVuhdIvzTlyRIB6YLEIwfYNwQOAk6NwNh8B7FDIyAd6yGCFuQA4Eos
                                        xafsFgHbQEZqY5BfJPrRQ1XrsWjF6n48Qz3dZisH8guwNLNStcULJeYg/hkTgabo73y1lkUdNBVh
                                        Hz1z78deofoixEdL/KzFigtsUmQ/k53QDVDVt4GHgPGqOsWJyQygySNT+XXWSmPiJLKHiExT1ROB
                                        H6jq3WVe6wUsNe5QWqefaXR++0XnbhrWU2Y34BVVPQN4IlRLS/qQZMk+tm0rtJ9LROT9NN2d2ipd
                                        maxvmvJkiYB0MfIREY/hWErKRRHYbCRLNQrWKlc+AtoFLAXpYEyLUYlqRjVhPJ4iFPpxhAaCPTBR
                                        5IZYqdV1HZRvhgmf27KYaMwl07xIbs0F8N+YIxUhZWnlaP7qq3SqGyJSWBeRlZ4+H/VFiEkhOra+
                                        ftz9fC6DDQa+EP09Dus78pETkpf97/FkpXhbovNXh0VXarF+LQcAW4jIf8sUYQjk52BfF7H2Q3Jr
                                        Opyv+uha2ArrDXKHql4DPBJKgCYikmwFf5b0AL5fgV3Nxkp4JksEhNy9OlmyREC6CvFwkD4Iaw53
                                        Nub1jyMe9REQr8EEzKOBx7EeD2dh5W1j4HUAJg5s6MhUmqhcaxzdKDiArVHVAZhn+1PAeqr6WeAr
                                        fjy9WTKiESIjeU1IAKNzo5voIt9OAOzxDa++nTfAiVgvlUCaJmDRltqIsCxrd9CBmNAcP5aVMEF+
                                        s4/1yz6uwbRfg9KUO26wLuXhuPvl5jAu+Tuc1lVwJmKh+JWwSMnzqjoO055MAxbmUrf+AjQW6zPS
                                        EWueTP9ydPSvFj8fzzmw2cfJ6uCIiPbLEZFv+OtmVb0IeFlEFiV9SLIV2Dbye2+57Vci8mGa7kRA
                                        cjYgTXmyREC6DvHoDewMHOdANQDGoWTpOoUIIKsDsO+RlUz9HJZH38c/14h5yA8CLu6A8X6sJQhE
                                        xj3jIboxEvi8A8YB/vuauc0MiYCm0jqaUZcD3XMcvPeJ5mFpdhtWdepdB9sNDtyn+/zNdeJWwLx3
                                        geyEfcVi+OZlnJ+a3Pmpc7AcCGM4zp5+THWYJqQHVqlrIJaKtj1Z+kR9G8cdIimh2teA3GdD1CRE
                                        TGLSd7i/AF7xNTRTVZ8AnheRyVi0JE4HrIvP/XJaEJ8f4iSpJXpvDvAv4CqsceXewF/82Gqi9RPm
                                        JpzjA/11uqreKCLvxNdZuuMkW4HsSxXYx/3Ag2mqu4QtqPD+EgFJlghIZ7YI2G0OHEXmCQ7EIwaM
                                        4gDteaxC0m4OXDfHoiA1WMO/wxz0agR4D8BEgjPaC8byGgHvmh1rN1Z14Lixqn7JyUazE4wYBLdE
                                        44+1GfOcZCzCPPqQpR+FVxwlGAW85XMzIwLf04BZTiZmO4BtwXpxLBfoXFbPf4gARW81527809tB
                                        8EL54B5+Ex+IRQnWImsqNsTnfieKR1KaormFLGIS607iaMlW/gLYD5irqo1YD5dXVfV14MO4w3Fc
                                        +phl7E0SGg86Mdo/Jn1kDTWv998XYhqhsH5exKJKQ6JNDo6OuxHrNn+U61j+JSKz0t0m2Qrk2BoI
                                        /LQCuzrHC18kSwQkbwPTlCdLBKRzPyhWBb4FXO5vjcM84kMjABvm9D3gCuAaB7kvYxqKHwH/duD1
                                        NnA7cAytPcrbA3t7p/Aa2mguF+k4WqKu6wE0bgbsAGyJhfe/XGwTWIRhngPe2hw4DKB4OKU9+zdg
                                        FZ7GOdGY6d+dA8wRkUXLMMelBOlajAwWIRTLe45LdVxvNQ6PhLX4eVvsBGI2lhqW32a9k8wBmKZl
                                        DQflGzmRLRU1Gec/82WIQzSoX470bheRv/+p6ruY13O0j68QVT+r8zXTHiIivrZ2Ab5I1ngwrNnL
                                        RWSqr8UhTsz7+Vx8y9feYViJ0R4+fomOOxD4a4A9VPUC4JlUJSvZCmJf9OuinPYLERmbprrL2MIK
                                        729QmvJkiYB0PtIRBNnDnVB81QHTAJbsWhs3nPsAuDgS2f4F+B1WGWkvsiZQl2E9QNbNgewfquqt
                                        wJyc2D0uiVtwYKhAT1VdC+uy/jkHfotpnQqlEfgL4HoObUc2gr3iJGoqFtmY7ABzun+/uVSqTxSd
                                        aQ+J0GKEo1KWG5Mu61opBtxFpMkJ3ZQccazDenisikVLRjgxWR/4epH1FUdKevrv/aKxhvFuTtZz
                                        5kBfBw8Bj6rqG1jK28JARmidxqYljq0H8LPcfmqcaN8SaUS+jemawKrtjMeqfL3m729N68pZcarZ
                                        RGBff/1GVS8UkdkpJStZN36+9KS1pqocdr07upIlAlLK1klTniwRkM5rCxwovo15setzIArgAgdT
                                        +wE7At9W1av9fzc4KdgCOBLTPszz7d2LRUaCR7kF04YcgHmFa5xkEKVVBS/2xk5oRgCfwXQdsRWw
                                        yEwgLrU5QAvF04LuBh7GvPBTsa7oM0Vk7lIeqPmmegHUdnsAWQQka46Y5Js3LvJXo8/zk/75AWQd
                                        zodhkaxTipDCJkyQ3ofWkZAQIamP1sNmwM+BN4GngddV9U7g/Zh4hMpaIfoQCiGo6tewiE1Y70Hf
                                        dJeTEPz6ONw/8z/gxiiCdxiwjX/uSSe52+Sun6FOQvB1XShFVJMl6yb2OV/r5bLRwB/K3dg2WZcn
                                        IJ9OU54sEZBOCCrdAztZVU/B0qcacuRjPPATJxKbY/qKkIpyCyaknoQJddfz/++PVQ0qYCld+2Cp
                                        ORqRgm8BNwXQ71qOQU42vuL/rwM2iIYcV6aCrGpUMQtg9k5gDJa6M86PZza5KksRyZBSoDulzbRJ
                                        TEpFFyT3+UYnJe8CL6r6NkNuAAAVIElEQVTqHcB5WIGA9XyNbYz14iiWulVD1vAxryEZGZGSIzFN
                                        zg2q+jIW2ZofpfLVhHXn+xroZDZoX97HooIhqvYD33YT8E8nrmEt/9D3Pw74va+1K7DS1XE5357+
                                        +fNEZE6KfiTrrubRj+PKvJtfJE1Vl3xmNKvqNCqXGtVHVVcSkQVp9pMlAtI57Umsj8HOZD0PClgp
                                        1zr3FL8G3AociwmFj3HAhQOu72Bi3h84IWkE3sDK8h5C5llWrJP6l1X1EWBXLFd4K0zXQY50hKZw
                                        te04jgYHeVcDfwIaRGR6G+D44/SpuNt7sg4nKPk5x1O4mn29veWve1W1P5bSNxRLbfqOr418L44l
                                        oi9kpXMDGdnB378RGKOqtwNjyTQjWzpBjtdmDfAYFoEJJONA/8wk4M/RGI500gymFfqPjyeUZ+6T
                                        W5e/B14tNjfJknUjCxUIy2WHisgbaZq7rL1HZbUZvam8+D3ZCm41aQqWDhC9fG0TlmZVT9Y4T7Fo
                                        xy+8mkkzcD6WSlLAohRDsDSXD7FSpTWYFmRvMl3GJVi1qAD2w88rsSZzf8UqpezgADJUcAqC4LpP
                                        cC4bgTdFZLqndH38io/dQXAiHhVcb0Hfkycm4SUis0XkLRF5BLjJ1w4svX68RGslrL2g3TkU62dz
                                        O/AI8F1VHYalbvWJvi+YnuVSsujHYViaVw1wtYhM8+2vi6UkqpOn893LthuWjtgnIs2L/Lq5waMw
                                        6d6UrFuaqvYFji/jLn4iIo+lme7SNr7C++uTpjxZIiCdExQGMPgipssYgHlsg2bj88C+DtLHY97k
                                        Giy38mAgAPsbMO9ufywK0te3+wqmuRBal8Jdw4FavZOb4IUOqVXyCT0dYF7tdePu54lodHpionEl
                                        q6jyVCiOMHhZNknrqFmjr71NsJLB12ANBvcli3qE3iuPYfnlYGV3v+u/Pw9cHUVxfoSljM0BngIe
                                        95SuIzGRfVi/DVg050LgDSdZKZ0vWXe1/Zywl8NOwdJqk3Vtm1Th/fVNU54sEZBOag6K5mOpVPW5
                                        OVTgJ6q6ir93LZbDXwCOwKocgVWP+heWehK0IDiwuz4iNXHufoh01HXQ+arHxO/DgTUS4eiaZAQv
                                        vUxWLWve8mzSSXUtrSMjq2O6jBCRq/U1ei0WsRBf3yOdZFxNFh38lJNv9YfpVT7ug7HS0LH2I5Di
                                        29N6TNbNnyPDgDPLtPnfYxHEdA11fZuWCEiyRECSxaAPLFpxHuZtbojA2WbAj31Ox2Ie5LlYd/Of
                                        R0TlCr+5FLAoSBAMPwS8ROuStcFLLR18OCHculHyNnfd9ehVq0Ie+codtWmyyIjmyLBgXdgf9fdi
                                        7cdY4B/RfeU4TDg/B9N9vKCqq2G9TwZF253opPho4L0kPE/WjclHL+CEMm3+N8AVpcqhJ+tyNrPC
                                        ++uXpjxZIiCd+wEifoO/mqwaVihnW8AiGmv431dhnt8CsAvuqc5pQTbGUqHwLrXXRGCP6PeOBmQD
                                        /OeXKX8TrGTlsz5YOlMgA2XhOrl1eKkL4wX4HiaCr8H63sz2z2wLHOS/T/z/9s49yqr6uuOfDUIk
                                        MIiSNToBjVFrtMZop5poxWrVpVGLwVi7NCu0qYiPNK2aR5OmXe2KpjVNTZqq1ZRq1KxgaHxCbDEa
                                        qYnGxmpbQxqCUl4RCIwVkBlEwZndP/b+eQ/XQWS4M8wdvp+17prhzr3nXs7Z55z9/e0X0Qq0Bzg3
                                        z4OSSthJRFieAmZLeIghzlRi7lOj+RRwu8THkGL9AH9ei3a5kAAZxFSGty0iis1bicLfEt0oURAn
                                        ohxfz78dTrZc7KUW5GJgTD7/EFELUmpLqg7glgYKkXKx+Qgxv0E0mRDOX9+VNtjZyM0TKYHdFdt7
                                        KW3yYeDh/PzWdKggZovcW6n9uDTtyoAHzGypu49PsdRat91WYIaZ/VLRDzGEz9njgL/sh01fYmbf
                                        0Xkz5Bjo9snjtMuFBEhzCJEeovvQCmr560WETCfSrorQeCKfv5DawJ9VRLehTmIYVakF2UgUEBaH
                                        cjMxo6OLiFRYnaNYumH1hY78nEPrnFrRPJSp45v68N6q/VSdl9IpazhRx7SFCM93EPVLG/M101JY
                                        dxFd2jrTCTqWaCntRLriP+V2L8/zorty3dkrxcs9OpRiCIuPg4CbGrzZpcDZZjZXe3hIMtA1IPto
                                        lwsJkMEvPspwwuXEilYLMWCtTIgeT0RBzMzWAnekk7Y3EQXZI52zGenUVWtBPIXNL/LYLEhn7lLg
                                        OmqdMUo+fm+DBv0tipLN+d2P1FFtSqdmeEXQbn6LgqNeaFS7qZW/LyNqnD5ODNhclK9ZCczK11Rr
                                        PxYRAzfd3d8O/GnaeBdwv5ktcvcDUmSProjoJWl/15nZOkU/xBA9T9tShDdypsO/AOeb2Xzt4SHL
                                        i+xcY5EdZT/tciEB0lz8K9GSdAwRTRiWTtl5QHtGFb5NDBuEmGDenkKmWgtyOPDhFC0vAjPTUXs3
                                        UScyC/gcUcxb+CZRM/ITYnJ5vWNZPy+knpH580h3H1VJLxOD26Epjvr4injcaxuCoxz/kk5ldX/7
                                        TyKt6t8rtvMN4M+J9MF3Eu1xDZiVU5VL7ccRbF37AXAScFxufzExxwZiIOe+1Nr5duQ5Mxt4THYn
                                        hui5Oh64nowyN4hrgSvz/iGGKFnPM5CR4QO114UESHNcHEoUZHU6aqUWpDhSbcTqMTnA8EvpBE5I
                                        IWE5w+Gb1GpBpgEt+fzMFBZ7ESvNY3Lb/1hxFNcQkZH3E21RO9PBm5+O5fbmhYzK90xK5xAa321L
                                        9IP5VWzsTGpdpHp7XTn+w4mc4lIk3gV8ATgLODsFshFh/3vTVvcmajzGpi1+qzJ3pNR+PA7cV6n9
                                        uCxtaSVwm5l1uPuhwAeJFeDhle/XShS0v1jOKR1aMYTEx355bziuQZv8CTDZzG7KYZ5i6POjAfys
                                        38iouhASIM0gQvLXh4DHeGMtyEeB0yuvmZfPTwFOzTqS1cDdKQSOJ8LqPUSNyMP5+rOAY7Pz0NPp
                                        IEIMn2szs81EJGVUOoFPpWN6fH7+lXnzgq0jIS3EROtfJVa5RZP4NvnzzeZ/OJHiNJNIBzwTOCbt
                                        1FKAzDCzDiKKcka+bw7w81x9O5mIaEBE+jpyuxdRV/uRrzknH68P48yhg3+Wn1HSAjvSVu9JASPx
                                        IYaa+DiQqP9rlPi4FrjAzJ7R3t2tWDCAnzUCdcISEiBNdaOxTEu5Ok/eFfmnnnT0PpF58S8Tofiu
                                        dNCuyuc9xcOafM/0HGbYnc7jsjxGl+bMh9eAufm+o4EzcvV5SUWYlLkQzwJ7Enn3r27jv7BH/jwk
                                        HUHNA2kC4Zu20J5Pbat7yU9T+D6S4vdt1FK27gXWpu2cQ0TmlqUocHcfSaRNFTFxW9pkWwrrHmAh
                                        cFe+pgW4ioiwvECka61N0XMMWxeeF/H7FTPbpPQrMcTuCe15XhzWgM09CJyRUY8u7d3djuXEotFA
                                        oU5YQgKkCfkP4E6irqJMM+8h0ptOyRXe7xHFg5bO41npUFZrQQ4j6keKA/l4/v6bwPG5Mj2XSNty
                                        4PfzfZuJiAkpTH4MPJAi5q+INC14Y4pVqV05Np1a0RyMSuHQSe/zPwz4ENEA4c4UIbcBB6Rd3kV0
                                        t9ob+D1q08p/kO8/CTg4tzOXqOcona/a0ub+wcw2pG1PTrtrIQYV3pLC4gpg/8p3Kl3jbiTSBIUY
                                        KsJjhLt/lKhr2tmC3oVEmuNlZrZAe3f3JBcEvzWAH9mqvS4kQJrnAlFqQTZQqwWpOoHjgM9ntOO1
                                        fM0qIk/+48CemVd/B/Df1OaCvCMdxVvz537ABe4+0sxWEoXvls7d1BQiZ1LrZHQQ0d53TH5uNcWl
                                        Mx3BJfl9W/K7jM8bqVakB6+TU47NBOB91KJuS6gNxix056M9hfAH0g66gfOJdrlTiQhZF9Es4VUi
                                        UjI9bauLWhvdNqKVdAvwQ6L2Y5i7jyVqkcYSHbFuzBz1U1Nkj6FW+zEy33+7mW1W5ysxRM7LfYG/
                                        IVKldoYXiEjiFDN7VIMFBdEgZKC6YU3Q7hYSIE0mQvLXJ4nWumUwXGnL+14iqmFEUVmJavwWUQ/i
                                        6TyWWpAPpAgp25ydv58NtGah2KP53P5EYfotZBetyueWdKpN6Uh2UCtYnkithmA28MVe/j9i8DKc
                                        6Iw2v3IsW/P4rshj/XK+roiO0rp5BFEXMoeoz2hNEfLD3PavA6fla/+ZqB+qr/0oraUd+BhwYtru
                                        UuBBdx8NfIatW0J35GddnWJbtiaaXXi8zd2n5Llz/k5sanUKj5PN7G4z26i9K/IauQ64ZoA+7j3a
                                        42IgUdpNY25Eliu6M1JUlBkbECvAf0zk43cAX0sHb1w6ad8jOhTdms7c24m0mNtzOvRMopjxXcTc
                                        kY1EG1TSSRxJrc1qEZQbiSnTUCswL99nHvBdYrV6KbBcN7zmErtm9jN3n1oRHwcCJ6RIqNKRQmEM
                                        W0fnXqPW+az8+2qi2PxkIjVrGZG+5cTKWKn9eDbFshPDq/4gf98E3JJ1HRcSdUWj0yY785xYAtxp
                                        Zj2Kfohmvt4DRwGfJaKLfeU54AZgXqWVtRD1PJC+Qn8PC5zs7l9WLaiQAGkyxzBvSs8QcxQ+R6xE
                                        T0xxcAwxiO1Goj5jFpH2dDTRZvfrZrbG3W8hQvkTgGnu/pV03DqJNKyL6z86nb/h+ZpN+fq9KsLj
                                        OaKQ7ZH8fmuAdXL+mt7mXkuRsCydortSRPwKEZGYBJxSER5LUoiMSjHqdSJ2Sj7Iv60noh97pLAp
                                        swyuN7MNae9TUwAZ8ASRljU6Rcm7qUVdXkp7vApYJPEhmlR4DEvhMY2oseorc4jc/v8ys1e1Z8V2
                                        rvXr3f1TRB1ff3JA+hmrGnGuSMgICZCBvVB0u/sdKUDKoL8SlfhDosvQaiJV64PpvE0jVprXEzUi
                                        5xIRj/OBXyNSqwrdFcFhKTqqkY5qG73PpgP5LBHl8F5upi5HsKkdopJy5zlvppPonPL97KZ2ONFm
                                        +QQiulZlKVtHRsrAymKvRxPpgvcSBe8QjQ7uyTTAthQmY4mi2b9P+784nbSq7ZdBifeV6IeOnmii
                                        82xUng/TqLWs3lFWEvVUPwAW67ordpB5RNvzj/Xz57x3ZwVIzsD5ortfa2aLdeiEBEj/i4+SHrPQ
                                        3a8C/o6toyDvIYYTfp7o7/0QMbitnYh23ECk0pR2i+/LR5US6YDaqnIRHY8S6VyPAM8DL9QXMRbH
                                        z8xcqxNDxua8emwrx3cdEZV4wt2/A3yZqC/6HaKeqNQA1UdGqhyW9loVLUX8Xk609e1Me/5xFuNe
                                        QAwdLNGPcg5MN7Plin6IJhL3BxEd4S6nb52tthCLTQ8D/6Noh9iJa32Pu3+VSG2d1I8fNTl9k76e
                                        NxOIutSjgHZ3P8XM1usICgmQAbhppXM1J29a49JBG02sMJ9DTD9fSMwFOTuds8uIVepzy6YqP8sq
                                        csnnL45jS277GiK16ul0OqvfZ6sohxy/oS+At3H8NxAzOn7u7rOIdKp2YpjlRypvKXNsJlbsr5ta
                                        F6tL0k7vota+txP4qpm94u5X5nt7KmJ5JNF8YY6Okhjk1+9ReX09CvhtIpVxR1lJDCF8khjqqfo6
                                        0ahr/Lq8xt5KLcrcaKa4+/VmtqgP58/B+d0OTvE9XeJDSIAMoBOYK2fLgOuI1a/SeaqbSIe5HPgk
                                        sDZFxf65qnFIdVP5s4taF6vS6agzb3BziC5Ia6rRDEU5RMUee3qxiVfSbua7+31EzdFpRKrfCRWx
                                        W2qJ6qMiR+Sj6nAtcPc2IvpRbeVYonR/ZGYdin6IQSQ2hhORuv2I3Pf2FNUj+rC5O1NkLwSWmtkW
                                        7WHRT9f0Ne5+SfoXJ/bTx1zh7ldmneFbPZ+OIhZX90nfZqqZzdcRExIgu8Dxc/fZwF9Qy38fRqwY
                                        X5ii4rwUFcUhK6vGVQewpFi15k1uLjH0cHE1vapa8CUHT/QmjOtuFkWQvFQRI7cTzRJOSLulF1uE
                                        raMinURq4YNE3nB1Va4zbX9e/l22OTic7ikN2FTbAH7tye6+PhdhuogOf68QndvKo3QBHJ73tOpj
                                        NFGnNC6do3cQK7Rn5vM7ynNEisrPiPTFZWb2sqxLDOD1fJW7Xwp8mjd2PmwEHwIWu/vNuWD1ZteU
                                        kUTa1tfyqaXARWb2v3Wv25PI+GgWxrn7eQ3Yzr+Z2VpZ7TZsWbugX270ltGQC1M4rKg4cG9GJzGM
                                        qpqfPwu4H1hUDWdWV7W1x0Vf7bTehvKGMhF4P9F6t9w0VhDpVL3VilARJ1Z5/UTgDDN7SNGPQXG8
                                        R+Q1RWyfhUQa1SKipm51ivEXZcdvamMnExH63Ym/NrObd9GCwunAl+ifFr1PETPGFqRfUsTIKGJR
                                        9AhiCG1ZeJoNXGNma3r5rmNTtO9unGhmy3Rl6B1FQPqXB4moxSRqg9ggVu3qO1mVdJcWolvWfcBj
                                        ZvaLykn8ek2HboJip1cfeumMZmZlXscSd/9uCpETgS9UXlrESGtFeFTrlVakPX8DeFxdr8QuYgvR
                                        XbBET9YC/5fPbSDmL63L3zfkdfglYMP2Vn6FGATX725grrs/DUwn0rsbybH52B4vE1Hz+9VoQeyQ
                                        DWsX9NvqRImCTEkxURUg1DlqZUV5BjAT+Gm1oFzRDrErbLfy7z2IWqVT8ybXnn9aQuTR10dEiq1P
                                        MrMfKfohxG5z7Tikcn3YXVhuZk8Ogn1/MJE+9Qn6VsvUF4H/t8DdZvaCrF9IgAy+C/JoIiR9Wj5V
                                        hgVWU7I+DXw/hUePRIcYRPY7rK7JwXhiTs25xFyEejG9KcXHDcAnd6SQUQghxE5fs8cSLdKPz+v0
                                        AQ3c/Abg28Rw42eyjlAICZBBeCEoUZCTiDkdC4hOWBD5lTcBj5jZ89X3SHiIwWrLdTe5Q4HfBT5T
                                        eekSspWpmc1X9EMIIXbZdXsYsC/R7a2NWBx6Z/7cl+haOIZo0rCJSAnvqDx+SdQ/rSI6Hq7KNF0h
                                        xGB32vIxxt1v9uBWd/+wu+9T/1rtMdFEN7XXf3f3I939Cnd/Pm38T9x9uGxaCCGEEGIXiZD8eZi7
                                        n+7u4yQ8xFAR13XPHejuF2UeuGxbCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEII
                                        IYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGE
                                        EEIIIYQQQgghhBCiv/l/88UwH3sGKYYAAAAASUVORK5CYII=" alt style="display:block;border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic" width="150" height="62"></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                          </table></td> 
                        </tr> 
                      </table> 
                      <table class="es-content" cellspacing="0" cellpadding="0" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;table-layout:fixed !important;width:100%"> 
                        <tr> 
                          <td align="center" style="padding:0;Margin:0"> 
                          <table class="es-content-body" cellspacing="0" cellpadding="0" bgcolor="#ffffff" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:900px"> 
                            <tr> 
                              <td align="left" style="padding:0;Margin:0"> 
                              <table width="100%" cellspacing="0" cellpadding="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td valign="top" align="center" style="padding:0;Margin:0;width:900px"> 
                                  <table width="100%" cellspacing="0" cellpadding="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td style="padding:20px;Margin:0"><p style="Margin:0;-webkit-text-size-adjust:none;-ms-text-size-adjust:none;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;line-height:21px;color:#333333;font-size:14px;text-align:justify">Dear Team,<br><br>
                                        Please find the below summary of records in Raisers Edge in F.Y. {{financial_year}}.</p></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                            <tr> 
                              <td class="es-m-p0t" align="left" style="padding:0;Margin:0;padding-top:20px;padding-left:20px;padding-right:20px"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:860px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" height="10" style="padding:0;Margin:0"></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                          </table></td> 
                        </tr> 
                      </table> 
                      <table cellpadding="0" cellspacing="0" class="es-content" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;table-layout:fixed !important;width:100%"> 
                        <tr> 
                          <td align="center" style="padding:0;Margin:0"> 
                          <table bgcolor="#f6f6f6" class="es-content-body" align="center" cellpadding="0" cellspacing="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#f6f6f6;width:900px"> 
                            <tr> 
                              <td align="left" style="padding:0;Margin:0;padding-top:20px;padding-left:20px;padding-right:20px"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:860px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" style="padding:0;Margin:0;font-size:0"> 
                                      <table border="0" width="100%" height="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                        <tr> 
                                          <td style="padding:0;Margin:0;border-bottom-width:0px;border-bottom-style:solid;border-bottom-color:#f6f6f6;background-image:none;height:1px;width:100%;margin:0px"></td> 
                                        </tr> 
                                      </table></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                          </table></td> 
                        </tr> 
                      </table> 
                      <table cellpadding="0" cellspacing="0" class="es-content" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;table-layout:fixed !important;width:100%"> 
                        <tr> 
                          <td align="center" style="padding:0;Margin:0"> 
                          <table bgcolor="#ffffff" class="es-content-body" align="center" cellpadding="0" cellspacing="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:900px"> 
                            <tr> 
                              <td align="left" style="padding:0;Margin:0"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:900px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" style="padding:20px;Margin:0"><h1 style="Margin:0;line-height:36px;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;font-size:30px;font-style:normal;font-weight:normal;color:#000000;text-align:center"><strong>Constituent Breakup</strong></h1></td> 
                                    </tr> 
                                    <tr> 
                                      <td align="center" style="padding:0;Margin:0;padding-left:20px;padding-right:20px;font-size:0"> 
                                      <table border="0" width="100%" height="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                        <tr> 
                                          <td style="padding:0;Margin:0;border-bottom:1px solid #cccccc;background:unset;height:1px;width:100%;margin:0px"></td> 
                                        </tr> 
                                      </table></td> 
                                    </tr> 
                                    <tr> 
                                      <td align="center" style="padding:20px;Margin:0">{{constituent_breakup}}</td> 
                                    </tr> 
                                    <tr> 
                                      <td align="center" height="20" style="padding:0;Margin:0"></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                          </table></td> 
                        </tr> 
                      </table> 
                      <table cellpadding="0" cellspacing="0" class="es-content" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;table-layout:fixed !important;width:100%"> 
                        <tr> 
                          <td align="center" style="padding:0;Margin:0"> 
                          <table bgcolor="#f6f6f6" class="es-content-body" align="center" cellpadding="0" cellspacing="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#f6f6f6;width:900px"> 
                            <tr> 
                              <td align="left" style="padding:0;Margin:0;padding-top:20px;padding-left:20px;padding-right:20px"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:860px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" style="padding:0;Margin:0;font-size:0"> 
                                      <table border="0" width="100%" height="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                        <tr> 
                                          <td style="padding:0;Margin:0;border-bottom-width:0px;border-bottom-style:solid;border-bottom-color:#f6f6f6;background-image:none;height:1px;width:100%;margin:0px"></td> 
                                        </tr> 
                                      </table></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                          </table></td> 
                        </tr> 
                      </table> 
                      <table cellpadding="0" cellspacing="0" class="es-content" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;table-layout:fixed !important;width:100%"> 
                        <tr> 
                          <td align="center" style="padding:0;Margin:0"> 
                          <table bgcolor="#ffffff" class="es-content-body" align="center" cellpadding="0" cellspacing="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:900px"> 
                            <tr> 
                              <td align="left" style="padding:0;Margin:0"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:900px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" style="padding:20px;Margin:0"><h1 style="Margin:0;line-height:36px;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;font-size:30px;font-style:normal;font-weight:normal;color:#000000;text-align:center"><strong>Individual</strong></h1></td> 
                                    </tr> 
                                    <tr> 
                                      <td align="center" style="padding:0;Margin:0;padding-left:20px;padding-right:20px;font-size:0"> 
                                      <table border="0" width="100%" height="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                        <tr> 
                                          <td style="padding:0;Margin:0;border-bottom:1px solid #cccccc;background:unset;height:1px;width:100%;margin:0px"></td> 
                                        </tr> 
                                      </table></td> 
                                    </tr> 
                                    <tr> 
                                      <td align="center" style="padding:20px;Margin:0">{{individual_html}}</td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                          </table></td> 
                        </tr> 
                      </table> 
                      <table cellpadding="0" cellspacing="0" class="es-content" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;table-layout:fixed !important;width:100%"> 
                        <tr> 
                          <td align="center" style="padding:0;Margin:0"> 
                          <table bgcolor="#f6f6f6" class="es-content-body" align="center" cellpadding="0" cellspacing="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#f6f6f6;width:900px"> 
                            <tr> 
                              <td align="left" style="padding:0;Margin:0;padding-top:20px;padding-left:20px;padding-right:20px"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:860px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" style="padding:0;Margin:0;font-size:0"> 
                                      <table border="0" width="100%" height="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                        <tr> 
                                          <td style="padding:0;Margin:0;border-bottom-width:0px;border-bottom-style:solid;border-bottom-color:#f6f6f6;background-image:none;height:1px;width:100%;margin:0px"></td> 
                                        </tr> 
                                      </table></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                          </table></td> 
                        </tr> 
                      </table> 
                      <table class="es-content" cellspacing="0" cellpadding="0" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;table-layout:fixed !important;width:100%"> 
                        <tr> 
                          <td align="center" style="padding:0;Margin:0"> 
                          <table class="es-content-body" cellspacing="0" cellpadding="0" bgcolor="#ffffff" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:900px"> 
                            <tr> 
                              <td align="left" style="padding:0;Margin:0"> 
                              <table width="100%" cellspacing="0" cellpadding="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td valign="top" align="center" style="padding:0;Margin:0;width:900px"> 
                                  <table width="100%" cellspacing="0" cellpadding="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="left" style="padding:20px;Margin:0"><h4 style="Margin:0;line-height:100%;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;text-align:justify">Note:</h4> 
                                      <ul> 
                                        <li style="-webkit-text-size-adjust:none;-ms-text-size-adjust:none;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;line-height:14px;Margin-bottom:15px;margin-left:0;color:#333333;font-size:14px"><p style="Margin:0;-webkit-text-size-adjust:none;-ms-text-size-adjust:none;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;line-height:14px;color:#333333;font-size:14px">The above mentioned donations are the ones as recorded and captured in Raisers Edge</p></li> 
                                        <li style="-webkit-text-size-adjust:none;-ms-text-size-adjust:none;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;line-height:14px;Margin-bottom:15px;margin-left:0;color:#333333;font-size:14px"><p style="Margin:0;-webkit-text-size-adjust:none;-ms-text-size-adjust:none;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;line-height:14px;color:#333333;font-size:14px">Kindly refer the attachment to get the complete list of donations for this Quarter</p></li> 
                                      </ul></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                            <tr> 
                              <td class="es-m-p0t" align="left" style="padding:0;Margin:0;padding-top:20px;padding-left:20px;padding-right:20px"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:860px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" height="10" style="padding:0;Margin:0"></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                          </table></td> 
                        </tr> 
                      </table> 
                      <table class="es-footer" cellspacing="0" cellpadding="0" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;table-layout:fixed !important;width:100%;background-color:transparent;background-repeat:repeat;background-position:center top"> 
                        <tr> 
                          <td align="center" style="padding:0;Margin:0"> 
                          <table class="es-footer-body" cellspacing="0" cellpadding="0" bgcolor="#ffffff" align="center" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:900px"> 
                            <tr> 
                              <td align="left" bgcolor="#305496" style="padding:0;Margin:0;background-color:#305496"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:900px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" style="padding:20px;Margin:0"><h5 style="Margin:0;line-height:28px;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;color:#ffffff;font-size:23px"><strong>ज्ञानम् परमम् ध्येयम्</strong></h5></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                            <tr> 
                              <td align="left" style="padding:0;Margin:0;padding-top:20px;padding-left:20px;padding-right:20px"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:860px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" style="padding:0;Margin:0"><h5 style="Margin:0;line-height:120%;mso-line-height-rule:exactly;font-family:arial, 'helvetica neue', helvetica, sans-serif;text-align:center"><strong>Indian Institute of Technology Bombay</strong><br><span style="color:#a9a9a9">Powai, Mumbai, Maharashtra, India 400076</span></h5></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                            <tr> 
                              <td align="left" style="padding:0;Margin:0;padding-top:20px;padding-left:20px;padding-right:20px"> 
                              <table cellpadding="0" cellspacing="0" width="100%" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                <tr> 
                                  <td align="center" valign="top" style="padding:0;Margin:0;width:860px"> 
                                  <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                    <tr> 
                                      <td align="center" style="padding:5px;Margin:0;font-size:0"> 
                                      <table border="0" width="100%" height="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"> 
                                        <tr> 
                                          <td style="padding:0;Margin:0;border-bottom-width:0px;border-bottom-style:solid;border-bottom-color:#cccccc;background-image:none;height:1px;width:100%;margin:0px"></td> 
                                        </tr> 
                                      </table></td> 
                                    </tr> 
                                  </table></td> 
                                </tr> 
                              </table></td> 
                            </tr> 
                          </table></td> 
                        </tr> 
                      </table></td> 
                    </tr> 
                  </table> 
                  </div>  
                </body>
                </html>
    """
    
    # Create a text/html message from a rendered template
    emailbody = MIMEText(
        Environment().from_string(TEMPLATE).render(
            financial_year = financial_year,
            constituent_breakup = constituent_breakup.replace('Since Inception', '<b>Since Inception</b>').replace('Created in Q1', '<b>Created in Q1</b>').replace('Created in Q2', '<b>Created in Q2</b>').replace('Created in Q3', '<b>Created in Q3</b>').replace('Created in Q4', '<b>Created in Q4</b>')
        ), "html"
    )
    
    message.attach(emailbody)
    emailcontent = message.as_string()
    
    # Create secure connection with server and send email
    context = ssl._create_unverified_context()
    with smtplib.SMTP_SSL(SMTP_URL, SMTP_PORT, context=context) as server:
        server.login(MAIL_USERN, MAIL_PASSWORD)
        server.sendmail(
            MAIL_USERN, SEND_TO.split(',') + CC_TO.split(','), emailcontent
        )

    # Save copy of the sent email to sent items folder
    with imaplib.IMAP4_SSL(IMAP_URL, IMAP_PORT) as imap:
        imap.login(MAIL_USERN, MAIL_PASSWORD)
        imap.append('Sent', '\\Seen', imaplib.Time2Internaldate(time.time()), emailcontent.encode('utf8'))
        imap.logout()

def get_donation():
      
      url = f"https://api.sky.blackbaud.com/gift/v1/gifts?gift_type=Donation&gift_type=MatchingGiftPayment&gift_type=PledgePayment&gift_type=RecurringGiftPayment&limit=5000"
      
      pagination_api_request(url)
    
def get_individual_donor_breakup():
      
      get_donation()
      
      donation_dataframe = pd.merge(dataframe, complete_constituent_dataframe, left_on='value.constituent_id', right_on='Constituent_ID', how='outer')
      
      individual_donor_breakup_list = {
        'Alumni Donors': [
          len(donation_dataframe.query('Description == "Alumni" and Type == "Individual" and value.amount.value > 0').index)
        ]
      }
      
      print_json(individual_donor_breakup_list)
      donation_dataframe.to_excel('Test.xlsx')

try:
    
    # Retrieve Token
    retrieve_token()
    
    # Housekeeping
    housekeeping()
    
    # Connect to DB
    connect_db()
    
    # Identify Quarters
    identify_current_quarter()
    
    # Get constituent data
    get_constituent_data()
    
    # Get constituency data
    get_constituency_data()
    
    # Get Constituent breakup
    get_constituent_breakup()
    constituent_breakup = html_output
    
    # Individual Donor breakup
    get_individual_donor_breakup()
    
    # Send email
    # send_email()
    
except Exception as Argument:
  
    subject = "Error while preparing Basic MIS Email from Raisers Edge"
    print(subject)
    send_error_emails()
  
finally:

    # Do housekeeping
    housekeeping()
    
    # Disconnect DB
    disconnect_db()