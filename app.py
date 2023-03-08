import os
from flask import Flask, render_template, redirect, current_app, send_from_directory, request
from flask.helpers import make_response
from pathlib import Path
from config import secretKey, okapiURL, tenant, externalPass
import login
import requests
import sys
import json
from datetime import datetime
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, PasswordField, TextField
from wtforms.validators import InputRequired
from flask_wtf.csrf import CSRFProtect
from urllib.parse import unquote
from requests.adapters import HTTPAdapter, Retry

# Flask-WTF requires an encryption key - the string can be anything
app = Flask(__name__)
csrf = CSRFProtect(app)

token = login.login()
if token == 0:
  sys.exit()
error = ""
locationPath = "/locations?limit=2000&query=cql.allRecords%3D1%20sortby%20name"
headers = {'x-okapi-tenant': tenant, 'x-okapi-token': token}
#selectmultipleField will auto-fail validation and refuse to submit form
#without this
class NoValidationSelectField(SelectField):
    def pre_validate(self, form):
      pass
      """per_validation is disabled"""

r = requests.get(okapiURL + locationPath, headers=headers)
if r.status_code != 200:
  error = "Cannot Get location code data from folio: " + str(r.status_code) + r.text
  sys.exit()

temp = r.json()
locations = temp["locations"]
if len(locations) == 0:
  error = "No locations defined."

selectValues = []
for entry in locations:
  selectValues.append(([entry["id"]], entry["name"]))


Bootstrap(app)
app.config['SECRET_KEY'] = secretKey

class authenticationForm(FlaskForm):
  password = PasswordField('Enter Password: ', validators=[InputRequired()])
  submit = SubmitField('Submit')

class selectLocForm(FlaskForm):
  location = NoValidationSelectField('Location:', choices=selectValues, validators=[InputRequired()])
  submit = SubmitField('Set Location')

class locationForm(FlaskForm):
  barcode = TextField('Item Barcode', validators=[InputRequired()], render_kw={'autofocus': True})
  submit = SubmitField('Submit')

class suppressLog(FlaskForm):
  downLoadSubmit = SubmitField('Download Log')
  clearSubmit = SubmitField('Clear Log')

class suppressForm(FlaskForm):
  barcode = TextField('Item Barcode', validators=[InputRequired()], render_kw={'autofocus': True})
  submit = SubmitField('Submit')
  clear = SubmitField('Clear')

displayLink = False
@app.route('/login', methods=['GET', 'POST'])
def login():
  showBackLink = False
  formName = "Login"
  header=""
  authForm = authenticationForm()
  loggedIn = request.cookies.get('loggedIn')
  if loggedIn != None and loggedIn == "true":
    return redirect("/changeRecords/choose", code=302)
  if authForm.validate_on_submit():
    passwd = authForm.password.data
    if passwd != externalPass.strip():
      message = "Invalid Password"
      return render_template('index.html', displayLink=displayLink, form=authForm, header=header, message=message,formName=formName)
    else:
      resp = make_response(redirect("/changeRecords/choose", code=302))
      resp.set_cookie('loggedIn', 'true')
      return resp
  return render_template('index.html', displayLink=displayLink, form=authForm, header=header, message="", formName=formName, showBackLink=showBackLink)

@app.route('/choose', methods=['GET'])
def choose():
  loggedIn = request.cookies.get('loggedIn')
  if loggedIn == None or loggedIn != "true":
    return redirect("/choose/login", code=302)
  return render_template('choose.html')

@app.route('/getItemSuppress', methods=['GET', 'POST'])
def getItemSuppress():
  showBackLink = True
  formName = "Download or clear item supression log"
  loggedIn = request.cookies.get('loggedIn')
  header = ""
  msg = ""
  if loggedIn == None or loggedIn != "true":
    return redirect("/changeRecords/login", code=302)
  logForm = suppressLog()
  fileName = "itemSuppressLog.txt"
  if logForm.validate_on_submit():
    downLoad = logForm.downLoadSubmit.data
    logFile = Path(current_app.root_path + "/logs/itemSuppressLog.txt")
    if downLoad == True:
      if logFile.is_file(): 
        return send_from_directory(path=current_app.root_path, directory="logs", filename=fileName, as_attachment=True)
      else:
        msg = "Suppress log does not exist-probably no item records suppressed since it was last cleared."
    else:
      if logFile.is_file():
        os.remove(logFile)
        msg = "Log Cleared"
      else:
        msg="Logfile already cleared."
  return render_template('index.html', displayLink=displayLink, form=logForm, header=header, message=msg, formName=formName, showBackLink=showBackLink)
  

