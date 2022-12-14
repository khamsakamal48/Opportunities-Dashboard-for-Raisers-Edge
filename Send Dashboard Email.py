#!/usr/bin/env python3

import requests, os, json, glob, csv, psycopg2, sys, smtplib, ssl, imaplib, time, email, itertools, datetime, logging, locale, xlsxwriter
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from jinja2 import Environment
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from datetime import date

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
ERROR_EMAILS_TO = os.getenv("ERROR_EMAILS_TO")
SEND_TO = os.getenv("SEND_TO")
CC_TO = os.getenv("CC_TO")
LAST_BOARD_MEETING_DATE = os.getenv("LAST_BOARD_MEETING_DATE")
BM_CORPORATE_PROSPECT = os.getenv("BM_CORPORATE_PROSPECT")
BM_CORPORATE_CULTIVATION = os.getenv("BM_CORPORATE_CULTIVATION")
BM_CORPORATE_SOLICITATION = os.getenv("BM_CORPORATE_SOLICITATION")
BM_CORPORATE_COMMITTED = os.getenv("BM_CORPORATE_COMMITTED")
BM_CORPORATE_REJECTED = os.getenv("BM_CORPORATE_REJECTED")
BM_MAJOR_DONOR_PROSPECT = os.getenv("BM_MAJOR_DONOR_PROSPECT")
BM_MAJOR_DONOR_CULTIVATION = os.getenv("BM_MAJOR_DONOR_CULTIVATION")
BM_MAJOR_DONOR_SOLICITATION = os.getenv("BM_MAJOR_DONOR_SOLICITATION")
BM_MAJOR_DONOR_COMMITTED = os.getenv("BM_MAJOR_DONOR_COMMITTED")
BM_MAJOR_DONOR_REJECTED = os.getenv("BM_MAJOR_DONOR_REJECTED")
BM_CORPORATE_PROSPECT_COUNT = os.getenv("BM_CORPORATE_PROSPECT_COUNT")
BM_CORPORATE_CULTIVATION_COUNT = os.getenv("BM_CORPORATE_CULTIVATION_COUNT")
BM_CORPORATE_SOLICITATION_COUNT = os.getenv("BM_CORPORATE_SOLICITATION_COUNT")
BM_CORPORATE_COMMITTED_COUNT = os.getenv("BM_CORPORATE_COMMITTED_COUNT")
BM_CORPORATE_REJECTED_COUNT = os.getenv("BM_CORPORATE_REJECTED_COUNT")
BM_MAJOR_DONOR_PROSPECT_COUNT = os.getenv("BM_MAJOR_DONOR_PROSPECT_COUNT")
BM_MAJOR_DONOR_CULTIVATION_COUNT = os.getenv("BM_MAJOR_DONOR_CULTIVATION_COUNT")
BM_MAJOR_DONOR_SOLICITATION_COUNT = os.getenv("BM_MAJOR_DONOR_SOLICITATION_COUNT")
BM_MAJOR_DONOR_COMMITTED_COUNT = os.getenv("BM_MAJOR_DONOR_COMMITTED_COUNT")
BM_MAJOR_DONOR_REJECTED_COUNT = os.getenv("BM_MAJOR_DONOR_REJECTED_COUNT")

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
    
    # Close writing to Process.log
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
    multiple_files = glob.glob("*.csv")

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

def retrieve_token():
    global access_token
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

