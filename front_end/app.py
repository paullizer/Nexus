import os
import requests
from datetime import datetime
from flask import Flask, redirect, render_template, request, send_from_directory, url_for, flash, session

app = Flask(__name__)
app.config['API_BASE_URL'] = os.getenv('API_BASE_URL')
app.config['API_KEY'] = os.getenv('API_KEY')
app.secret_key = os.getenv('FLASK_KEY')
app.config['VERSION'] = '0.71'

# ===============================
# VM Management Routes
# ===============================

# Index page
@app.route('/')
def index():
    print('Request for index page received')
    return render_template('index.html')

# Favicon route
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/test-flash')
def test_flash():
    flash("This is a test message!", "success")
    return redirect(url_for('index'))

# Retrieve a list of all virtual machines
@app.route('/vms')
def view_all_vms():
    try:
        api_url = f"{app.config['API_BASE_URL']}/vms"
        headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        vms = response.json()
        return render_template('vm/view_all_vms.html', vms=vms)
    except requests.exceptions.RequestException as e:
        flash("Unable to retrieve VM data. Please try again later.", "danger")
        print(f"Error fetching VMs: {e}")
        return redirect(url_for('index'))

# Retrieve details for a specific virtual machine
@app.route('/vms/<int:vmid>')
def view_vm_details(vmid):
    try:
        api_url = f"{app.config['API_BASE_URL']}/vms/{vmid}"
        headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        vm = response.json()
        return render_template('vm/view_vm_details.html', vm=vm)
    except requests.exceptions.RequestException as e:
        flash("Unable to retrieve VM details. Please try again later.", "danger")
        print(f"Error fetching VM details: {e}")
        return redirect(url_for('view_all_vms'))

# Add a new virtual machine
@app.route('/vms/add', methods=['GET', 'POST'])
def add_vm():
    if request.method == 'POST':
        try:
            data = {
                "hostname": request.form['hostname'],
                "ipaddress": request.form['ipaddress'],
                "powerstate": request.form['powerstate'],
                "networkstatus": request.form['networkstatus'],
                "vmstatus": request.form['vmstatus'],
                "username": request.form.get('username', ''),
                "avdhost": request.form.get('avdhost', ''),
                "description": request.form.get('description', '')
            }
            api_url = f"{app.config['API_BASE_URL']}/vms/add"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            print(f"API Response: {response.status_code}, {response.text}")
            # response.raise_for_status()
            if response.status_code == 201:
                flash("VM added successfully!", "success")
                return redirect(url_for('view_all_vms'))
            else:
                print(f"Unexpected status code: {response.status_code}, {response.text}")

        except requests.exceptions.RequestException as e:
            flash("Unable to add VM. Please try again later.", "danger")
            print(f"Error adding VM: {e}")
            print(f"API Response: {response.status_code}, {response.text}")  # More detailed logging
    return render_template('vm/add_vm.html')

# Delete a virtual machine
@app.route('/vms/<int:vmid>/delete', methods=['GET', 'POST'])
def delete_vm(vmid):
    if request.method == 'POST':
        try:
            # Sending a request to the remote API to delete the VM
            api_url = f"{app.config['API_BASE_URL']}/vms/{vmid}/delete"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers)
            response.raise_for_status()
            flash("VM deleted successfully!", "success")
        except requests.exceptions.RequestException as e:
            flash("Unable to delete VM. Please try again later.", "danger")
            print(f"Error deleting VM: {e}")
        return redirect(url_for('view_all_vms'))


# Update attributes for a virtual machine
@app.route('/vms/<int:vmid>/update', methods=['GET', 'POST'])
def update_vm_attributes(vmid):
    if request.method == 'POST':
        try:
            data = {
                "powerstate": request.form['powerstate'],
                "networkstatus": request.form['networkstatus'],
                "vmstatus": request.form['vmstatus']
            }
            api_url = f"{app.config['API_BASE_URL']}/vms/{vmid}/update-attributes"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            flash("VM attributes updated successfully!", "success")
            return redirect(url_for('view_vm_details', vmid=vmid))
        except requests.exceptions.RequestException as e:
            flash("Unable to update VM attributes. Please try again later.", "danger")
            print(f"Error updating VM attributes: {e}")
            return redirect(url_for('view_vm_details', vmid=vmid))
    else:
        try:
            api_url = f"{app.config['API_BASE_URL']}/vms/{vmid}"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            vm = response.json()
            return render_template('vm/update_vm_attributes.html', vm=vm)
        except requests.exceptions.RequestException as e:
            flash("Unable to retrieve VM details. Please try again later.", "danger")
            print(f"Error fetching VM details: {e}")
            return redirect(url_for('view_all_vms'))

