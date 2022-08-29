#!/usr/bin/env python3

import requests, os, json, glob, csv, psycopg2, sys, smtplib, ssl, imaplib, time, datetime, logging, locale, xlsxwriter, pretty_html_table, quickchart
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
from quickchart import QuickChart, QuickChartFunction

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
    global previous_quarter_workbook, current_quarter_workbook, corporate_workbook, major_donor_workbook
    
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    print("Creating Excel file for Previous Quarter")
    previous_quarter_workbook = pd.ExcelWriter('Previous_Quarter.xlsx', engine='xlsxwriter', engine_kwargs={'options':{'strings_to_urls': False}})
    
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    print("Creating Excel file for Current Quarter")
    current_quarter_workbook = pd.ExcelWriter('Current_Quarter.xlsx', engine='xlsxwriter', engine_kwargs={'options':{'strings_to_urls': False}})
    
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    print("Creating Excel file for Corporate")
    corporate_workbook = pd.ExcelWriter('Corporate.xlsx', engine='xlsxwriter', engine_kwargs={'options':{'strings_to_urls': False}})
    
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    print("Creating Excel file for Major Donor")
    major_donor_workbook = pd.ExcelWriter('Major Donor.xlsx', engine='xlsxwriter', engine_kwargs={'options':{'strings_to_urls': False}})
    
def save_excel_file():
    print("Saving Excel file for Previous Quarter")
    previous_quarter_workbook.save()
    
    print("Saving Excel file for Current Quarter")
    current_quarter_workbook.save()
    
    print("Saving Excel file for Corporate")
    corporate_workbook.save()
    
    print("Saving Excel file for Major Donor")
    major_donor_workbook.save()

def write_to_excel(dataframe, workbook, worksheet, formatting):
    dataframe.to_excel(workbook, sheet_name=f'{worksheet}', index=False)
    
    # Begin formatting the excel
    print("Beginning to format the excel")
    workbook_formatted = workbook.book
    worksheet_formatted = workbook.sheets[f'{worksheet}']
    
    last_row_count = len(dataframe.index)
    last_column_count = (dataframe.shape)[1] - 1
    
    if formatting == "required":
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

def create_empty_dataframe():
    global empty_dataframe
    
    data = [['', '', '', '', '']]
    empty_dataframe = pd.DataFrame(data, columns = ['Name', 'Opportunity Name', 'Ask Amount', 'Expected Amount', 'Funded Amount'])
    
def add_formula_to_columns(dataframe):
    global dataframe_excel
    
    # Checking if dataframe is empty
    if dataframe.empty:
        print("Dataframe is empty")
        create_empty_dataframe()
        
        dataframe_excel = empty_dataframe
    
    else:
        # Adding formula and re-arranging columns
        dataframe_copy = dataframe.copy()
        dataframe_copy['Opportunity Name'] = dataframe_copy.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/opportunities/",{row.Opportunity_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Opportunity_Name}")', axis=1)
        dataframe_copy_with_constituent_name = pd.merge(
                                                    dataframe_copy,
                                                    constituent_dataframe,
                                                    on = 'Constituent_ID',
                                                    how = 'inner'
                                                )
        dataframe_copy_with_constituent_name['Name'] = dataframe_copy_with_constituent_name.apply(lambda row: f'=HYPERLINK(CONCATENATE("https://host.nxt.blackbaud.com/constituent/records/",{row.Constituent_ID},"?svcid=renxt&envid=p-dzY8gGigKUidokeljxaQiA"),"{row.Constituent_Name}")', axis=1)
        dataframe_excel = dataframe_copy_with_constituent_name.filter(['Name', 'Opportunity Name', 'Ask Amount', 'Expected Amount', 'Funded Amount'])

