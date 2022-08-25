#!/usr/bin/env python3

import requests, os, json, glob, csv, psycopg2, sys, smtplib, ssl, imaplib, time, datetime, logging, locale, xlsxwriter
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
      
def create_excel_file():
    global corporate_workbook, major_donor_workbook
    
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    print("Creating Excel file for Corporate")
    corporate_workbook = pd.ExcelWriter('Corporate.xlsx', engine='xlsxwriter', engine_kwargs={'options':{'strings_to_urls': False}})
    
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    print("Creating Excel file for Major Donor")
    major_donor_workbook = pd.ExcelWriter('Major Donor.xlsx', engine='xlsxwriter', engine_kwargs={'options':{'strings_to_urls': False}})
    
def save_excel_file():
    print("Saving Excel file for Corporate")
    corporate_workbook.save()
    
    print("Saving Excel file for Major Donor")
    major_donor_workbook.save()

def write_to_excel(dataframe, workbook, worksheet):
    dataframe.to_excel(workbook, sheet_name=f'{worksheet}', index=False)
    
    # Begin formatting the excel
    print("Beginning to format the excel")
    workbook_formatted = workbook.book
    worksheet_formatted = workbook.sheets[f'{worksheet}']
    
    last_row_count = len(dataframe.index)
    last_column_count = (dataframe.shape)[1] - 1
    
    # Setting Header format
    header_format = workbook_formatted.add_format(
        {
            'bg_color': 'orange',
            'bold': True,
            'font_color': 'white',
            'border': 1,
            'border_color': 'white',
            'center_across': True,
            'font_size': '12'
        }
    )
    
    # Setting cell format
    money = workbook_formatted.add_format(
        {
            'num_format': '_(₹* #,##0.00_);_(₹* (#,##0.00);_(₹* "-"??_);_(@_)',
            'font_size': '12'
        }
    )
    
    hyperlink = workbook_formatted.add_format(
        {
            'font_size': '12',
            'font_color': '#0068DA',
            'underline': True
        }
    )
    
    black_border = workbook_formatted.add_format(
        {
            'border_color': 'black',
            'border': 1
        }
    )
    
    # Applying Header format
    for col , value in enumerate(dataframe.columns.values):
        worksheet_formatted.write(0, col, value, header_format)
    
    # Applying cell format
    worksheet_formatted.set_column('A:B', 70, hyperlink)
    worksheet_formatted.set_column('C:E', 30, money)
    worksheet_formatted.conditional_format(1, 0, last_row_count, last_column_count, {'type': 'no_errors', 'format': black_border})
    
    # Freeze the header
    worksheet_formatted.freeze_panes(1, 0)
    
    # Set auto filter
    worksheet_formatted.autofilter(0, 0, last_row_count, last_column_count)        

def identify_current_quarter():
    global current_quarter, current_quarter_end_date, previous_quarter_end_date, pp_previous_quarter_end_date
    
    print("Identifying current quarter")
    
    current_month = int(datetime.now().strftime("%m"))
    current_year = int(datetime.now().strftime("%Y"))
    print(f"Current month: {current_month}")
    print(f"Current year: {current_year}")
    
    # Current month between Apr and Jun
    if current_month >= 4 and current_month <= 6:
        current_quarter = "Q1"
        current_quarter_end_date = datetime.strptime(f"30-06-{current_year}", "%d-%m-%Y").date()
        previous_quarter_end_date = datetime.strptime(f"31-03-{current_year}", "%d-%m-%Y").date()
        pp_previous_quarter_end_date = datetime.strptime(f"31-12-{current_year - 1}", "%d-%m-%Y").date()
    
    # Current month between Jul and Sep
    elif current_month >= 7 and current_month <= 9:
        current_quarter = "Q2"
        current_quarter_end_date = datetime.strptime(f"30-09-{current_year}", "%d-%m-%Y").date()
        previous_quarter_end_date = datetime.strptime(f"30-06-{current_year}", "%d-%m-%Y").date()
        pp_previous_quarter_end_date = datetime.strptime(f"31-03-{current_year}", "%d-%m-%Y").date()
    
    # Current month between Oct and Dec    
    elif current_month >= 10 and current_month <= 12:
        current_quarter = "Q3"
        current_quarter_end_date = datetime.strptime(f"31-12-{current_year}", "%d-%m-%Y").date()
        previous_quarter_end_date = datetime.strptime(f"30-09-{current_year}", "%d-%m-%Y").date()
        pp_previous_quarter_end_date = datetime.strptime(f"30-06-{current_year}", "%d-%m-%Y").date()
    
    # Current month between Jan and Mar    
    elif current_month >= 1 and current_month <= 3:
        current_quarter = "Q4"
        current_quarter_end_date = datetime.strptime(f"31-03-{current_year}", "%d-%m-%Y").date()
        previous_quarter_end_date = datetime.strptime(f"31-12-{current_year - 1}", "%d-%m-%Y").date()
        pp_previous_quarter_end_date = datetime.strptime(f"30-09-{current_year - 1}", "%d-%m-%Y").date()
        
    print(f"Current Quarter: {current_quarter}")
    print(f"Current Quarter End date: {current_quarter_end_date}")
    print(f"Previous Quarter End date: {previous_quarter_end_date}")