# Checkout a virtual machine
@app.route('/vms/checkout', methods=['GET', 'POST'])
def checkout_vm():
    if request.method == 'POST':
        try:
            data = {
                "username": request.form['username'],
                "avdhost": request.form['avdhost']
            }
            api_url = f"{app.config['API_BASE_URL']}/vms/checkout"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            vm = response.json()  # Assuming the API returns the checked out VM details
            flash("Successfully Checkedout VM!", "success")
            return redirect(url_for('view_vm_details', vmid=vm['VMID']))
        except requests.exceptions.RequestException as e:
            flash("Unable to Checkout VM Please try again later.", "danger")
            print(f"Error checking out VM: {e}")
            return redirect(url_for('view_all_vms'))
    return render_template('vm/checkout_vm.html')

# Release a virtual machine by Hostname
@app.route('/vms/<hostname>/release', methods=['GET', 'POST'])
def release_vm(hostname):
    if request.method == 'POST':
        try:
            api_url = f"{app.config['API_BASE_URL']}/vms/{hostname}/release"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers)
            response.raise_for_status()
            flash(f"VM '{hostname}' released successfully!", "success")
        except requests.exceptions.RequestException as e:
            flash(f"Unable to release VM '{hostname}'. Please try again later.", "danger")
            print(f"Error releasing VM: {e}")
        return redirect(url_for('view_all_vms'))


# Return a virtual machine
@app.route('/vms/<int:vmid>/return', methods=['GET', 'POST'])
def return_vm(vmid):
    if request.method == 'POST':
        try:
            api_url = f"{app.config['API_BASE_URL']}/vms/{vmid}/return"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers)
            response.raise_for_status()
            flash(f"VM '{vmid}' returned successfully!", "success")
        except requests.exceptions.RequestException as e:
            flash(f"Unable to return VM '{vmid}'. Please try again later.", "danger")
            print(f"Error returning VM: {e}")
        return redirect(url_for('view_all_vms'))

@app.route('/vms/history', methods=['GET', 'POST'])
def vm_history():
    if request.method == 'POST':
        try:
            # Get the date strings directly from the form
            startdate = request.form.get('startdate')
            enddate = request.form.get('enddate')
            limit = request.form.get('limit', 'null')

            # Check if ignore_dates or ignore_limit is checked
            ignore_dates = request.form.get('ignore_dates')
            ignore_limit = request.form.get('ignore_limit')

            # If ignore_limit is checked, set limit to "null"
            if ignore_limit:
                limit = "null"

            # If ignore_dates is checked, set dates to "null"
            if ignore_dates:
                startdate = "null"
                enddate = "null"
            else:
                # Convert dates to MM/DD/YYYY format if they are not ignored
                if startdate:
                    startdate = datetime.strptime(startdate, '%Y-%m-%d').strftime('%m/%d/%Y')
                else:
                    startdate = "null"

                if enddate:
                    enddate = datetime.strptime(enddate, '%Y-%m-%d').strftime('%m/%d/%Y')
                else:
                    enddate = "null"

            # Prepare data dictionary, passing dates as strings
            data = {
                "startdate": startdate,
                "enddate": enddate,
                "limit": limit if limit else "null"
            }

            # Store the data in session for later use in GET requests
            session['vm_history_data'] = data

            # Fetch the VM history from the API
            api_url = f"{app.config['API_BASE_URL']}/vms/history"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            vm_history = response.json()

            # Store the fetched data in session
            session['vm_history'] = vm_history

            flash("VM history retrieved successfully!", "success")
            return redirect(url_for('vm_history'))
        except requests.exceptions.RequestException as e:
            flash("Unable to retrieve VM history. Please try again later.", "danger")
            print(f"Error retrieving VM history: {e}")
            return redirect(url_for('view_all_vms'))
    else:
        # Handle GET requests, use session data if available
        vm_history = session.get('vm_history', [])
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        total_items = len(vm_history)
        total_pages = (total_items + per_page - 1) // per_page

        start = (page - 1) * per_page
        end = start + per_page
        vm_history_paginated = vm_history[start:end]

        return render_template('vm/vm_history.html', 
                               vm_history=vm_history_paginated, 
                               page=page, 
                               total_pages=total_pages,
                               per_page=per_page)


# ===============================
# Scaling and Scaling Rules APIs
# ===============================
    