@app.route('/getSuppress', methods=['GET', 'POST'])
def getSuppress():
  showBackLink = True
  formName = "Download or clear supression log"
  loggedIn = request.cookies.get('loggedIn')
  header = ""
  msg = ""
  if loggedIn == None or loggedIn != "true":
    return redirect("/changeRecords/login", code=302)
  logForm = suppressLog()
  fileName = "instanceSuppressLog.txt"
  if logForm.validate_on_submit():
    downLoad = logForm.downLoadSubmit.data
    logFile = Path(current_app.root_path + "/logs/instanceSuppressLog.txt")
    if downLoad == True:
      if logFile.is_file(): 
        return send_from_directory(path=current_app.root_path, directory="logs", filename=fileName, as_attachment=True)
      else:
        msg = "Suppress log does not exist-probably no instance records suppressed since it was last cleared."
    else:
      if logFile.is_file():
        os.remove(logFile)
        msg = "Log Cleared"
      else:
        msg="Logfile already cleared."
  return render_template('index.html', displayLink=displayLink, form=logForm, header=header, message=msg, formName=formName, showBackLink=showBackLink)
  

@app.route('/locationselect', methods=['GET', 'POST'])
def locSelect():
  showBackLink = True
  formName = "Select Location"
  loggedIn = request.cookies.get('loggedIn')
  header = ""
  msg = ""
  if loggedIn == None or loggedIn != "true":
    return redirect("/changeRecords/login", code=302)
  locForm = selectLocForm()
  if locForm.validate_on_submit():
    location = locForm.location.data
    url = "/changeRecords/locationchange?location=" + location
    return redirect(url)
  return render_template('index.html', displayLink=displayLink, form=locForm, header=header, message=msg, formName=formName, showBackLink=showBackLink)


@app.route('/locationchange', methods=['GET', 'POST'])
def reservereport():
  showBackLink = True
  displayLink = True
  formName = "Change Item location"
  loggedIn = request.cookies.get('loggedIn')
  msg = ""
  if loggedIn == None or loggedIn != "true":
    return redirect("/changeRecords/login", code=302)
  
  if "location" not in request.args:
    return redirect("/changeRecords/locationselect")
  location = request.args.get("location")
  location = unquote(location)
  name = ""
  for entry in selectValues:
    if entry[0][0] == formatString(location):
      name = entry[1]
      break
  print("name: " + name)
  header = "Changing location of items to " + name
  locForm = locationForm()
  if locForm.validate_on_submit():
    barcode = locForm.barcode.data
    msg = changeLocation(location, barcode, token)
    locForm.barcode.data = ""
  return render_template('index.html', displayLink=displayLink, form=locForm, header=header, message=msg, formName=formName, showBackLink=showBackLink)

@app.route('/suppress', methods=['GET', 'POST'])
def suppress():
  showBackLink = True
  header = ""
  formName = "Suppress item"
  loggedIn = request.cookies.get('loggedIn')
  msg = ""
  if loggedIn == None or loggedIn != "true":
    return redirect("/changeRecords/login", code=302)
  supForm = suppressForm()
  if supForm.validate_on_submit():
    if (supForm.clear.data):
      supForm.barcode.data = ""
      return render_template('index.html', displayLink=displayLink, form=supForm, header=header, message=msg, formName=formName, showBackLink=showBackLink)
    
    barcode = supForm.barcode.data
    msg = doSuppress(barcode, token)
    supForm.barcode.data = ""
  return render_template('index.html', displayLink=displayLink, form=supForm,header=header, message=msg, formName=formName, showBackLink=showBackLink)

statCode = "ec3ff490-dfbf-4728-96f7-32e87620e832"

def allRecordsSuppressedCheck(records):
  for record in records:
    if "discoverySuppress" not in record or record["discoverySuppress"] != True:
      return False
  return True

def pullRecordById(id, path, headers, session):
  print("Attempting to pull record from  " + path + " with id " + id)
  query = okapiURL + path + "/" + id
  r = session.get(query, headers=headers)

  if (r.status_code != 200):
    print("Cannot retrieve items for holdings record " + id)
    sys.exit()

  return r.json()

