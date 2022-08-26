# Opportunities-Dashboard-for-Raisers-Edge

### Pre-requisites
- Install below packages

```bash

sudo apt install python3-pip
sudo apt install git
pip3 install python-dotenv
pip3 install psycopg2
pip3 install xlsxwriter
pip3 install pandas 
pip3 install pretty_html_table

```
- If you encounter error on installing **pyscopg2**, then try:
```bash

pip3 install psycopg2-binary

```

- Install **PostgreSQL** using the steps mentioned [here](https://www.postgresql.org/download/linux/ubuntu/).
```bash

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt -y install postgresql

```

- Create required **Databases**
```sql

CREATE DATABASE "opportunities-in-re"

CREATE TABLE opportunity_list
(
    opportunity_id character varying,
    ask_amount character varying,
    constituent_id character varying,
    date_added character varying,
    date_modified character varying,
    expected_amount character varying,
    funded_amount character varying,
    opportunity_name character varying,
    purpose character varying,
    status character varying,
    date date
);

CREATE TABLE constituent_list
(
    constituent_id character varying,
    name character varying
);

```

- Create a **.env** file with below parameters. ***`Replace # ... with appropriate values`***

```bash

AUTH_CODE= # Raiser's Edge NXT Auth Code (encode Client 
REDIRECT_URL= # Redirect URL of application in Raiser's Edge NXT
CLIENT_ID= # Client ID of application in Raiser's Edge NXT
RE_API_KEY= # Raiser's Edge NXT Developer API Key
MAIL_USERN= # Email Username
MAIL_PASSWORD= # Email password
IMAP_URL= # IMAP web address
IMAP_PORT= # IMAP Port
SMTP_URL= # SMTP web address
SMTP_PORT= # SMTP Port
SEND_TO='email_1, email_2' # Email ID of users who needs to receive the report
CC_TO='email_3, email_4' # Email ID of users who will be CC'd for the report
ERROR_EMAILS_TO= # Email ID of user who needs to receive error emails (if any)
DB_IP= # IP of SQL Database
DB_NAME= # Name of SQL Database
DB_USERNAME= # Login for SQL Database
DB_PASSWORD= # Password for SQL Database
LAST_BOARD_MEETING_DATE= # Date when the last Board meeting occurred. Format date as - Apr 1, 2022 
BM_CORPORATE_PROSPECT= # Prospect amount for Corporates as shown to the Board. Format as ₹100 Cr.
BM_CORPORATE_CULTIVATION= # Cultivated amount for Corporates as shown to the Board. Format as ₹100 Cr.
BM_CORPORATE_SOLICITATION= # Solicited amount for Corporates as shown to the Board. Format as ₹100 Cr.
BM_CORPORATE_COMMITTED= # Committed amount for Corporates as shown to the Board. Format as ₹100 Cr.
BM_CORPORATE_REJECTED= # Rejected amount for Corporates as shown to the Board. Format as ₹100 Cr.
BM_MAJOR_DONOR_PROSPECT= # Prospect amount for Major Donor as shown to the Board. Format as ₹100 Cr.
BM_MAJOR_DONOR_CULTIVATION= # Cultivated amount for Major Donor as shown to the Board. Format as ₹100 Cr.
BM_MAJOR_DONOR_SOLICITATION= # Solicited amount for Major Donor as shown to the Board. Format as ₹100 Cr.
BM_MAJOR_DONOR_COMMITTED= # Committed amount for Major Donor as shown to the Board. Format as ₹100 Cr.
BM_MAJOR_DONOR_REJECTED= # Rejected amount for Major Donor as shown to the Board. Format as ₹100 Cr.
BM_CORPORATE_PROSPECT_COUNT= # Prospect count for Corporates as shown to the Board.
BM_CORPORATE_CULTIVATION_COUNT= # Cultivated count for Corporates as shown to the Board.
BM_CORPORATE_SOLICITATION_COUNT= # Solicited count for Corporates as shown to the Board.
BM_CORPORATE_COMMITTED_COUNT= # Committed count for Corporates as shown to the Board.
BM_CORPORATE_REJECTED_COUNT= # Rejected count for Corporates as shown to the Board.
BM_MAJOR_DONOR_PROSPECT_COUNT= # Prospect count for Major Donor as shown to the Board.
BM_MAJOR_DONOR_CULTIVATION_COUNT= # Cultivated count for Major Donor as shown to the Board.
BM_MAJOR_DONOR_SOLICITATION_COUNT= # Solicted count for Major Donor as shown to the Board.
BM_MAJOR_DONOR_COMMITTED_COUNT= # Committed count for Major Donor as shown to the Board.
BM_MAJOR_DONOR_REJECTED_COUNT= # Rejected count for Major Donor as shown to the Board.

```

### Installation
Clone the repository
```bash

git clone https://github.com/khamsakamal48/Opportunities-Dashboard-for-Raisers-Edge.git

```

Run below command in Terminal
```bash

cd Opportunities-Dashboard-for-Raisers-Edge
python3 'Request Access Token.py'

```
- Copy and paste the link in a browser to get the **TOKEN**
- Copy the **TOKEN** in the terminal and press ENTER

Run below command in Terminal
```bash

python3 'Refresh Access Token.py'

```

Set a CRON job to refresh token and start the program
```bash

*/42 * * * * cd Opportunities-Dashboard-for-Raisers-Edge/ && python3 Refresh\ Access\ Token.py > /dev/null 2>&1
@weekly cd Opportunities-Dashboard-for-Raisers-Edge/ && python3 Download\ Opportunities\ from\ RE.py > /dev/null 2>&1
0 9 * * 1 cd Opportunities-Dashboard-for-Raisers-Edge/ && python3 Send\ Dashboard\ Email.py > /dev/null 2>&1

```