# Retrieve all scaling rules
@app.route('/scaling/rules')
def view_all_rules():
    try:
        api_url = f"{app.config['API_BASE_URL']}/scaling/rules"
        headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        rules = response.json()
        return render_template('scaling/view_all_rules.html', rules=rules)
    except requests.exceptions.RequestException as e:
        flash("Unable to retrieve scaling rules. Please try again later.", "danger")
        print(f"Error retrieving scaling rules: {e}")
        return redirect(url_for('index'))


# Retrieve details for a specific scaling rule
@app.route('/scaling/rules/<int:ruleid>')
def view_rule_details(ruleid):
    try:
        api_url = f"{app.config['API_BASE_URL']}/scaling/rules/{ruleid}"
        headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        rule = response.json()
        return render_template('scaling/view_rule_details.html', rule=rule)
    except requests.exceptions.RequestException as e:
        flash("Unable to retrieve scaling rule details. Please try again later.", "danger")
        print(f"Error retrieving scaling rule details: {e}")
        return redirect(url_for('view_all_rules'))


# Create a new scaling rule
@app.route('/scaling/rules/create', methods=['GET', 'POST'])
def create_rule():
    if request.method == 'POST':
        try:
            data = {
                "minvms": request.form['minvms'],
                "maxvms": request.form['maxvms'],
                "scaleupratio": request.form['scaleupratio'],
                "scaleupincrement": request.form['scaleupincrement'],
                "scaledownratio": request.form['scaledownratio'],
                "scaledownincrement": request.form['scaledownincrement']
            }
            api_url = f"{app.config['API_BASE_URL']}/scaling/rules/create"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers, json=data)
            print(f"API Response: {response.status_code}, {response.text}")  # Debug logging
            if response.status_code == 201:
                flash("Scaling rule created successfully!", "success")
                return redirect(url_for('view_all_rules'))
            else:
                flash(f"Unexpected error occurred: {response.status_code} - {response.text}", "danger")

        except requests.exceptions.RequestException as e:
            flash("Unable to create scaling rule. Please try again later.", "danger")
            print(f"Error creating scaling rule: {e}")
            print(f"API Response: {response.status_code if response else 'No Response'}, {response.text if response else 'No Text'}")
    return render_template('scaling/create_rule.html')


# Update an existing scaling rule
@app.route('/scaling/rules/<int:ruleid>/update', methods=['GET', 'POST'])
def update_rule(ruleid):
    if request.method == 'POST':
        try:
            data = {
                "minvms": request.form['minvms'],
                "maxvms": request.form['maxvms'],
                "scaleupratio": request.form['scaleupratio'],
                "scaleupincrement": request.form['scaleupincrement'],
                "scaledownratio": request.form['scaledownratio'],
                "scaledownincrement": request.form['scaledownincrement']
            }
            api_url = f"{app.config['API_BASE_URL']}/scaling/rules/{ruleid}/update"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            flash("Scaling rule updated successfully!", "success")
            return redirect(url_for('view_rule_details', ruleid=ruleid))
        except requests.exceptions.RequestException as e:
            flash("Unable to update scaling rule. Please try again later.", "danger")
            print(f"Error updating scaling rule: {e}")
            return redirect(url_for('view_rule_details', ruleid=ruleid))
    else:
        try:
            api_url = f"{app.config['API_BASE_URL']}/scaling/rules/{ruleid}"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            rule = response.json()
            return render_template('scaling/update_rule.html', rule=rule)
        except requests.exceptions.RequestException as e:
            flash("Unable to retrieve scaling rule details. Please try again later.", "danger")
            print(f"Error fetching scaling rule details: {e}")
            return redirect(url_for('view_all_rules'))


# Delete a scaling rule
@app.route('/scaling/rules/<int:ruleid>/delete', methods=['POST'])
def delete_rule(ruleid):
    try:
        api_url = f"{app.config['API_BASE_URL']}/scaling/rules/{ruleid}/delete"
        headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
        response = requests.post(api_url, headers=headers)
        response.raise_for_status()
        flash("Scaling rule deleted successfully!", "success")
    except requests.exceptions.RequestException as e:
        flash("Unable to delete scaling rule. Please try again later.", "danger")
        print(f"Error deleting scaling rule: {e}")
    return redirect(url_for('view_all_rules'))