def pullAllChildRecords(id, path, headers, fieldName, arrayName, session):

  limit = "100"
  offset = 0

  queryString="&query=" + fieldName + "==" + id

  fullQuery = "?limit=" + limit + "&offset=" + str(offset) + queryString

  r = session.get(okapiURL + path + fullQuery, headers=headers)
  print("Attempting to get data from endpoint: " + path)
  if r.status_code != 200:
    error = "Could not get data from endpoint, status code: " + str(r.status_code) + " Error message:" + r.text
    print(error)
    sys.exit()

  json = r.json()[arrayName]

  if len(json) < 1:
    error = "No data defined in " + path + " endpoint"
    print(error)
    sys.exit()
  
  list = json

  while json:
    offset += 100
    fullQuery = "?limit=" + limit + "&offset=" + str(offset) + queryString
    print("attempting to fetch next 100 entries from " + str(offset))
    r = session.get(okapiURL + path + fullQuery, headers=headers)
    json = r.json()[arrayName]
    if len(json) >= 1:
      list = list + json
    else:
      print("No more data to fetch")
  return list


def addStatCodeToRecord(recordId, headers, path, session):
  print("Attempting to get record from path: " + path + " with id " + recordId)
  r = session.get(okapiURL + path + "/" + recordId, headers=headers)
  if r.status_code != 200:
    print("unable to retrive record from path: " + path + " with id: " + recordId + " for editing, exiting program")
    sys.exit()
  json = r.json()
  if statCode not in json["statisticalCodeIds"]:
    print("Record with Id: " + recordId + " does not have code, attempting to add")
    if "None" in json["statisticalCodeIds"]:
      index =  json["statisticalCodeIds"].index("None")
      del json["statisticalCodeIds"][index]
    json["statisticalCodeIds"].append(statCode)
    url = okapiURL + path + "/" + recordId
    r = session.put(url, json=json, headers=headers)
    if r.status_code != 204:
      print("unable to attach statistical code to record: " + recordId + " " + str(r.status_code) + " " + str(r.text))
      sys.exit()
    else:
      print("Statistical code attached to record " + recordId)
  else:
    print("Record with Id: " + recordId + " already has stat code, skipping and continuing")

def doSuppress(barcode, token):
  session = requests.Session()
  barcode = barcode.strip()
  retries = Retry(total=5, backoff_factor=0.1)
  session.mount('https://', HTTPAdapter(max_retries=retries))
  itemsPath = "/inventory/items"
  holdingsPath = "/holdings-storage/holdings"
  instancesPath = "/inventory/instances"

  headers = {'x-okapi-tenant': tenant, 'x-okapi-token': token}

  print("Attempting to retrieve item record with barcode " + str(barcode))

  queryString = "?query=barcode==\"" + str(barcode) + "\""
  # pull the item record with the specified barcode
  r = session.get(okapiURL + itemsPath + queryString, headers=headers)

  if (r.status_code != 200):
    return "Item with barcode " + str(barcode) + " not found"
  
  print("Item retrieved")
  itemRecord = r.json()["items"][0]

  # mark the item record as suppressed and withdrawn
  itemRecord["discoverySuppress"] = True
  itemRecord["status"]["name"] = "Withdrawn"

  itemId = itemRecord["id"]

  putUrl = okapiURL + itemsPath + "/" + itemId

  r = session.put(putUrl, json=itemRecord, headers=headers)

  if (r.status_code != 204):
    return "Cannot modify item record " + itemId
  path = Path(current_app.root_path + "/logs/itemSuppressLog.txt")
  f = open(path, "a")
  now = datetime.now()
  dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
  f.write(itemRecord["id"] + "," + itemRecord["barcode"] + "," + dt_string + "\n")
  f.close()
  # now pull all item records attached to the same holdings record
  holdingsId = itemRecord["holdingsRecordId"]

  itemRecordsForHolding = pullAllChildRecords(holdingsId, itemsPath, headers, "holdingsRecordId", "items", session)
  # now pull the holdings record itself
  holdingsRecord = pullRecordById(holdingsId, holdingsPath, headers, session)

  instanceId = holdingsRecord["instanceId"]
  
  # now pull the instance record
  instanceRecord = pullRecordById(instanceId, instancesPath, headers, session)

  # if all item records are suppressed, suppress the holdings record
  if allRecordsSuppressedCheck(itemRecordsForHolding) == True:
    print("Single item record attached to holdings or all item records suppressed, suppressing holdings record.")
    
    holdingsRecord["discoverySuppress"] = True
    queryString = "/" + holdingsId
    r = requests.put(okapiURL + holdingsPath + queryString, json=holdingsRecord, headers=headers)
    
    if (r.status_code != 204):
      return "Unable to modify holdings record " + holdingsRecord["id"]

    print("holdings record " + holdingsId + " suppressed")

    # now check to see if all the holdings records are suppressed
    holdingsForInstance = pullAllChildRecords(instanceId, holdingsPath, headers, "instanceId", "holdingsRecords", session)
    if allRecordsSuppressedCheck(holdingsForInstance) == True:
      print("All holdings records attached to instance record with ID " + instanceId + " are suppressed, suppressing instance record")

      instanceRecord["discoverySuppress"] = True
      queryString = "/" + instanceId
      r = requests.put(okapiURL + instancesPath + queryString, json=instanceRecord, headers=headers)
      
      if (r.status_code != 204):
        return "Unable to modify instance record " + holdingsRecord["id"]

      try:
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        path = Path(current_app.root_path + "/logs/instanceSuppressLog.txt")
        f = open(path, "a")
        f.write(instanceRecord["id"] + "," + dt_string + "\n")
        f.close()
      except Exception as e:
        print("unable to log supression of instance record " + instanceRecord["id"] + " " + str(e))
      print("instance record " + holdingsId + " suppressed")
    
  # attach statistical codes
  # if it's the only item record, check the holdings record to see if it's the 
  # only one attached to the instance record
  print("Attaching statistical code check")
  if (len(itemRecordsForHolding) > 1):
    print("Multiple item records attached to holdings record, attempting to attach code to item record")
    addStatCodeToRecord(itemId, headers, itemsPath, session)
  else:
    print("Checking for multiple holdings records attached to instance record")
    holdingsForInstance = pullAllChildRecords(instanceId, holdingsPath, headers, "instanceId", "holdingsRecords", session)
    if (len(holdingsForInstance) > 1):
      print("Multiple holdings records found, attaching statistical code to item record")
      addStatCodeToRecord(itemId, headers, itemsPath, session)
    else:
      print("Single holdings record, attaching statisitcal code to instance record")
      addStatCodeToRecord(instanceId, headers, instancesPath, session)
  return "Item with barcode " + barcode + " successfully suppressed"