def get_quarterwise_data(dataframe, quarter, type, stage, workbook): # dataframe to query on, current/previous quarter, Corporate/Major Donor, excel workbook
    global quarter_dataframe, quarter_dataframe_total
    
    print(f"Working on {type} {stage}")
    
    quarter_dataframe = dataframe.query(f'Type == "{type}" and Status == "{stage}"').filter(['Constituent_ID', 'Opportunity_ID', 'Opportunity_Name', 'Ask Amount', 'Expected Amount', 'Funded Amount']).drop_duplicates()
    
    print("{quarter} quarter {type} {stage} dataframe")
    pprint(quarter_dataframe)
    
    # Adding formula and re-arranging columns
    add_formula_to_columns(quarter_dataframe)
    
    # Writing to excel
    write_to_excel(dataframe_excel, workbook, f"{stage} - {quarter} Quarter", "required")
    
    quarter_dataframe_total = locale.currency(round(quarter_dataframe['Ask Amount'].sum()/10000000), grouping=True).replace(".00", "") + " Cr."
    print(f"{quarter} Quarter {type} {stage} Total: {quarter_dataframe_total}")

def get_stagewise_data(opportunity_id, dataframe, quarter, type, stage, classification, workbook): # opportunity IDs to query on, current/previous quarter, Corporate/Major Donor, Newly added/Rejected, excel workbook
    global new_dataframe, new_dataframe_count, new_dataframe_total
    
    print(f"Working to get {classification} {stage} in {type} for {quarter} quarter")
    
    new_dataframe = dataframe[dataframe['Opportunity_ID'].isin(opportunity_id)].drop_duplicates()
    
    # Adding formula and re-arranging columns
    add_formula_to_columns(new_dataframe)
    
    # Writing to excel
    write_to_excel(dataframe_excel, workbook, f"{stage} - {classification}", "required")
    
    # Get count
    new_dataframe_count = len(new_dataframe.index)
    print(f"Count of {classification} {type} {stage}: {new_dataframe_count}")
    
    # Get Amount
    new_dataframe_total = locale.currency(round(new_dataframe['Ask Amount'].sum()/10000000), grouping=True).replace(".00", "") + " Cr."
    print(f"Amount of {classification} {type} {stage}: {new_dataframe_total}")

def get_prospect(type):
    global html_output_prospect_summary_table
    
    if type == "Corporate":
        workbook = corporate_workbook
        
    elif type == "Major Donor":
        workbook = major_donor_workbook
    
    ## Previous Quarter
    get_quarterwise_data(previous_quarter_dataframe, "Previous", f"{type}", "Prospect", workbook)
    previous_quarter_prospect_dataframe = quarter_dataframe
    previous_quarter_prospect_total = quarter_dataframe_total
    
    ## Current Quarter
    get_quarterwise_data(current_quarter_dataframe, "Current", f"{type}", "Prospect", workbook)
    current_quarter_prospect_dataframe = quarter_dataframe
    current_quarter_prospect_total = quarter_dataframe_total
    ### Count of carried forwarded corporate prospects
    current_quarter_prospect_count = len(current_quarter_prospect_dataframe.index)
    
    ## Working to get newly added prospects
    missing_opportunity_id = list(set(current_quarter_prospect_dataframe['Opportunity_ID']) - set(previous_quarter_prospect_dataframe['Opportunity_ID']) - set(previous_quarter_dataframe['Opportunity_ID']))
    get_stagewise_data(missing_opportunity_id, current_quarter_prospect_dataframe, "Current", f"{type}", "Prospect", "Newly added", workbook)
    newly_added_prospect_count = new_dataframe
    newly_added_prospect_count = new_dataframe_count
    newly_added_prospect_total = new_dataframe_total
    
    ## Working to get rejected prospects
    current_quarter_rejected_dataframe = current_quarter_dataframe.query(f'Type == "{type}" and Status == "Rejected"').filter(['Constituent_ID', 'Opportunity_ID', 'Opportunity_Name', 'Ask Amount', 'Expected Amount', 'Funded Amount']).drop_duplicates()
    rejected_opportunity_id = list(current_quarter_rejected_dataframe['Opportunity_ID'])
    get_stagewise_data(rejected_opportunity_id, previous_quarter_prospect_dataframe, "Current", f"{type}", "Rejected", "Prospect", workbook)
    rejected_prospect_dataframe = new_dataframe
    rejected_prospect_count = new_dataframe_count
    rejected_prospect_total = new_dataframe_total
    
    ## Working to get moved prospects
    moved_prospect_opportunity_id = list(set(previous_quarter_prospect_dataframe) - set(current_quarter_prospect_dataframe) - set(current_quarter_rejected_dataframe))
    get_stagewise_data(moved_prospect_opportunity_id, previous_quarter_prospect_dataframe, "Current", f"{type}", "Prospect", "Moved", workbook)
    moved_prospect_dataframe = new_dataframe        
    moved_prospect_dataframe_count = new_dataframe_count
    moved_prospect_dataframe_total = new_dataframe_total
    
    # Prepare HTML for Corporate Prospect Summary
    prepare_summary_table(previous_quarter_prospect_total, current_quarter_prospect_total)
    html_output_prospect_summary_table = html_output
    print(html_output_prospect_summary_table)
    
    prepare_detailed_table(newly_added_prospect_total, newly_added_prospect_count, moved_prospect_dataframe_total, moved_prospect_dataframe_count,
                           rejected_prospect_total, rejected_prospect_count, current_quarter_prospect_total, current_quarter_prospect_count, "", "", "Prospect")
    
    html_output_prospect_detailed_table = html_output.replace("Newly added", "<b>Newly added</b>").replace("Moved to the next stage", "<b>Moved to the next stage</b>").replace("Rejected", "<b>Rejected</b>").replace("Carried Forward", "<b>Carried Forward</b>").replace("Moved to the previous stage", "<b>Moved to the previous stage</b>")
    print(html_output_prospect_detailed_table)
    
