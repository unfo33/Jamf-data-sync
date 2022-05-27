#!/Library/ManagedFrameworks/Python/Python3.framework/Versions/Current/bin/python3
import requests
import json
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']
from local_credentials import jamf_user, jamf_password, jamf_hostname, snipe_token

def get_uapi_token():
    jamf_test_url = jamf_hostname + "/api/v1/auth/token"
    headers = {'Accept': 'application/json', }
    response = requests.post(url=jamf_test_url, headers=headers, auth=(jamf_user, jamf_password))
    response_json = response.json()
    return response_json['token']

def invalidate_uapi_token(uapi_token):
    jamf_test_url = jamf_hostname + "/api/v1/auth/invalidate-token"
    headers = {'Accept': '*/*', 'Authorization': 'Bearer ' + uapi_token}
    response = requests.post(url=jamf_test_url, headers=headers)
    if response.status_code == 204:
        print('Token invalidated!')
    else:
        print('Error invalidating token.')

def jamf_Computers(uapi_token):
    # get comoputers
    url = jamf_hostname + "/JSSResource/computers/subset/basic"
    headers = {'Accept': 'application/json', 'Authorization': 'Bearer ' + uapi_token}
    response = requests.get(url, headers=headers)
    data = json.loads(response.text)
    #print(response.text)
    return data

def snipe_GetInfo(serial):
    url = f"https://snipe.venturewell.org/api/v1/hardware/byserial/{serial}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {snipe_token}"
    }
    response = requests.get(url, headers=headers)
    data = json.loads(response.text)
    return data


def solve(s):
    # checks for valid email address
   pat = "^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$"
   if re.match(pat,s):
      return True
   return False
    
def google_Info(email):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('admin', 'directory_v1', credentials=creds)

    # Call the Admin SDK Directory API
    try:
        result = service.users().get(userKey=email).execute()
    except:
        return None

    if not result:
        return('No users matching.')
    else:
        email = result["primaryEmail"]
        #print(json.dumps(result))
        return result

def jamf_Department(uapi_token, name):
    # Checking departments doesn't use xml so escaping & is uncessary
    headers = {'Accept': "application/json", 'Authorization': 'Bearer ' + uapi_token}
    url = f"https://venturewell.jamfcloud.com/JSSResource/departments/name/{name}"
    response = requests.request("GET", url, headers=headers)
    print(f"Get Policy exit code = {response.status_code}")
    if response.status_code == 200:
        dict = json.loads(response.text)
        print ("Department exists already")
        return dict
    else:
        print ("Creating department")
        headers = {'Accept': 'application/xml', 'Content-Type': 'application/xml', 'Authorization': 'Bearer ' + uapi_token}
        url = f"https://venturewell.jamfcloud.com/JSSResource/departments/id/0"
        # escapes xml characters &
        name = xml_Characters(name)
        body = f"""
        <department>
            <name>{name}</name>
        </department>"""
        response = requests.post(url, headers=headers, data=body)
        print(response.text)
        return None

def xml_Characters(department, title=None):
    if "&" in department:
        department = department.replace("&", "&amp;")
    if "&" in title:
        title = department.replace("&", "&amp;")
    return department, title

def jamf_Update(snipe_data, google_data, uapi_token, id):
    # sets data to empty in case we don't get anything from our sources
    department, title, manager, name, asset = "No Data", "No Data", "No Data", "No Data", "No Data"
    purchase, warranty = "0000-00-00", "0000-00-00"

    email = snipe_data["rows"][0]["assigned_to"]["username"]
    # if its a spare skip google cause we know it won't be there
    if email.startswith("spare"):
        email = "spare"
        name = "spare"
    else:
        # lots of checks to prevent errors if empty
        if google_data:
            print(google_data)
            if "organizations" in google_data:
                if "department" in google_data["organizations"][0]:
                    department = google_data["organizations"][0]["department"]
                    print(department)
                if "title" in google_data["organizations"][0]:
                    title = google_data["organizations"][0]["title"]
            if "relations" in google_data:
                if "value" in google_data["relations"][0]:
                    manager = google_data["relations"][0]["value"]
            if "name" in google_data:
                if "fullName" in google_data["name"]:
                    name = google_data["name"]["fullName"]
    if snipe_data:
        if "rows" in snipe_data:
            if "asset_tag" in snipe_data["rows"][0]:
                asset = snipe_data["rows"][0]["asset_tag"]
            if "purchase_date" in snipe_data["rows"][0]:
                if not snipe_data["rows"][0]["purchase_date"] == None:
                    if "date" in snipe_data["rows"][0]["purchase_date"]:
                        if not snipe_data["rows"][0]["purchase_date"]["date"] == None:
                            purchase = snipe_data["rows"][0]["purchase_date"]["date"]
                            print(purchase)
            if "warranty_expires" in snipe_data["rows"][0]:
                if not snipe_data["rows"][0]["warranty_expires"] == None:
                    if "date" in snipe_data["rows"][0]["warranty_expires"]:
                        warranty = snipe_data["rows"][0]["purchase_date"]["date"]
                        print (warranty)

    # create department if it doesn't exist yet
    jamf_Department(uapi_token, department)
    # fix xml formatting for below xml block
    department, title = xml_Characters(department, title)
    print(asset, email, name, title, department, purchase, warranty, manager)
    body = f"""
        <computer>
            <general>
                <asset_tag>{asset}</asset_tag>
            </general>
            <location>
                <username>{email}</username>
                <realname>{name}</realname>
                <real_name>{name}</real_name>
                <email_address>{email}</email_address>
                <position>{title}</position>
                <department>{department}</department>
            </location>
            <purchasing>
                <po_date>{purchase}</po_date>
                <warranty_expires>{warranty}</warranty_expires>
            </purchasing>
            <extension_attributes>
                <extension_attribute>
                    <id>8</id>
                    <name>Manager</name>
                    <type>String</type>
                    <multi_value>false</multi_value>
                    <value>{manager}</value>
                </extension_attribute>
            </extension_attributes>
        </computer>"""
    url = jamf_hostname + f"/JSSResource/computers/id/{id}"
    headers = {'Accept': 'application/xml', 'Content-Type': 'application/xml', 'Authorization': 'Bearer ' + uapi_token}
    print("attempting to update Computer Object")
    response = requests.put(url, headers=headers, data=body)
    print(response.text)

def main():
    # fetch Jamf Pro api token
    uapi_token = get_uapi_token()
    # Get Computers from Jamf
    jamf_computers = jamf_Computers(uapi_token)
    for computer in jamf_computers["computers"]:
        computer_ID = computer["id"]
        serial = computer["serial_number"]
        print (f"*************Beginning computer with Serial: {serial}****************")
        print("Getting snipe data...")
        snipe_data = snipe_GetInfo(serial)
        # if we can't get anything from snipe we don't have any data so skip
        if not snipe_data:
            break
        email = snipe_data["rows"][0]["assigned_to"]["username"]
        print ("Getting Google data...")
        google_data = google_Info(email)
        print ("Updating Jamf...")
        jamf_Update(snipe_data, google_data, uapi_token, computer_ID)
    
    # invalidate token
    print('invalidating token...')
    invalidate_uapi_token(uapi_token)


if __name__ == '__main__':
    main()