def get_opportunity_list_from_re():
    global url, params, today_date, total_corporate_prospect_amount_in_inr_crores, total_corporate_cultivation_amount_in_inr_crores, total_corporate_solicitation_amount_in_inr_crores, total_corporate_committed_amount_in_inr_crores, total_corporate_rejected_amount_in_inr_crores, total_corporate_prospect_count, total_corporate_cultivation_count, total_corporate_solicitation_count, total_corporate_committed_count, total_corporate_rejected_count, total_major_donor_prospect_amount_in_inr_crores, total_major_donor_cultivation_amount_in_inr_crores, total_major_donor_solicitation_amount_in_inr_crores, total_major_donor_committed_amount_in_inr_crores, total_major_donor_rejected_amount_in_inr_crores, total_major_donor_prospect_count, total_major_donor_cultivation_count, total_major_donor_solicitation_count, total_major_donor_committed_count, total_major_donor_rejected_count

    retrieve_token()
    
    housekeeping()
    
    # Blackbaud API URL
    url = 'https://api.sky.blackbaud.com/opportunity/v1/opportunities?include_inactive=false'
    params = ""
    
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
    print("Parsing content from Opportunity_List_from_RE_*.json files")
    multiple_files = glob.glob("Opportunity_List_from_RE_*.json")
    
    # Workbook() takes one, non-optional, argument
    # which is the filename that we want to create.
    workbook = xlsxwriter.Workbook('Opportunities_in_RE.xlsx')
    
    # By default worksheet names in the spreadsheet will be
    # Sheet1, Sheet2 etc., but we can also specify a name.
    corporate_worksheet = workbook.add_worksheet("Corporate")
    major_donor_worksheet = workbook.add_worksheet("Major Donor")
    
    # Add a bold format to use to highlight cells.
    
    # Add a number format for cells with money.
    # money = workbook.add_format({'num_format': '???##,###'})
    
    # Format cell
    header_format = workbook.add_format()
    header_format.set_pattern(1)  # This is optional when using a solid fill.
    header_format.set_bg_color('orange')
    header_format.set_bold()
    header_format.set_font_color('white')
    header_format.set_font_size(12)
    header_format.set_border()
    header_format.set_border_color('white')
    
    header_format_centre = workbook.add_format()
    header_format_centre.set_pattern(1)  # This is optional when using a solid fill.
    header_format_centre.set_bg_color('orange')
    header_format_centre.set_bold()
    header_format_centre.set_font_color('white')
    header_format_centre.set_font_size(12)
    header_format_centre.set_border()
    header_format_centre.set_border_color('white')
    header_format_centre.set_center_across()
    
    cell_format = workbook.add_format()
    cell_format.set_font_size(12)
    cell_format.set_border()
    cell_format.set_border_color('orange')
    
    cell_format_centre = workbook.add_format()
    cell_format_centre.set_font_size(12)
    cell_format_centre.set_border()
    cell_format_centre.set_border_color('orange')
    cell_format_centre.set_center_across()
    
    money = workbook.add_format()
    money.set_font_size(12)
    money.set_border()
    money.set_border_color('orange')
    money.set_num_format('_(???* #,##0.00_);_(???* (#,##0.00);_(???* "-"??_);_(@_)')
    
    cell_format_bold = workbook.add_format()
    cell_format_bold.set_font_size(12)
    cell_format_bold.set_border()
    cell_format_bold.set_border_color('orange')
    cell_format_bold.set_bold()
    
    cell_format_blue = workbook.add_format()
    cell_format_blue.set_font_size(12)
    cell_format_blue.set_border()
    cell_format_blue.set_border_color('orange')
    cell_format_blue.set_font_color('#0068DA')
    cell_format_blue.set_underline()
    cell_format_blue.set_center_across()
    
    # Adding Header
    corporate_worksheet.write('A1', 'Name', header_format)
    corporate_worksheet.write('B1', 'Open Constituent in RE', header_format_centre)
    corporate_worksheet.write('C1', 'Opportunity Name', header_format)
    corporate_worksheet.write('D1', 'Status', header_format_centre)
    corporate_worksheet.write('E1', 'Asked Amount', header_format_centre)
    corporate_worksheet.write('F1', 'Expected Amount', header_format_centre)
    corporate_worksheet.write('G1', 'Funded Amount', header_format_centre)
    
    major_donor_worksheet.write('A1', 'Name', header_format)
    major_donor_worksheet.write('B1', 'Open Constituent in RE', header_format_centre)
    major_donor_worksheet.write('C1', 'Opportunity Name', header_format)
    major_donor_worksheet.write('D1', 'Status', header_format_centre)
    major_donor_worksheet.write('E1', 'Asked Amount', header_format_centre)
    major_donor_worksheet.write('F1', 'Expected Amount', header_format_centre)
    major_donor_worksheet.write('G1', 'Funded Amount', header_format_centre)
    
    # Freeze the Top rows
    corporate_worksheet.freeze_panes(1, 0)
    major_donor_worksheet.freeze_panes(1, 0)
    
    # Set column width
    corporate_worksheet.set_column('A:A', 50)
    major_donor_worksheet.set_column('A:A', 50)
    
    corporate_worksheet.set_column('B:B', 25)
    major_donor_worksheet.set_column('B:B', 25)
    
    corporate_worksheet.set_column('C:C', 70)
    major_donor_worksheet.set_column('C:C', 70)
    
    corporate_worksheet.set_column('D:G', 20)
    major_donor_worksheet.set_column('D:G', 20)
    
    # Start from the first cell. Rows and
    # columns are zero indexed.
    corporate_worksheet_row = 1
    corporate_worksheet_col = 0
    
    major_donor_worksheet_row = 1
    major_donor_worksheet_col = 0
    
    corporate_prospect_amount = []
    corporate_solicitation_amount = []
    corporate_cultivation_amount = []
    corporate_committed_amount = []
    corporate_rejected_amount = []
    major_donor_prospect_amount = []
    major_donor_solicitation_amount = []
    major_donor_cultivation_amount = []
    major_donor_committed_amount = []
    major_donor_rejected_amount = []
    
    corporate_prospect_count = []
    corporate_solicitation_count = []
    corporate_cultivation_count = []
    corporate_committed_count = []
    corporate_rejected_count = []
    major_donor_prospect_count = []
    major_donor_solicitation_count = []
    major_donor_cultivation_count = []
    major_donor_committed_count = []
    major_donor_rejected_count = []
    
    for each_file in multiple_files:
    
        # Open JSON file
        with open(each_file, 'r') as json_file:
            json_content = json.load(json_file)

            for results in json_content['value']:
                
                try:
                    if results['purpose'] == "Corporate":
                        # Working with Corporate
                        print("Working with Corporate")
                        corporate_worksheet_col = 0
                        
                        # Getting Prospect amount
                        print("Getting Prospect amount")
                        
                        # try:
                        if results['status'] == "Prospect":
                            
                            try:
                                prospect_amount = results['ask_amount']['value']
                                
                            except:
                                prospect_amount = "0"
                        
                            finally:
                                prospect_count = "1"
                                
                                corporate_prospect_amount.append(int(prospect_amount))
                                corporate_prospect_count.append(int(prospect_count))
                        
                        # Getting Cultivation amount
                        print("Getting Cultivation amount")
                        
                        if results['status'] == "Cultivation":
                            
                            try:
                                cultivation_amount = results['ask_amount']['value']
                                
                            except:
                                cultivation_amount = "0"
                                
                            finally:
                                cultivation_count = "1"
                                
                                corporate_cultivation_amount.append(int(cultivation_amount))
                                corporate_cultivation_count.append(int(cultivation_count))
                        
                        # Getting Solicitation amount
                        print("Getting Solicitation amount")
                        
                        if results['status'] == "Solicitation":
                            
                            try:
                                solicitation_amount = results['ask_amount']['value']
                                
                            except:
                                solicitation_amount = "0"
                            
                            finally:
                                solicitation_count ="1"
                                                                
                                corporate_solicitation_amount.append(int(solicitation_amount))
                                corporate_solicitation_count.append(int(solicitation_count))
                        
                        # Getting Committed amount
                        print("Getting Committed amount")

                        if results['status'] == "Committed":
                            
                            try:
                                committed_amount = results['expected_amount']['value']
                                    
                            except:
                                committed_amount = "0"
                            
                            finally:
                                committed_count = "1"
                                
                                corporate_committed_amount.append(int(committed_amount))
                                corporate_committed_count.append(int(committed_count))
                        
                        # Getting Rejected amount
                        print("Getting Rejected amount")
                        
                        if results['status'] == "Rejected":
                            
                            try:
                                rejected_amount = results['ask_amount']['value']
                                
                            except:
                                rejected_amount = "0"
                            
                            finally:
                                rejected_count = "1"
                                
                                corporate_rejected_amount.append(int(rejected_amount))
                                corporate_rejected_count.append(int(rejected_count))
                        
                        print("Getting Constituent ID")
                        constituent_id = results['constituent_id']
                        
                        # Getting Constituent Name
                        print("Getting Constituent Name")
                        try:
                            extract_sql =  """
                            SELECT * FROM constituent_list WHERE constituent_id = %s;
                            """
                        
                            cur.execute(extract_sql, [constituent_id])
                            result = cur.fetchall()

                            # Ensure no comma or brackets in output
                            result_list = list(result[0])
                            constituent_name = result_list[1]
                            
                        except:
                            constituent_name = ""

                        # Getting Opportunity Name
                        print("Getting Opportunity Name")
                        try:
                            opportunity_name = results['name']
                        except:
                            opportunity_name = ""
                        
                        # Getting Opportunity Status
                        print("Getting Opportunity Status")
                        try:
                            status = results['status']
                        except:
                            status = ""
                        
                        # Getting Opportunity Ask Amount
                        print("Getting Opportunity Ask Amount")
                        try:
                            ask_amount = results['ask_amount']['value']
                        except:
                            ask_amount = ""
                            
                        # Getting Opportunity Expected Amount
                        print("Getting Opportunity Expected Amount")
                        try:
                            expected_amount = results['expected_amount']['value']
                        except:
                            expected_amount = ""
                        
                        # Getting Opportunity Funded Amount
                        print("Getting Opportunity Funded Amount")
                        try:
                            funded_amount = results['funded_amount']['value']
                        except:
                            funded_amount = ""
                            
                        corporate_worksheet.write(corporate_worksheet_row, corporate_worksheet_col, constituent_name, cell_format_bold)
                        corporate_worksheet_col += 1
                        corporate_worksheet.write(corporate_worksheet_row, corporate_worksheet_col, f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/constituent/records/","{constituent_id}","?envId=p-dzY8gGigKUidokeljxaQiA&svcId=renxt"),"Open in RE")', cell_format_blue)
                        corporate_worksheet_col += 1
                        corporate_worksheet.write(corporate_worksheet_row, corporate_worksheet_col, opportunity_name, cell_format)
                        corporate_worksheet_col += 1
                        corporate_worksheet.write(corporate_worksheet_row, corporate_worksheet_col, status, cell_format_centre)
                        corporate_worksheet_col += 1
                        corporate_worksheet.write(corporate_worksheet_row, corporate_worksheet_col, ask_amount, money)
                        corporate_worksheet_col += 1
                        corporate_worksheet.write(corporate_worksheet_row, corporate_worksheet_col, expected_amount, money)
                        corporate_worksheet_col += 1
                        corporate_worksheet.write(corporate_worksheet_row, corporate_worksheet_col, funded_amount, money)
                        corporate_worksheet_row += 1
                        
                    elif results['purpose'] == "Major Donor":
                        # Working with Corporate
                        print("Working with Major Donor")
                        
                        major_donor_worksheet_col = 0
                        
                        # Getting Prospect amount
                        print("Getting Prospect amount")
                        
                        if results['status'] == "Prospect":
                            
                            try:
                                prospect_amount = results['ask_amount']['value']
                                prospect_count = "1"
                                
                            except:
                                prospect_amount = "0"
                                prospect_count = "0"
                                
                            finally:                                    
                                major_donor_prospect_amount.append(int(prospect_amount))
                                major_donor_prospect_count.append(int(prospect_count))

                        # Getting Cultivation amount
                        print("Getting Cultivation amount")
                        
                        if results['status'] == "Cultivation":
                            
                            try:
                                cultivation_amount = results['ask_amount']['value']
                                
                            except:
                                cultivation_amount = "0"
                            
                            finally:
                                cultivation_count = "1"
                                    
                                major_donor_cultivation_amount.append(int(cultivation_amount))
                                major_donor_cultivation_count.append(int(cultivation_count))

                        
                        # Getting Solicitation amount
                        print("Getting Solicitation amount")

                        if results['status'] == "Solicitation":
                            
                            try:
                                solicitation_amount = results['ask_amount']['value']
                                
                            except:
                                solicitation_amount = "0"
                            
                            finally:
                                solicitation_count = "1"
                                                                
                                major_donor_solicitation_amount.append(int(solicitation_amount))
                                major_donor_solicitation_count.append(int(solicitation_count))
                        
                        # Getting Committed amount
                        print("Getting Committed amount")

                        if results['status'] == "Committed":
                            
                            try:
                                committed_amount = results['expected_amount']['value']
                                
                            except:
                                committed_amount = "0"
                            
                            finally:
                                committed_count = "1"
                                
                                major_donor_committed_amount.append(int(committed_amount))
                                major_donor_committed_count.append(int(committed_count))
                        
                        # Getting Rejected amount
                        print("Getting Rejected amount")

                        if results['status'] == "Rejected":
                            
                            try:
                                rejected_amount = results['ask_amount']['value']
                                
                            except:
                                rejected_amount = "0"
                                rejected_count = "0"
                            
                            finally:
                                rejected_count = "1"
                                    
                                major_donor_rejected_amount.append(int(rejected_amount))
                                major_donor_rejected_count.append(int(rejected_count))
                        
                        print("Getting Constituent ID")
                        constituent_id = results['constituent_id']
                        
                        # Getting Constituent Name
                        print("Getting Constituent Name")
                        try:
                            extract_sql =  """
                            SELECT * FROM constituent_list WHERE constituent_id = %s;
                            """
                        
                            cur.execute(extract_sql, [constituent_id])
                            result = cur.fetchall()

                            # Ensure no comma or brackets in output
                            result_list = list(result[0])
                            constituent_name = result_list[1]
                        
                        except:
                            constituent_name = ""

                        # Getting Opportunity Name
                        print("Getting Opportunity Name")
                        try:
                            opportunity_name = results['name']
                        except:
                            opportunity_name = ""
                            
                        # Getting Opportunity Status
                        print("Getting Opportunity Status")
                        try:
                            status = results['status']
                        except:
                            status = ""
                            
                        # Getting Opportunity Ask Amount
                        print("Getting Opportunity Ask Amount")
                        try:
                            ask_amount = results['ask_amount']['value']
                        except:
                            ask_amount = ""
                            
                        # Getting Opportunity Expected Amount
                        print("Getting Opportunity Expected Amount")
                        try:
                            expected_amount = results['expected_amount']['value']
                        except:
                            expected_amount = ""
                        
                        # Getting Opportunity Funded Amount
                        print("Getting Opportunity Funded Amount")
                        try:
                            funded_amount = results['funded_amount']['value']
                        except:
                            funded_amount = ""
                            
                        major_donor_worksheet.write(major_donor_worksheet_row, major_donor_worksheet_col, constituent_name, cell_format_bold)
                        major_donor_worksheet_col += 1
                        major_donor_worksheet.write(major_donor_worksheet_row, major_donor_worksheet_col, f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/constituent/records/","{constituent_id}","?envId=p-dzY8gGigKUidokeljxaQiA&svcId=renxt"),"Open in RE")', cell_format_blue)
                        major_donor_worksheet_col += 1
                        major_donor_worksheet.write(major_donor_worksheet_row, major_donor_worksheet_col, opportunity_name, cell_format)
                        major_donor_worksheet_col += 1
                        major_donor_worksheet.write(major_donor_worksheet_row, major_donor_worksheet_col, status, cell_format_centre)
                        major_donor_worksheet_col += 1
                        major_donor_worksheet.write(major_donor_worksheet_row, major_donor_worksheet_col, ask_amount, money)
                        major_donor_worksheet_col += 1
                        major_donor_worksheet.write(major_donor_worksheet_row, major_donor_worksheet_col, expected_amount, money)
                        major_donor_worksheet_col += 1
                        major_donor_worksheet.write(major_donor_worksheet_row, major_donor_worksheet_col, funded_amount, money)
                        major_donor_worksheet_row += 1
                        
                except:
                    pass
            
    total_corporate_prospect_amount = round(sum(corporate_prospect_amount)/10000000)
    total_corporate_prospect_amount_in_inr = locale.currency(round(total_corporate_prospect_amount), grouping=True).replace(".00", "")
    total_corporate_prospect_amount_in_inr_crores = f"{total_corporate_prospect_amount_in_inr} Cr."
    print(f"Total Corporate Prospect Amount = {total_corporate_prospect_amount}")
    print(f"Total Corporate Prospect Amount in INR = {total_corporate_prospect_amount_in_inr}")
    print(total_corporate_prospect_amount_in_inr_crores)
    total_corporate_prospect_count = sum(corporate_prospect_count)
    
    total_corporate_cultivation_amount = round(sum(corporate_cultivation_amount)/10000000)
    total_corporate_cultivation_amount_in_inr = locale.currency(round(total_corporate_cultivation_amount), grouping=True).replace(".00", "")
    total_corporate_cultivation_amount_in_inr_crores = f"{total_corporate_cultivation_amount_in_inr} Cr."
    print(f"Total Corporate Cultivation Amount = {total_corporate_cultivation_amount}")
    print(f"Total Corporate Cultivation Amount in INR = {total_corporate_cultivation_amount_in_inr}")
    print(total_corporate_cultivation_amount_in_inr_crores)
    total_corporate_cultivation_count = sum(corporate_cultivation_count)
    
    total_corporate_solicitation_amount = round(sum(corporate_solicitation_amount)/10000000)
    total_corporate_solicitation_amount_in_inr = locale.currency(round(total_corporate_solicitation_amount), grouping=True).replace(".00", "")
    total_corporate_solicitation_amount_in_inr_crores = f"{total_corporate_solicitation_amount_in_inr} Cr."
    print(f"Total Corporate Solicitation Amount = {total_corporate_solicitation_amount}")
    print(f"Total Corporate Solicitation Amount in INR = {total_corporate_solicitation_amount_in_inr}")
    print(total_corporate_solicitation_amount_in_inr_crores)
    total_corporate_solicitation_count = sum(corporate_solicitation_count)
    
    total_corporate_committed_amount = round(sum(corporate_committed_amount)/10000000)
    total_corporate_committed_amount_in_inr = locale.currency(round(total_corporate_committed_amount), grouping=True).replace(".00", "")
    total_corporate_committed_amount_in_inr_crores = f"{total_corporate_committed_amount_in_inr} Cr."
    print(f"Total Corporate Committed Amount = {total_corporate_committed_amount}")
    print(f"Total Corporate Committed Amount in INR = {total_corporate_committed_amount_in_inr}")
    print(total_corporate_committed_amount_in_inr_crores)
    total_corporate_committed_count = sum(corporate_committed_count)
    
    total_corporate_rejected_amount = round(sum(corporate_rejected_amount)/10000000)
    total_corporate_rejected_amount_in_inr = locale.currency(round(total_corporate_rejected_amount), grouping=True).replace(".00", "")
    total_corporate_rejected_amount_in_inr_crores = f"{total_corporate_rejected_amount_in_inr} Cr."
    print(f"Total Corporate Rejected Amount = {total_corporate_rejected_amount}")
    print(f"Total Corporate Rejected Amount in INR = {total_corporate_rejected_amount_in_inr}")
    print(total_corporate_rejected_amount_in_inr_crores)
    total_corporate_rejected_count = sum(corporate_rejected_count)
    
    total_major_donor_prospect_amount = round(sum(major_donor_prospect_amount)/10000000)
    total_major_donor_prospect_amount_in_inr = locale.currency(total_major_donor_prospect_amount, grouping=True).replace(".00", "")
    total_major_donor_prospect_amount_in_inr_crores = f"{total_major_donor_prospect_amount_in_inr} Cr."
    print(f"Total Major Donor Prospect Amount = {total_major_donor_prospect_amount}")
    print(f"Total Major Donor Prospect Amount in INR = {total_major_donor_prospect_amount_in_inr}")
    print(total_major_donor_prospect_amount_in_inr_crores)
    total_major_donor_prospect_count = sum(major_donor_prospect_count)
    
    total_major_donor_cultivation_amount = round(sum(major_donor_cultivation_amount)/10000000)
    total_major_donor_cultivation_amount_in_inr = locale.currency(round(total_major_donor_cultivation_amount), grouping=True).replace(".00", "")
    total_major_donor_cultivation_amount_in_inr_crores = f"{total_major_donor_cultivation_amount_in_inr} Cr."
    print(f"Total Major Donor Cultivation Amount = {total_major_donor_cultivation_amount}")
    print(f"Total Major Donor Cultivation Amount in INR = {total_major_donor_cultivation_amount_in_inr}")
    print(total_major_donor_cultivation_amount_in_inr_crores)
    total_major_donor_cultivation_count = sum(major_donor_cultivation_count)
    
    total_major_donor_solicitation_amount = round(sum(major_donor_solicitation_amount)/10000000)
    total_major_donor_solicitation_amount_in_inr = locale.currency(round(total_major_donor_solicitation_amount), grouping=True).replace(".00", "")
    total_major_donor_solicitation_amount_in_inr_crores = f"{total_major_donor_solicitation_amount_in_inr} Cr."
    print(f"Total Major Donor Solicitation Amount = {total_major_donor_solicitation_amount}")
    print(f"Total Major Donor Solicitation Amount in INR = {total_major_donor_solicitation_amount_in_inr}")
    print(total_major_donor_solicitation_amount_in_inr_crores)
    total_major_donor_solicitation_count = sum(major_donor_solicitation_count)
    
    total_major_donor_committed_amount = round(sum(major_donor_committed_amount)/10000000)
    total_major_donor_committed_amount_in_inr = locale.currency(round(total_major_donor_committed_amount), grouping=True).replace(".00", "")
    total_major_donor_committed_amount_in_inr_crores = f"{total_major_donor_committed_amount_in_inr} Cr."
    print(f"Total Major Donor Committed Amount = {total_major_donor_committed_amount}")
    print(f"Total Major Donor Committed Amount in INR = {total_major_donor_committed_amount_in_inr}")
    print(total_major_donor_committed_amount_in_inr_crores)
    total_major_donor_committed_count = sum(major_donor_committed_count)
    
    total_major_donor_rejected_amount = round(sum(major_donor_rejected_amount)/10000000)
    total_major_donor_rejected_amount_in_inr = locale.currency(round(total_major_donor_rejected_amount), grouping=True).replace(".00", "")
    total_major_donor_rejected_amount_in_inr_crores = f"{total_major_donor_rejected_amount_in_inr} Cr."
    print(f"Total Major Donor Rejected Amount = {total_major_donor_rejected_amount}")
    print(f"Total Major Donor Rejected Amount in INR = {total_major_donor_rejected_amount_in_inr}")
    print(total_major_donor_rejected_amount_in_inr_crores)
    total_major_donor_rejected_count = sum(major_donor_rejected_count)
    print(f"major_donor_rejected_count: {major_donor_rejected_count}")
    print(f"total_major_donor_rejected_count: {total_major_donor_rejected_count}")
    
    # Set auto-filters
    corporate_worksheet.autofilter(0, 0, corporate_worksheet_row, corporate_worksheet_col)
    major_donor_worksheet.autofilter(0, 0, major_donor_worksheet_row, major_donor_worksheet_col)
    
    # Close the excel file
    workbook.close()
    
    today_date = date.today().strftime("%d %b, %Y")
    
    # # Preparing JSON Data
    # corporate_json_data = {
    #     'Status': ['Prospect', 'Cultivation', 'Solicitation', 'Committed'],
    #     f'Amount as on {LAST_BOARD_MEETING_DATE}': [BM_CORPORATE_PROSPECT, BM_CORPORATE_CULTIVATION, BM_CORPORATE_SOLICITATION, BM_CORPORATE_COMMITTED],
    #     f'Amount as on {today}': [total_corporate_prospect_amount_in_inr_crores, total_corporate_cultivation_amount_in_inr_crores, total_corporate_solicitation_amount_in_inr_crores, total_corporate_committed_amount_in_inr_crores],
    #     f'Count as on {today}': [total_corporate_prospect_count, total_corporate_cultivation_count, total_corporate_solicitation_count, total_corporate_committed_count]
    # }
    
    # major_donor_json_data = {
    #     'Status': ['Prospect', 'Cultivation', 'Solicitation', 'Committed'],
    #     f'Amount as on {LAST_BOARD_MEETING_DATE}': [BM_MAJOR_DONOR_PROSPECT, BM_MAJOR_DONOR_CULTIVATION, BM_MAJOR_DONOR_SOLICITATION, BM_MAJOR_DONOR_COMMITTED],
    #     f'Amount as on {today}': [total_major_donor_prospect_amount_in_inr_crores, total_major_donor_cultivation_amount_in_inr_crores, total_major_donor_solicitation_amount_in_inr_crores, total_major_donor_committed_amount_in_inr_crores],
    #     f'Count as on {today}': [total_major_donor_prospect_count, total_major_donor_cultivation_count, total_major_donor_solicitation_count, total_major_donor_committed_count]
    # }
    
def send_email():
    print("Sending email...")
    
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = MAIL_USERN
    message["To"] = SEND_TO
    message['Cc'] = CC_TO

    # Adding Reply-to header
    message.add_header('reply-to', MAIL_USERN)
        
    TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:v="urn:schemas-microsoft-com:vml">
    <head>
    <title></title>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch><o:AllowPNG/></o:OfficeDocumentSettings></xml><![endif]-->
    <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                padding: 0;
            }

            a[x-apple-data-detectors] {
                color: inherit !important;
                text-decoration: inherit !important;
            }

            #MessageViewBody a {
                color: inherit;
                text-decoration: none;
            }

            p {
                line-height: inherit
            }

            .desktop_hide,
            .desktop_hide table {
                mso-hide: all;
                display: none;
                max-height: 0px;
                overflow: hidden;
            }

            @media (max-width:768px) {

                .row-12 .column-1 .block-2.heading_block h3,
                .row-12 .column-2 .block-2.heading_block h3,
                .row-12 .column-3 .block-2.heading_block h3,
                .row-12 .column-4 .block-2.heading_block h3,
                .row-13 .column-1 .block-2.heading_block h3,
                .row-13 .column-2 .block-2.heading_block h3,
                .row-13 .column-3 .block-2.heading_block h3,
                .row-13 .column-4 .block-2.heading_block h3,
                .row-14 .column-1 .block-2.heading_block h3,
                .row-14 .column-2 .block-2.heading_block h3,
                .row-14 .column-3 .block-2.heading_block h3,
                .row-14 .column-4 .block-2.heading_block h3,
                .row-15 .column-1 .block-2.heading_block h3,
                .row-15 .column-2 .block-2.heading_block h3,
                .row-15 .column-3 .block-2.heading_block h3,
                .row-15 .column-4 .block-2.heading_block h3,
                .row-16 .column-1 .block-2.heading_block h3,
                .row-16 .column-2 .block-2.heading_block h3,
                .row-16 .column-3 .block-2.heading_block h3,
                .row-16 .column-4 .block-2.heading_block h3,
                .row-2 .column-1 .block-1.paragraph_block td.pad>div,
                .row-5 .column-1 .block-2.heading_block h3,
                .row-5 .column-2 .block-2.heading_block h3,
                .row-5 .column-3 .block-2.heading_block h3,
                .row-5 .column-4 .block-2.heading_block h3,
                .row-6 .column-1 .block-2.heading_block h3,
                .row-6 .column-2 .block-2.heading_block h3,
                .row-6 .column-3 .block-2.heading_block h3,
                .row-6 .column-4 .block-2.heading_block h3,
                .row-7 .column-1 .block-2.heading_block h3,
                .row-7 .column-2 .block-2.heading_block h3,
                .row-7 .column-3 .block-2.heading_block h3,
                .row-7 .column-4 .block-2.heading_block h3,
                .row-8 .column-1 .block-2.heading_block h3,
                .row-8 .column-2 .block-2.heading_block h3,
                .row-8 .column-3 .block-2.heading_block h3,
                .row-8 .column-4 .block-2.heading_block h3,
                .row-9 .column-1 .block-2.heading_block h3,
                .row-9 .column-2 .block-2.heading_block h3,
                .row-9 .column-3 .block-2.heading_block h3,
                .row-9 .column-4 .block-2.heading_block h3 {
                    font-size: 14px !important;
                }

                .row-12 .column-1 .block-2.heading_block td.pad,
                .row-5 .column-1 .block-2.heading_block td.pad {
                    padding: 25px 0 0 !important;
                }

                .row-11 .column-1 .block-1.heading_block h1,
                .row-3 .column-1 .block-1.heading_block h1,
                .row-4 .column-1 .block-1.heading_block h1 {
                    font-size: 23px !important;
                }

                .row-3 .column-1 .block-1.heading_block td.pad {
                    padding: 10px 10px 0 !important;
                }

                .row-2 .column-1 .block-1.paragraph_block td.pad {
                    padding: 20px !important;
                }

                .row-1 .column-1 .block-1.image_block td.pad,
                .row-19 .column-1 .block-1.heading_block td.pad {
                    padding: 10px !important;
                }

                .row-13 .column-1 .block-2.heading_block td.pad,
                .row-13 .column-4 .block-2.heading_block td.pad,
                .row-14 .column-1 .block-2.heading_block td.pad,
                .row-14 .column-4 .block-2.heading_block td.pad,
                .row-15 .column-1 .block-2.heading_block td.pad,
                .row-15 .column-4 .block-2.heading_block td.pad,
                .row-16 .column-1 .block-2.heading_block td.pad,
                .row-16 .column-4 .block-2.heading_block td.pad,
                .row-6 .column-1 .block-2.heading_block td.pad,
                .row-6 .column-4 .block-2.heading_block td.pad,
                .row-7 .column-1 .block-2.heading_block td.pad,
                .row-7 .column-4 .block-2.heading_block td.pad,
                .row-8 .column-1 .block-2.heading_block td.pad,
                .row-8 .column-4 .block-2.heading_block td.pad,
                .row-9 .column-1 .block-2.heading_block td.pad,
                .row-9 .column-4 .block-2.heading_block td.pad {
                    padding: 10px 0 0 !important;
                }

                .row-17 .column-1 .block-2.list_block ul {
                    font-size: 14px !important;
                    line-height: auto !important;
                }

                .row-20 .column-1 .block-1.paragraph_block td.pad>div {
                    font-size: 13px !important;
                }

                .row-19 .column-1 .block-1.heading_block h2 {
                    font-size: 18px !important;
                }
            }

            @media (max-width:920px) {
                .desktop_hide table.icons-inner {
                    display: inline-block !important;
                }

                .icons-inner {
                    text-align: center;
                }

                .icons-inner td {
                    margin: 0 auto;
                }

                .row-content {
                    width: 100% !important;
                }

                .mobile_hide {
                    display: none;
                }

                .stack .column {
                    width: 100%;
                    display: block;
                }

                .mobile_hide {
                    min-height: 0;
                    max-height: 0;
                    max-width: 0;
                    overflow: hidden;
                    font-size: 0px;
                }

                .desktop_hide,
                .desktop_hide table {
                    display: table !important;
                    max-height: none !important;
                }

                .row-3 .column-1 {
                    padding: 0 20px 10px !important;
                }

                .row-12 .column-1,
                .row-12 .column-2,
                .row-12 .column-3,
                .row-12 .column-4,
                .row-13 .column-2,
                .row-13 .column-3,
                .row-13 .column-4,
                .row-14 .column-2,
                .row-14 .column-3,
                .row-14 .column-4,
                .row-15 .column-2,
                .row-15 .column-3,
                .row-15 .column-4,
                .row-16 .column-2,
                .row-16 .column-3,
                .row-16 .column-4,
                .row-17 .column-1,
                .row-5 .column-1,
                .row-5 .column-2,
                .row-5 .column-3,
                .row-5 .column-4,
                .row-6 .column-2,
                .row-6 .column-3,
                .row-6 .column-4,
                .row-7 .column-2,
                .row-7 .column-3,
                .row-7 .column-4,
                .row-8 .column-2,
                .row-8 .column-3,
                .row-8 .column-4,
                .row-9 .column-2,
                .row-9 .column-3,
                .row-9 .column-4 {
                    padding: 10px !important;
                }

                .row-13 .column-1,
                .row-14 .column-1,
                .row-15 .column-1,
                .row-16 .column-1,
                .row-6 .column-1,
                .row-7 .column-1,
                .row-8 .column-1,
                .row-9 .column-1 {
                    padding: 10px 10px 10px 5px !important;
                }
            }
        </style>
    </head>
    <body style="background-color: #ebebeb; margin: 0; padding: 0; -webkit-text-size-adjust: none; text-size-adjust: none;">
    <table border="0" cellpadding="0" cellspacing="0" class="nl-container" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ebebeb;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-1" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #193e8d; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; vertical-align: top; padding-top: 5px; padding-bottom: 5px; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="100%">
    <table border="0" cellpadding="20" cellspacing="0" class="image_block block-1" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad">
    <div align="center" class="alignment" style="line-height:10px"><img src="https://i.ibb.co/fk6J37P/iitblogowhite.png" style="display: block; height: auto; border: 0; width: 100px; max-width: 100%;" width="100"/></div>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; vertical-align: top; padding-top: 5px; padding-bottom: 5px; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="100%">
    <table border="0" cellpadding="0" cellspacing="0" class="paragraph_block block-1" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; word-break: break-word;" width="100%">
    <tr>
    <td class="pad" style="padding-left:20px;padding-right:20px;padding-top:20px;">
    <div style="color:#101112;direction:ltr;font-family:Arial, Helvetica Neue, Helvetica, sans-serif;font-size:16px;font-weight:400;letter-spacing:0px;line-height:120%;text-align:justify;mso-line-height-alt:19.2px;">
    <p style="margin: 0; margin-bottom: 16px;">Dear Team,</p>
    <p style="margin: 0;">Below is the status of Opportunities as recorded in Raisers Edge.</p>
    </div>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-3" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; vertical-align: top; padding-top: 5px; padding-bottom: 5px; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="100%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-1" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="padding-bottom:10px;padding-top:20px;text-align:center;width:100%;">
    <h1 style="margin: 0; color: #101112; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 38px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Opportunity Pipeline</span></h1>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-4" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-bottom: 0 solid #FFFFFF; border-left: 0 solid #FFFFFF; border-right: 0px solid #FFFFFF; border-top: 0 solid #FFFFFF; background-color: #193e8d; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #FFFFFF; border-left: 0px solid #FFFFFF; border-right: 0px solid #FFFFFF; border-top: 0px solid #FFFFFF; padding-left: 20px; padding-right: 20px; vertical-align: top; padding-top: 20px; padding-bottom: 20px;" width="100%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-1" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;">
    <h1 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 38px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Corporate</span></h1>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-5" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #284988; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="padding-top:35px;text-align:center;width:100%;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Status</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Amount as on {{LAST_BOARD_MEETING_DATE}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Count as on {{LAST_BOARD_MEETING_DATE}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Amount as on {{today_date}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Count as on {{today_date}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-6" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Prospect</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_PROSPECT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_PROSPECT_COUNT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_prospect_amount_in_inr_crores}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_prospect_count}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-7" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Cultivation</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_CULTIVATION}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_CULTIVATION_COUNT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_cultivation_amount_in_inr_crores}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_cultivation_count}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-8" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Solicitation</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_SOLICITATION}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_SOLICITATION_COUNT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_solicitation_amount_in_inr_crores}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_solicitation_count}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-9" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Committed</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_COMMITTED}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_COMMITTED_COUNT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_committed_amount_in_inr_crores}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_committed_count}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-9" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tbody>
        <tr>
        <td>
        <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
        <tbody>
        <tr>
        <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Rejected</span></h3>
        </td>
        </tr>
        </table>
        </td>
        <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_REJECTED}}</span></h3>
        </td>
        </tr>
        </table>
        </td>
        <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_CORPORATE_REJECTED_COUNT}}</span></h3>
        </td>
        </tr>
        </table>
        </td>
        <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_rejected_amount_in_inr_crores}}</span></h3>
        </td>
        </tr>
        </table>
        </td>
        <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_corporate_rejected_count}}</span></h3>
        </td>
        </tr>
        </table>
        </td>
        </tr>
        </tbody>
        </table>
        </td>
        </tr>
        </tbody>
        </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-10" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; vertical-align: top; padding-top: 5px; padding-bottom: 5px; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="100%">
    <div class="spacer_block" style="height:20px;line-height:20px;font-size:1px;">???</div>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-11" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-bottom: 0 solid #FFFFFF; border-left: 0 solid #FFFFFF; border-right: 0px solid #FFFFFF; border-top: 0 solid #FFFFFF; background-color: #193e8d; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; padding-left: 20px; padding-right: 20px; vertical-align: top; padding-top: 20px; padding-bottom: 20px; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="100%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-1" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;">
    <h1 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 38px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Major Donor</span></h1>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-12" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #284988; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="padding-top:35px;text-align:center;width:100%;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Status</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Amount as on {{LAST_BOARD_MEETING_DATE}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Count as on {{LAST_BOARD_MEETING_DATE}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Amount as on {{today_date}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Count as on {{today_date}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-13" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Prospect</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_PROSPECT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_PROSPECT_COUNT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_prospect_amount_in_inr_crores}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_prospect_count}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-14" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Cultivation</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_CULTIVATION}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_CULTIVATION_COUNT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_cultivation_amount_in_inr_crores}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_cultivation_count}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-15" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Solicitation</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_SOLICITATION}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_SOLICITATION_COUNT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_solicitation_amount_in_inr_crores}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_solicitation_count}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-16" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Committed</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_COMMITTED}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_COMMITTED_COUNT}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_committed_amount_in_inr_crores}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
    <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
    <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_committed_count}}</span></h3>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-9" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tbody>
        <tr>
        <td>
        <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
        <tbody>
        <tr>
        <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; background-color: #d3ddef; padding-left: 20px; padding-right: 20px; vertical-align: top; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">Rejected</span></h3>
        </td>
        </tr>
        </table>
        </td>
        <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_REJECTED}}</span></h3>
        </td>
        </tr>
        </table>
        </td>
        <td class="column column-2" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{BM_MAJOR_DONOR_REJECTED_COUNT}}</span></h3>
        </td>
        </tr>
        </table>
        </td>
        <td class="column column-3" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_rejected_amount_in_inr_crores}}</span></h3>
        </td>
        </tr>
        </table>
        </td>
        <td class="column column-4" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; border-bottom: 0px solid #D3DDEF; border-left: 0px solid #D3DDEF; border-right: 0px solid #D3DDEF; border-top: 0px solid #D3DDEF; padding-left: 20px; padding-right: 20px; vertical-align: top;" width="20%">
        <table border="0" cellpadding="0" cellspacing="0" class="heading_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
        <tr>
        <td class="pad" style="text-align:center;width:100%;padding-top:20px;padding-bottom:20px;">
        <h3 style="margin: 0; color: #000000; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 24px; font-weight: 400; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">{{total_major_donor_rejected_count}}</span></h3>
        </td>
        </tr>
        </table>
        </td>
        </tr>
        </tbody>
        </table>
        </td>
        </tr>
        </tbody>
        </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-17" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: justify; padding-left: 20px; padding-right: 20px; vertical-align: top; padding-top: 20px; padding-bottom: 20px; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="100%">
    <table border="0" cellpadding="0" cellspacing="0" class="list_block block-2" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; word-break: break-word;" width="100%">
    <tr>
    <td class="pad" style="padding-top:20px;">
    <ul start="1" style="margin: 0; padding: 0; margin-left: 20px; list-style-type: revert; color: #363a3e; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 16px; font-weight: 400; letter-spacing: 0px; line-height: 150%; text-align: justify;">
    <li style="margin-bottom: 5px;">The Amount as on {{LAST_BOARD_MEETING_DATE}} are the ones shown to the Board of Directors at the last board meeting</li>
    <li style="margin-bottom: 5px;">The Amount reflecting at ???Prospect??? stage may not be available for all opportunities as it is at a very initial stage of engagement</li>
    <li style="margin-bottom: 5px;">The calculation of <b>'Committed'</b> amount is based on the '<u>Expected amount</u>' stored in Raisers Edge for both Corporate & Major Donors. Calculation of <b>???Prospect???, ???Cultivation???, ???Solicitation??? and ???Rejected???</b> amount is based on the '<u>Asked amount</u>'</li>
    <li>A list of all the active opportunities available and recorded in Raisers Edge is also attached with this email for your perusal</li>
    </ul>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-18" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; vertical-align: top; padding-top: 5px; padding-bottom: 5px; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="100%">
    <div class="spacer_block" style="height:20px;line-height:20px;font-size:1px;">???</div>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-19" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #193e8d; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; vertical-align: top; padding-top: 5px; padding-bottom: 5px; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="100%">
    <table border="0" cellpadding="20" cellspacing="0" class="heading_block block-1" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tr>
    <td class="pad">
    <h2 style="margin: 0; color: #ffffff; direction: ltr; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 30px; font-weight: 700; letter-spacing: normal; line-height: 120%; text-align: center; margin-top: 0; margin-bottom: 0;"><span class="tinyMce-placeholder">????????????????????? ??????????????? ?????????????????????</span></h2>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row row-20" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;" width="100%">
    <tbody>
    <tr>
    <td>
    <table align="center" border="0" cellpadding="0" cellspacing="0" class="row-content stack" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #ffffff; border-radius: 0; color: #000000; width: 900px;" width="900">
    <tbody>
    <tr>
    <td class="column column-1" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; font-weight: 400; text-align: left; vertical-align: top; padding-top: 5px; padding-bottom: 5px; border-top: 0px; border-right: 0px; border-bottom: 0px; border-left: 0px;" width="100%">
    <table border="0" cellpadding="20" cellspacing="0" class="paragraph_block block-1" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; word-break: break-word;" width="100%">
    <tr>
    <td class="pad">
    <div style="color:#7f7f7f;direction:ltr;font-family:Arial, Helvetica Neue, Helvetica, sans-serif;font-size:16px;font-weight:400;letter-spacing:0px;line-height:120%;text-align:center;mso-line-height-alt:19.2px;">
    <p style="margin: 0;">This is a system generated email</p>
    </div>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table>
    </td>
    </tr>
    </tbody>
    </table><!-- End -->
    </body>
    </html>
    """
    
    emailbody = MIMEText(
        Environment().from_string(TEMPLATE).render(
            BM_CORPORATE_PROSPECT = BM_CORPORATE_PROSPECT,
            BM_CORPORATE_CULTIVATION = BM_CORPORATE_CULTIVATION,
            BM_CORPORATE_SOLICITATION = BM_CORPORATE_SOLICITATION,
            BM_CORPORATE_COMMITTED = BM_CORPORATE_COMMITTED,
            BM_CORPORATE_REJECTED = BM_CORPORATE_REJECTED,
            total_corporate_prospect_amount_in_inr_crores = total_corporate_prospect_amount_in_inr_crores,
            total_corporate_cultivation_amount_in_inr_crores = total_corporate_cultivation_amount_in_inr_crores,
            total_corporate_solicitation_amount_in_inr_crores = total_corporate_solicitation_amount_in_inr_crores,
            total_corporate_committed_amount_in_inr_crores = total_corporate_committed_amount_in_inr_crores,
            total_corporate_rejected_amount_in_inr_crores = total_corporate_rejected_amount_in_inr_crores,
            BM_MAJOR_DONOR_PROSPECT = BM_MAJOR_DONOR_PROSPECT,
            BM_MAJOR_DONOR_CULTIVATION = BM_MAJOR_DONOR_CULTIVATION,
            BM_MAJOR_DONOR_SOLICITATION = BM_MAJOR_DONOR_SOLICITATION,
            BM_MAJOR_DONOR_COMMITTED = BM_MAJOR_DONOR_COMMITTED,
            BM_MAJOR_DONOR_REJECTED = BM_MAJOR_DONOR_REJECTED,
            today_date = today_date,
            total_major_donor_prospect_amount_in_inr_crores = total_major_donor_prospect_amount_in_inr_crores,
            total_major_donor_cultivation_amount_in_inr_crores = total_major_donor_cultivation_amount_in_inr_crores,
            total_major_donor_solicitation_amount_in_inr_crores = total_major_donor_solicitation_amount_in_inr_crores,
            total_major_donor_committed_amount_in_inr_crores = total_major_donor_committed_amount_in_inr_crores,
            total_major_donor_rejected_amount_in_inr_crores = total_major_donor_rejected_amount_in_inr_crores,
            LAST_BOARD_MEETING_DATE = LAST_BOARD_MEETING_DATE,
            total_corporate_prospect_count = total_corporate_prospect_count,
            total_corporate_cultivation_count = total_corporate_cultivation_count,
            total_corporate_solicitation_count = total_corporate_solicitation_count,
            total_corporate_committed_count = total_corporate_committed_count,
            total_corporate_rejected_count = total_corporate_rejected_count,
            total_major_donor_prospect_count = total_major_donor_prospect_count,
            total_major_donor_cultivation_count = total_major_donor_cultivation_count,
            total_major_donor_solicitation_count = total_major_donor_solicitation_count,
            total_major_donor_committed_count = total_major_donor_committed_count,
            total_major_donor_rejected_count = total_major_donor_rejected_count,
            BM_CORPORATE_PROSPECT_COUNT = BM_CORPORATE_PROSPECT_COUNT,
            BM_CORPORATE_CULTIVATION_COUNT = BM_CORPORATE_CULTIVATION_COUNT,
            BM_CORPORATE_SOLICITATION_COUNT = BM_CORPORATE_SOLICITATION_COUNT,
            BM_CORPORATE_COMMITTED_COUNT = BM_CORPORATE_COMMITTED_COUNT,
            BM_CORPORATE_REJECTED_COUNT = BM_CORPORATE_REJECTED_COUNT,
            BM_MAJOR_DONOR_PROSPECT_COUNT = BM_MAJOR_DONOR_PROSPECT_COUNT,
            BM_MAJOR_DONOR_CULTIVATION_COUNT = BM_MAJOR_DONOR_CULTIVATION_COUNT,
            BM_MAJOR_DONOR_SOLICITATION_COUNT = BM_MAJOR_DONOR_SOLICITATION_COUNT,
            BM_MAJOR_DONOR_COMMITTED_COUNT = BM_MAJOR_DONOR_COMMITTED_COUNT,
            BM_MAJOR_DONOR_REJECTED_COUNT = BM_MAJOR_DONOR_REJECTED_COUNT
        ), "html"
    )
    
    # Add HTML parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(emailbody)
    attach_file_to_email(message, 'Opportunities_in_RE.xlsx')
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

try:
    connect_db()
    
    housekeeping()
    
    get_opportunity_list_from_re()
    
    subject = "Opportunity Pipeline | Raisers Edge"
    send_email()
    
except Exception as Argument:
    print("Error while sending Opportunity Dashboard")
    subject = "Error while sending Opportunity Dashboard"
    send_error_emails()
    
finally:
    # Do housekeeping
    housekeeping()
    
    # Disconnect DB
    disconnect_db()