def prepare_detailed_table(newly_added, newly_added_count, moved, moved_count, rejected, rejected_count, carried_forward, carried_forward_count, moved_back, moved_back_count, stage):
    
    if stage == "Prospect":
        table = {
            'Progress in this quarter': [
                'Newly added',
                'Moved to the next stage',
                'Rejected',
                'Carried Forward'
            ],
            'Amount': [
                newly_added,
                moved,
                rejected,
                carried_forward
            ],
            'Count': [
                newly_added_count,
                moved_count,
                rejected_count,
                carried_forward_count
            ]
        }
        
    prepare_html_table(table, "center")
    
    table_chart = {
        
    }

def prepare_chart(data):
    qc = QuickChart()
    qc.width = 900
    qc.height = 300
    qc.device_pixel_ratio = 2.0
    qc.config = {
        'type': 'bar',
        'data': data,
        'options': {
            'indexAxis': 'y',
            'plugins': {
                'position': 'right',
            },
            'title': {
                'display': 'true',
                'text': 'Chart.js Bar Chart - Stacked'
            }
        },
        'responsive': 'true',
        'scales': {
            'x': {
                'stacked': 'true'
            },
            'y': {
                'stacked': 'true'
            }
        }
    }

def prepare_html_table(dataframe, text_align):
    global html_output
    
    data = pd.DataFrame(dataframe)
    html_output = (build_table(data, 'blue_dark', font_family='Open Sans, Helvetica, Arial, sans-serif', even_color='black', padding='10px', width='900px', font_size='16px', text_align=text_align)).replace("background-color: #D9E1F2;font-family: Open Sans", "background-color: #D9E1F2; color: black;font-family: Open Sans")
        
def prepare_summary_table(previous_quarter, current_quarter):
    table = {
            'Total as on previous quarter end': [
                previous_quarter
            ],
            'Total as on this quarter end': [
                current_quarter
            ]
        }
    
    prepare_html_table(table, "center")

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
        
    # Writing to excel
    write_to_excel(current_quarter_dataframe, current_quarter_workbook, "Sheet1", "not_required")
    
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
        
    # Writing to excel
    write_to_excel(previous_quarter_dataframe, previous_quarter_workbook, "Sheet1", "not_required")
    
    # Work on Corporate Prospect
    get_prospect("Corporate")
    
    # Work on Major Donor Prospect
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