def changeLocation(location, barcode, token):
  session = requests.Session()
  barcode = barcode.strip()
  retries = Retry(total=5, backoff_factor=0.1)
  session.mount('https://', HTTPAdapter(max_retries=retries))
  disallowed_characters = "''[]"
  
  for character in disallowed_characters:
    location = location.replace(character, "")
  print("Attempting to log in to folio")

  itemsPath = "/inventory/items"
  holdingsPath = "/holdings-storage/holdings"

  headers = {'x-okapi-tenant': tenant, 'x-okapi-token': token}

  print("Attempting to retrieve item record with barcode " + str(barcode))

  queryString = "?query=barcode==\"" + str(barcode) + "\""

  r = session.get(okapiURL + itemsPath + queryString, headers=headers)

  if (r.status_code != 200):
    return "Item with barcode " + str(barcode) + " not found"
  print("Item retrieved")
  itemRecord = r.json()["items"][0]

  holdingsId = itemRecord["holdingsRecordId"]

  queryString = "?query=holdingsRecordId==\"" + holdingsId + "\""
  print("Checking for multiple items atatched to holdings record with Id " + holdingsId)
  r = session.get(okapiURL + itemsPath + queryString, headers=headers)

  if (r.status_code != 200):
    return "Cannot retrieve holdings record " + holdingsId

  if (len(r.json()["items"]) > 1):
    return "Multiple items attached to holdings record, location must be changed manually."
  
  print("Single item record attached to holdings, proceeding with location change.")
  queryString = "/" + holdingsId
  r = session.get(okapiURL + holdingsPath + queryString, headers=headers)

  if (r.status_code != 200):
    return "Cannot retrieve holdings record " + holdingsId

  holdingsRecord = r.json()

  holdingsRecord["permanentLocationId"] = location

  query = okapiURL + holdingsPath + queryString

  headers = {'x-okapi-tenant': tenant, 'x-okapi-token': token, "content-type": "application/json"}
  r = session.put(query, json=holdingsRecord, headers=headers)

  if (r.status_code != 204):
    return "Unable to edit holdings record " + holdingsId + " Status code: " + str(r.status_code)

  return "Location updated for item with barcode: " + barcode

def formatString(string):
  disallowed_characters = "''[]"
  
  for character in disallowed_characters:
    string = string.replace(character, "")
  return string
  



  


