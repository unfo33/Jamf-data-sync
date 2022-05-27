# Jamf-data-sync
Python script to pull in data from Google Workspace and Snipe IT Asset management

## Workflow
1. Pulls subset basic info on all computers from Jamf
2. Grabs a serial number and checks for that computer in Snipe, if found it grabs asset tag, warranty, purchase date, and assigned username
3. Uses assigned username to pull in additional info from Google such as: department, title, manager, and full name
4. Attempts to update the computer object with all above info in Jamf. Creates a department if it doesn't exist already. 

## Potential Issues
- departments and other info are uploaded in XML format. If unsafe XML characters such as & exist they need to be escaped. Currently & is escaped for Departments and Titles

## Requirements
- Credentials for API Access to Snipe, Jamf, and Google
- Google Workspace SDK installed