def get_quarter_data():
    global result
    
    extract_sql = """
    SELECT * from opportunity_list where date = %s
    """
    cur.execute(extract_sql, [query_date])
    result = list(cur.fetchall())
    
    print(result)
    
def get_constituent_data():
    global constituent_dataframe
    
    extract_sql = """
    SELECT * from constituent_list
    """
    cur.execute(extract_sql)
    constituent_data = list(cur.fetchall())
    
    # Converting to Panda's Dataframe
    print("Converting to Panda's Dataframe")
    constituent_dataframe = pd.DataFrame(constituent_data, columns = ['Constituent_ID', 'Constituent_Name'])

def get_prospect(type):
    global current_quarter_corporate_prospect_total, current_quarter_major_donor_prospect_total, previous_quarter_corporate_prospect_total, previous_quarter_major_donor_prospect_total
    
    if type == "Corporate":
        print(f"Working on {type} Prospect")
        
        # Working on Previous Quarter
        print("Working on Previous Quarter")
        previous_quarter_corporate_prospect_dataframe = previous_quarter_dataframe.query(f'Type == "{type}" and Status == "Prospect"').filter(['Constituent_ID', 'Opportunity_ID', 'Opportunity_Name', 'Ask Amount', 'Expected Amount', 'Funded Amount']).drop_duplicates()
        print("Previous Quarter Corporate Prospect Dataframe")
        pprint(previous_quarter_corporate_prospect_dataframe)
        
        # Adding formula and re-arranging columns
        previous_quarter_corporate_prospect_dataframe_copy = previous_quarter_corporate_prospect_dataframe.copy()
        previous_quarter_corporate_prospect_dataframe_copy['Opportunity Name'] = previous_quarter_corporate_prospect_dataframe_copy.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/opportunities/",{row.Opportunity_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Opportunity_Name}")', axis=1)
        previous_quarter_corporate_prospect_dataframe_copy_with_constituent_name = pd.merge(
            previous_quarter_corporate_prospect_dataframe_copy,
            constituent_dataframe,
            on = 'Constituent_ID',
            how = 'inner'
        )
        previous_quarter_corporate_prospect_dataframe_copy_with_constituent_name['Name'] = previous_quarter_corporate_prospect_dataframe_copy_with_constituent_name.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/constituent/records/",{row.Constituent_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Constituent_Name}")', axis=1)
        pprint(previous_quarter_corporate_prospect_dataframe_copy_with_constituent_name)
        
        previous_quarter_corporate_prospect_dataframe_excel = previous_quarter_corporate_prospect_dataframe_copy_with_constituent_name.filter(['Name', 'Opportunity Name', 'Ask Amount', 'Expected Amount', 'Funded Amount'])
        
        # Writing to excel
        write_to_excel(previous_quarter_corporate_prospect_dataframe_excel, corporate_workbook, "Prospect - Previous Quarter")
        
        previous_quarter_corporate_prospect_total = locale.currency(round(previous_quarter_corporate_prospect_dataframe['Ask Amount'].sum()/10000000), grouping=True).replace(".00", "") + " Cr."
        print(f"Previous Quarter Corporate Prospect Total: {previous_quarter_corporate_prospect_total}")
        
        # Working on Current Quarter
        print("Working on Current Quarter")
        current_quarter_corporate_prospect_dataframe = current_quarter_dataframe.query(f'Type == "{type}" and Status == "Prospect"').filter(['Constituent_ID', 'Opportunity_ID', 'Opportunity_Name', 'Ask Amount', 'Expected Amount', 'Funded Amount']).drop_duplicates()
        print("Current Quarter Corporate Prospect Dataframe:")
        pprint(current_quarter_corporate_prospect_dataframe)
        
        # Adding formula and re-arranging columns
        current_quarter_corporate_prospect_dataframe_copy = current_quarter_corporate_prospect_dataframe.copy()
        current_quarter_corporate_prospect_dataframe_copy['Opportunity Name'] = current_quarter_corporate_prospect_dataframe_copy.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/opportunities/",{row.Opportunity_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Opportunity_Name}")', axis=1)
        current_quarter_corporate_prospect_dataframe_copy_with_constituent_name = pd.merge(
            current_quarter_corporate_prospect_dataframe_copy,
            constituent_dataframe,
            on = 'Constituent_ID',
            how = 'inner'
        )
        current_quarter_corporate_prospect_dataframe_copy_with_constituent_name['Name'] = current_quarter_corporate_prospect_dataframe_copy_with_constituent_name.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/constituent/records/",{row.Constituent_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Constituent_Name}")', axis=1)
        pprint(current_quarter_corporate_prospect_dataframe_copy_with_constituent_name)
        
        current_quarter_corporate_prospect_dataframe_excel = current_quarter_corporate_prospect_dataframe_copy_with_constituent_name.filter(['Name', 'Opportunity Name', 'Ask Amount', 'Expected Amount', 'Funded Amount'])
        
        # Writing to excel
        write_to_excel(current_quarter_corporate_prospect_dataframe_excel, corporate_workbook, "Prospect - Current Quarter")
        
        current_quarter_corporate_prospect_total = locale.currency(round(current_quarter_corporate_prospect_dataframe['Ask Amount'].sum()/10000000), grouping=True).replace(".00", "") + " Cr."
        print(f"Current Quarter Corporate Prospect Total: {current_quarter_corporate_prospect_total}")
        
        # Working to get newly added prospects
        print("Working to get newly added prospects")
        missing_opportunity_id_corporates = list(set(current_quarter_corporate_prospect_dataframe['Opportunity_ID']) - set(previous_quarter_corporate_prospect_dataframe['Opportunity_ID']) - set(previous_quarter_dataframe['Opportunity_ID']))
        print(f"Opportunity_IDs of Newly added prospects: {missing_opportunity_id_corporates}")
        
        newly_added_corporate_prospect_dataframe = current_quarter_corporate_prospect_dataframe[current_quarter_corporate_prospect_dataframe['Opportunity_ID'].isin(missing_opportunity_id_corporates)].drop_duplicates()
        print("Newly Added Prospect Dataframe:")
        pprint(newly_added_corporate_prospect_dataframe)
        
        # Writing to excel
        write_to_excel(newly_added_corporate_prospect_dataframe, corporate_workbook, "Prospect - Newly added")
        
        # Count of newly added corporate prospects
        newly_added_corporate_prospect_count = len(newly_added_corporate_prospect_dataframe.index)
        print(f"Count of newly added {type} prospects: {newly_added_corporate_prospect_count}")
        
        # Amount of newly added corporate prospects
        newly_added_corporate_prospect_total = locale.currency(round(newly_added_corporate_prospect_dataframe['Ask Amount'].sum()/10000000), grouping=True).replace(".00", "") + " Cr."
        print(f"Amount of newly added {type} prospects: {newly_added_corporate_prospect_total}")
        
    elif type == "Major Donor":
        print(f"Working on {type} Prospect")
        
        # Working on Previous Quarter
        print("Working on Previous Quarter")
        previous_quarter_major_donor_prospect_dataframe = previous_quarter_dataframe.query(f'Type == "{type}" and Status == "Prospect"').filter(['Constituent_ID', 'Opportunity_ID', 'Opportunity_Name', 'Ask Amount', 'Expected Amount', 'Funded Amount']).drop_duplicates()
        print("Previous Quarter Major Donor Prospect Dataframe")
        pprint(previous_quarter_major_donor_prospect_dataframe)
        
        # Adding formula and re-arranging columns
        previous_quarter_major_donor_prospect_dataframe_copy = previous_quarter_major_donor_prospect_dataframe.copy()
        previous_quarter_major_donor_prospect_dataframe_copy['Opportunity Name'] = previous_quarter_major_donor_prospect_dataframe_copy.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/opportunities/",{row.Opportunity_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Opportunity_Name}")', axis=1)
        previous_quarter_major_donor_prospect_dataframe_copy_with_constituent_name = pd.merge(
            previous_quarter_major_donor_prospect_dataframe_copy,
            constituent_dataframe,
            on = 'Constituent_ID',
            how = 'inner'
        )
        previous_quarter_major_donor_prospect_dataframe_copy_with_constituent_name['Name'] = previous_quarter_major_donor_prospect_dataframe_copy_with_constituent_name.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/constituent/records/",{row.Constituent_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Constituent_Name}")', axis=1)
        pprint(previous_quarter_major_donor_prospect_dataframe_copy_with_constituent_name)
        
        previous_quarter_major_donor_prospect_dataframe_excel = previous_quarter_major_donor_prospect_dataframe_copy_with_constituent_name.filter(['Name', 'Opportunity Name', 'Ask Amount', 'Expected Amount', 'Funded Amount'])
        
        # Writing to excel
        write_to_excel(previous_quarter_major_donor_prospect_dataframe_excel, major_donor_workbook, "Prospect - Previous Quarter")
        
        previous_quarter_major_donor_prospect_total = locale.currency(round(previous_quarter_major_donor_prospect_dataframe['Ask Amount'].sum()/10000000), grouping=True).replace(".00", "") + " Cr."
        print(f"Previous Quarter Major Donor Prospect Total: {previous_quarter_major_donor_prospect_total}")
        
        # Working on Current Quarter
        print("Working on Current Quarter")
        current_quarter_major_donor_prospect_dataframe = current_quarter_dataframe.query(f'Type == "{type}" and Status == "Prospect"').filter(['Constituent_ID', 'Opportunity_ID', 'Opportunity_Name', 'Ask Amount', 'Expected Amount', 'Funded Amount']).drop_duplicates()
        print("Current Quarter Major Donor Prospect Dataframe")
        pprint(current_quarter_major_donor_prospect_dataframe)
        
        # Adding formula and re-arranging columns
        current_quarter_major_donor_prospect_dataframe_copy = current_quarter_major_donor_prospect_dataframe.copy()
        current_quarter_major_donor_prospect_dataframe_copy['Opportunity Name'] = current_quarter_major_donor_prospect_dataframe_copy.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/opportunities/",{row.Opportunity_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Opportunity_Name}")', axis=1)
        current_quarter_major_donor_prospect_dataframe_copy_with_constituent_name = pd.merge(
            current_quarter_major_donor_prospect_dataframe_copy,
            constituent_dataframe,
            on = 'Constituent_ID',
            how = 'inner'
        )
        current_quarter_major_donor_prospect_dataframe_copy_with_constituent_name['Name'] = current_quarter_major_donor_prospect_dataframe_copy_with_constituent_name.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/constituent/records/",{row.Constituent_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Constituent_Name}")', axis=1)
        pprint(current_quarter_major_donor_prospect_dataframe_copy_with_constituent_name)
        
        current_quarter_major_donor_prospect_dataframe_excel = current_quarter_major_donor_prospect_dataframe_copy_with_constituent_name.filter(['Name', 'Opportunity Name', 'Ask Amount', 'Expected Amount', 'Funded Amount'])
        
        # Writing to excel
        write_to_excel(current_quarter_major_donor_prospect_dataframe_excel, major_donor_workbook, "Prospect - Current Quarter")
        
        current_quarter_major_donor_prospect_total = locale.currency(round(current_quarter_major_donor_prospect_dataframe['Ask Amount'].sum()/10000000), grouping=True).replace(".00", "") + " Cr."
        print(f"Current Quarter Major Donor Prospect Total: {current_quarter_major_donor_prospect_total}")
        
        # Working to get newly added prospects
        print("Working to get newly added prospects")
        missing_opportunity_id_major_donor = list(set(current_quarter_major_donor_prospect_dataframe['Opportunity_ID']) - set(previous_quarter_major_donor_prospect_dataframe['Opportunity_ID']) - set(previous_quarter_dataframe['Opportunity_ID']))
        print(f"Opportunity_IDs of Newly added prospects: {missing_opportunity_id_major_donor}")
        
        newly_added_major_donor_prospect_dataframe = current_quarter_major_donor_prospect_dataframe[current_quarter_major_donor_prospect_dataframe['Opportunity_ID'].isin(missing_opportunity_id_major_donor)].drop_duplicates()
        print("Newly Added Prospect Dataframe:")
        pprint(newly_added_major_donor_prospect_dataframe)
        
        # Writing to excel
        write_to_excel(newly_added_major_donor_prospect_dataframe, major_donor_workbook, "Prospect - Newly added")
        
        # Count of newly added major donor prospects
        newly_added_major_donor_prospect_count = len(newly_added_major_donor_prospect_dataframe.index)
        print(f"Count of newly added {type} prospects: {newly_added_major_donor_prospect_count}")
        
        # Amount of newly added major donor prospects
        newly_added_major_donor_prospect_total = locale.currency(round(newly_added_major_donor_prospect_dataframe['Ask Amount'].sum()/10000000), grouping=True).replace(".00", "") + " Cr."
        print(f"Amount of newly added {type} prospects: {newly_added_major_donor_prospect_total}")

