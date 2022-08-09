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
BM_MAJOR_DONOR_PROSPECT = os.getenv("BM_MAJOR_DONOR_PROSPECT")
BM_MAJOR_DONOR_CULTIVATION = os.getenv("BM_MAJOR_DONOR_CULTIVATION")
BM_MAJOR_DONOR_SOLICITATION = os.getenv("BM_MAJOR_DONOR_SOLICITATION")
BM_MAJOR_DONOR_COMMITTED = os.getenv("BM_MAJOR_DONOR_COMMITTED")

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
    global url, params, total_corporate_prospect_amount_in_inr_crores, total_corporate_cultivation_amount_in_inr_crores, total_corporate_solicitation_amount_in_inr_crores, total_corporate_committed_amount_in_inr_crores, total_major_donor_prospect_amount_in_inr_crores, total_major_donor_cultivation_amount_in_inr_crores, total_major_donor_solicitation_amount_in_inr_crores, total_major_donor_committed_amount_in_inr_crores
    
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
    # money = workbook.add_format({'num_format': '₹##,###'})
    
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
    money.set_num_format('_(₹* #,##0.00_);_(₹* (#,##0.00);_(₹* "-"??_);_(@_)')
    
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
    
            corporate_solicitation_amount = []
            corporate_cultivation_amount = []
            corporate_committed_amount = []
            major_donor_pipeline_amount = []
            major_donor_solicitation_amount = []
            major_donor_cultivation_amount = []
            major_donor_committed_amount = []

            for results in json_content['value']:
                
                try:
                    if results['purpose'] == "Corporate":
                        # Working with Corporate
                        print("Working with Corporate")
                        
                        # Getting Pipeline amount
                        print("Getting Pipeline amount")
                        try:
                            if results['status'] == "Pipeline":
                                try:
                                    pipeline_amount = results['ask_amount']['value']
                                except:
                                    pipeline_amount = "0"
                                    
                                corporate_pipeline_amount.append(int(pipeline_amount))
                        except:
                            pass
                        
                        # Getting Cultivation amount
                        print("Getting Cultivation amount")
                        try:
                            if results['status'] == "Cultivation":
                                try:
                                    cultivation_amount = results['ask_amount']['value']
                                except:
                                    cultivation_amount = "0"
                                    
                                corporate_cultivation_amount.append(int(cultivation_amount))
                        except:
                            pass
                        
                        # Getting Solicitation amount
                        print("Getting Solicitation amount")
                        try:
                            if results['status'] == "Solicitation":
                                try:
                                    solicitation_amount = results['ask_amount']['value']
                                except:
                                    solicitation_amount = "0"
                                    
                                corporate_solicitation_amount.append(int(solicitation_amount))
                        except:
                            pass
                        
                        # Getting Committed amount
                        print("Getting Committed amount")
                        try:
                            if results['status'] == "Committed":
                                try:
                                    committed_amount = results['expected_amount']['value']
                                except:
                                    committed_amount = "0"
                                    
                                corporate_committed_amount.append(int(committed_amount))
                        except:
                            pass
                        
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
                        
                        # Getting Pipeline amount
                        print("Getting Pipeline amount")
                        try:
                            if results['status'] == "Pipeline":
                                try:
                                    pipeline_amount = results['ask_amount']['value']
                                except:
                                    pipeline_amount = "0"
                                    
                                major_donor_pipeline_amount.append(int(pipeline_amount))
                        except:
                            pass
                        
                        # Getting Cultivation amount
                        print("Getting Cultivation amount")
                        try:
                            if results['status'] == "Cultivation":
                                try:
                                    cultivation_amount = results['ask_amount']['value']
                                except:
                                    cultivation_amount = "0"
                                    
                                major_donor_cultivation_amount.append(int(cultivation_amount))
                        except:
                            pass
                        
                        # Getting Solicitation amount
                        print("Getting Solicitation amount")
                        try:
                            if results['status'] == "Solicitation":
                                try:
                                    solicitation_amount = results['ask_amount']['value']
                                except:
                                    solicitation_amount = "0"
                                    
                                major_donor_solicitation_amount.append(int(solicitation_amount))
                        except:
                            pass
                        
                        # Getting Committed amount
                        print("Getting Committed amount")
                        try:
                            if results['status'] == "Committed":
                                try:
                                    committed_amount = results['ask_amount']['value']
                                except:
                                    committed_amount = "0"
                                    
                                major_donor_committed_amount.append(int(committed_amount))
                        except:
                            pass
                        
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
                        
    
    total_corporate_cultivation_amount = sum(corporate_cultivation_amount)/10000000
    total_corporate_cultivation_amount_in_inr = locale.currency(total_corporate_cultivation_amount, grouping=True)
    total_corporate_cultivation_amount_in_inr_crores = f"{total_corporate_cultivation_amount_in_inr} Cr."
    print(f"Total Corporate Cultivation Amount = {total_corporate_cultivation_amount}")
    print(f"Total Corporate Cultivation Amount in INR = {total_corporate_cultivation_amount_in_inr}")
    print(total_corporate_cultivation_amount_in_inr_crores)
    
    total_corporate_solicitation_amount = sum(corporate_solicitation_amount)/10000000
    total_corporate_solicitation_amount_in_inr = locale.currency(total_corporate_solicitation_amount, grouping=True)
    total_corporate_solicitation_amount_in_inr_crores = f"{total_corporate_solicitation_amount_in_inr} Cr."
    print(f"Total Corporate Solicitation Amount = {total_corporate_solicitation_amount}")
    print(f"Total Corporate Solicitation Amount in INR = {total_corporate_solicitation_amount_in_inr}")
    print(total_corporate_solicitation_amount_in_inr_crores)
    
    total_corporate_committed_amount = sum(corporate_committed_amount)/10000000
    total_corporate_committed_amount_in_inr = locale.currency(total_corporate_committed_amount, grouping=True)
    total_corporate_committed_amount_in_inr_crores = f"{total_corporate_committed_amount_in_inr} Cr."
    print(f"Total Corporate Committed Amount = {total_corporate_committed_amount}")
    print(f"Total Corporate Committed Amount in INR = {total_corporate_committed_amount_in_inr}")
    print(total_corporate_committed_amount_in_inr_crores)
    
    total_major_donor_pipeline_amount = sum(major_donor_pipeline_amount)/10000000
    total_major_donor_pipeline_amount_in_inr = locale.currency(total_major_donor_pipeline_amount, grouping=True)
    total_major_donor_pipeline_amount_in_inr_crores = f"{total_major_donor_pipeline_amount_in_inr} Cr."
    print(f"Total Major Donor Pipeline Amount = {total_major_donor_pipeline_amount}")
    print(f"Total Major Donor Pipeline Amount in INR = {total_major_donor_pipeline_amount_in_inr}")
    print(total_major_donor_pipeline_amount_in_inr_crores)
    
    total_major_donor_cultivation_amount = sum(major_donor_cultivation_amount)/10000000
    total_major_donor_cultivation_amount_in_inr = locale.currency(total_major_donor_cultivation_amount, grouping=True)
    total_major_donor_cultivation_amount_in_inr_crores = f"{total_major_donor_cultivation_amount_in_inr} Cr."
    print(f"Total Major Donor Cultivation Amount = {total_major_donor_cultivation_amount}")
    print(f"Total Major Donor Cultivation Amount in INR = {total_major_donor_cultivation_amount_in_inr}")
    print(total_major_donor_cultivation_amount_in_inr_crores)
    
    total_major_donor_solicitation_amount = sum(major_donor_solicitation_amount)/10000000
    total_major_donor_solicitation_amount_in_inr = locale.currency(total_major_donor_solicitation_amount, grouping=True)
    total_major_donor_solicitation_amount_in_inr_crores = f"{total_major_donor_solicitation_amount_in_inr} Cr."
    print(f"Total Major Donor Solicitation Amount = {total_major_donor_solicitation_amount}")
    print(f"Total Major Donor Solicitation Amount in INR = {total_major_donor_solicitation_amount_in_inr}")
    print(total_major_donor_solicitation_amount_in_inr_crores)
    
    total_major_donor_committed_amount = sum(major_donor_committed_amount)/10000000
    total_major_donor_committed_amount_in_inr = locale.currency(total_major_donor_committed_amount, grouping=True)
    total_major_donor_committed_amount_in_inr_crores = f"{total_major_donor_committed_amount_in_inr} Cr."
    print(f"Total Major Donor Committed Amount = {total_major_donor_committed_amount}")
    print(f"Total Major Donor Committed Amount in INR = {total_major_donor_committed_amount_in_inr}")
    print(total_major_donor_committed_amount_in_inr_crores)

    # Set auto-filters
    corporate_worksheet.autofilter(0, 0, corporate_worksheet_row, corporate_worksheet_col)
    major_donor_worksheet.autofilter(0, 0, major_donor_worksheet_row, major_donor_worksheet_col)
    
    # Close the excel file
    workbook.close()
try:
    housekeeping()
    
    get_opportunity_list_from_re()
    
except Exception as Argument:
    print("Error while sending Opportunity Dashboard")
    subject = "Error while sending Opportunity Dashboard"
    send_error_emails()
    
finally:
    # Do housekeeping
    housekeeping()
    
    # Close writing to Process.log
    sys.stdout.close()
    
    exit()