# Scaling activity log
@app.route('/scaling/log', methods=['GET', 'POST'])
def scaling_activity_log():
    if request.method == 'POST':
        try:
            # Get the date strings directly from the form
            startdate = request.form.get('startdate')
            enddate = request.form.get('enddate')
            limit = request.form.get('limit', 'null')

            # Check if ignore_dates or ignore_limit is checked
            ignore_dates = request.form.get('ignore_dates')
            ignore_limit = request.form.get('ignore_limit')

            # If ignore_limit is checked, set limit to "null"
            if ignore_limit:
                limit = "null"

            # If ignore_dates is checked, set dates to "null"
            if ignore_dates:
                startdate = "null"
                enddate = "null"
            else:
                # Convert dates to MM/DD/YYYY format if they are not ignored
                if startdate:
                    startdate = datetime.strptime(startdate, '%Y-%m-%d').strftime('%m/%d/%Y')
                else:
                    startdate = "null"

                if enddate:
                    enddate = datetime.strptime(enddate, '%Y-%m-%d').strftime('%m/%d/%Y')
                else:
                    enddate = "null"

            # Prepare data dictionary, passing dates as strings
            data = {
                "startdate": startdate,
                "enddate": enddate,
                "limit": limit if limit else "null"
            }

            # Store the data in session for later use in GET requests
            session['scaling_activity_log_data'] = data

            # Fetch the scaling activity log from the API
            api_url = f"{app.config['API_BASE_URL']}/scaling/log"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            log = response.json()

            # Store the fetched data in session
            session['scaling_activity_log'] = log

            flash("Scaling activity log retrieved successfully!", "success")
            return redirect(url_for('scaling_activity_log'))
        except requests.exceptions.RequestException as e:
            flash("Unable to retrieve scaling activity log. Please try again later.", "danger")
            print(f"Error retrieving scaling activity log: {e}")
            return redirect(url_for('view_all_rules'))
    else:
        # Handle GET requests, use session data if available
        log = session.get('scaling_activity_log', [])
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        total_items = len(log)
        total_pages = (total_items + per_page - 1) // per_page

        start = (page - 1) * per_page
        end = start + per_page
        log_paginated = log[start:end]

        return render_template('scaling/scaling_activity_log.html', 
                               log=log_paginated, 
                               page=page, 
                               total_pages=total_pages,
                               per_page=per_page)



# Scaling rules history
@app.route('/scaling/rules/history', methods=['GET', 'POST'])
def scaling_rules_history():
    if request.method == 'POST':
        try:
            # Get the date strings directly from the form
            startdate = request.form.get('startdate')
            enddate = request.form.get('enddate')
            limit = request.form.get('limit', 'null')

            # Check if ignore_dates or ignore_limit is checked
            ignore_dates = request.form.get('ignore_dates')
            ignore_limit = request.form.get('ignore_limit')

            # If ignore_limit is checked, set limit to "null"
            if ignore_limit:
                limit = "null"

            # If ignore_dates is checked, set dates to "null"
            if ignore_dates:
                startdate = "null"
                enddate = "null"
            else:
                # Convert dates to MM/DD/YYYY format if they are not ignored
                if startdate:
                    startdate = datetime.strptime(startdate, '%Y-%m-%d').strftime('%m/%d/%Y')
                else:
                    startdate = "null"

                if enddate:
                    enddate = datetime.strptime(enddate, '%Y-%m-%d').strftime('%m/%d/%Y')
                else:
                    enddate = "null"

            # Prepare data dictionary, passing dates as strings
            data = {
                "startdate": startdate,
                "enddate": enddate,
                "limit": limit if limit else "null"
            }

            # Store the data in session for later use in GET requests
            session['scaling_rules_history_data'] = data

            # Fetch the scaling rules history from the API
            api_url = f"{app.config['API_BASE_URL']}/scaling/rules/history"
            headers = {'Ocp-Apim-Subscription-Key': app.config['API_KEY']}
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            history = response.json()

            # Store the fetched data in session
            session['scaling_rules_history'] = history

            flash("Scaling rules history retrieved successfully!", "success")
            return redirect(url_for('scaling_rules_history'))
        except requests.exceptions.RequestException as e:
            flash("Unable to retrieve scaling rules history. Please try again later.", "danger")
            print(f"Error retrieving scaling rules history: {e}")
            return redirect(url_for('view_all_rules'))
    else:
        # Handle GET requests, use session data if available
        history = session.get('scaling_rules_history', [])
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        total_items = len(history)
        total_pages = (total_items + per_page - 1) // per_page

        start = (page - 1) * per_page
        end = start + per_page
        history_paginated = history[start:end]

        return render_template('scaling/scaling_rules_history.html', 
                               history=history_paginated, 
                               page=page, 
                               total_pages=total_pages,
                               per_page=per_page)



if __name__ == '__main__':
    app.run(debug=True)