try:
    # Connect to DB
    connect_db()
    
    # Create excel file
    create_excel_file()
    
    # Identify Current Quarter
    identify_current_quarter()
    
    # Get constituent data
    get_constituent_data()
    
    # Get data for Current quarter
    print("Getting data for Current quarter")
    new_date = current_quarter_end_date
    
    while current_quarter_end_date:
        query_date = new_date
        print(f"Querying Current Quarter's data for date: {query_date}")
        get_quarter_data()
        
        if result == []:
            # Subtracting the day by 1
            new_date = query_date - timedelta(days=1)
            
            # Ensuring that the reduced date is not from last quarter
            if new_date <= previous_quarter_end_date:
                current_quarter_data = []
                break
            
        else:
            current_quarter_data = result
            result = []
            break
        
    print("Current Quarter Data:")
    pprint(current_quarter_data)
    
    # Converting to Panda's Dataframe
    print("Converting to Panda's Dataframe")
    current_quarter_dataframe = pd.DataFrame(current_quarter_data, columns = ['Opportunity_ID', 'Ask Amount', 'Constituent_ID', 'Date Added', 'Date Modified', 'Expected Amount', 'Funded Amount', 'Opportunity_Name', 'Type', 'Status', 'Date'])
    
    # Setting the datatypes
    print("Setting the datatypes")
    current_quarter_dataframe[['Ask Amount']] = current_quarter_dataframe[['Ask Amount']].apply(pd.to_numeric)
    current_quarter_dataframe[['Expected Amount']] = current_quarter_dataframe[['Expected Amount']].apply(pd.to_numeric)
    current_quarter_dataframe[['Funded Amount']] = current_quarter_dataframe[['Funded Amount']].apply(pd.to_numeric)
    current_quarter_dataframe[['Date']] = current_quarter_dataframe[['Date']].apply(pd.to_datetime)
    
    pprint("Current Quarter Dataframe:")
    print(current_quarter_dataframe)
    
    # Get data for Previous quarter
    print("Getting data for Previous quarter")
    new_date = previous_quarter_end_date
    
    while previous_quarter_end_date:
        query_date = new_date
        print(f"Querying Previous Quarter's data for date: {query_date}")
        get_quarter_data()
        
        if result == []:
            # Subtracting the day by 1
            new_date = query_date - timedelta(days=1)
            
            # Ensuring that the reduced date is not from last quarter
            if new_date <= pp_previous_quarter_end_date:
                previous_quarter_data = []
                break
            
        else:
            previous_quarter_data = result
            result = []
            break
        
    print("Previous Quarter Data:")
    pprint(previous_quarter_data)
    
    # Converting to Panda's Dataframe
    print("Converting to Panda's Dataframe")
    previous_quarter_dataframe = pd.DataFrame(previous_quarter_data, columns = ['Opportunity_ID', 'Ask Amount', 'Constituent_ID', 'Date Added', 'Date Modified', 'Expected Amount', 'Funded Amount', 'Opportunity_Name', 'Type', 'Status', 'Date'])
    
    # Setting the datatypes
    print("Setting the datatypes")
    previous_quarter_dataframe[['Ask Amount']] = previous_quarter_dataframe[['Ask Amount']].apply(pd.to_numeric)
    previous_quarter_dataframe[['Expected Amount']] = previous_quarter_dataframe[['Expected Amount']].apply(pd.to_numeric)
    previous_quarter_dataframe[['Funded Amount']] = previous_quarter_dataframe[['Funded Amount']].apply(pd.to_numeric)
    previous_quarter_dataframe[['Date']] = previous_quarter_dataframe[['Date']].apply(pd.to_datetime)
    
    pprint("Previous Quarter Dataframe:")
    print(previous_quarter_dataframe)
    
    # Work on Corporate Prospect
    print("Working on Corporate Prospect")
    get_prospect("Corporate")
    
    # Work on Major Donor Prospect
    print("Working on Major Donor Prospect")
    get_prospect("Major Donor")

except Exception as Argument:
    subject = "Error while preparing opportunity pipeline progress from Raisers Edge"
    print(subject)
    send_error_emails()
    
finally:
    # Do housekeeping
    housekeeping()
    
    # Save excel file
    save_excel_file()
    
    # Disconnect DB
    disconnect_db()