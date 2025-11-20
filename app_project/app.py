from flask import Flask, render_template, request, redirect, url_for, session
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv() # ← magically loads the .env file
app = Flask(__name__)
app.secret_key = 'a_very_secret_key_for_calc_app'

PROJECTS_FILE = 'projects.txt'

# --- Environment Variable for API Key (Recommended) ---
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')  # → returns your real key

# --- Helper Functions for Projects ---
def read_projects():
    if not os.path.exists(PROJECTS_FILE):
        return []
    try:
        with open(PROJECTS_FILE, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        print(f"Error reading projects file: {e}")
        return []

def write_projects(projects):
    try:
        with open(PROJECTS_FILE, 'w') as f:
            for project in projects:
                f.write(project + '\n')
        return True
    except Exception as e:
        print(f"Error writing projects file: {e}")
        return False

# --- Session Initialization ---
@app.before_request
def initialize_session():
    if 'history' not in session:
        session['history'] = []

# --- Calculator Route ---
@app.route('/', methods=['GET', 'POST'])
def calculator():
    result = None
    error = None

    if request.method == 'POST':
        if 'clear' in request.form:
            session['history'] = []
            session.modified = True
            return redirect(url_for('calculator'))

        try:
            num1 = float(request.form.get('num1'))
            num2 = float(request.form.get('num2'))
            operator = request.form.get('operator')

            if operator == 'add':
                result = num1 + num2
            elif operator == 'subtract':
                result = num1 - num2
            elif operator == 'multiply':
                result = num1 * num2
            elif operator == 'divide':
                if num2 == 0:
                    error = "Error: Division by zero is not allowed."
                else:
                    result = num1 / num2
            else:
                error = "Invalid operator selected."

            if result is not None:
                symbol_map = {'add': '+', 'subtract': '-', 'multiply': '×', 'divide': '÷'}
                symbol = symbol_map.get(operator, '?')
                formatted_result = f"{result:.2f}".rstrip('0').rstrip('.')

                calculation_entry = {
                    'num1': num1,
                    'num2': num2,
                    'operator_symbol': symbol,
                    'result': formatted_result
                }
                session['history'].append(calculation_entry)
                session.modified = True

        except ValueError:
            error = "Invalid input: Please enter valid numeric values."
        except Exception as e:
            error = f"An unexpected error occurred: {e}"

    return render_template('index.html', result=result, error=error, history=session.get('history', []))

# --- Projects Route ---
@app.route('/projects', methods=['GET', 'POST'])
def projects():
    message = None
    error = None
    projects_list = read_projects()

    if request.method == 'POST':
        if 'add_project' in request.form:
            new_project = request.form.get('project_name', '').strip()
            if not new_project:
                error = "Project name cannot be empty."
            elif len(new_project) > 100:
                error = "Project name must be 100 characters or less."
            elif len(projects_list) >= 3:
                error = "Only three projects accepted."
            else:
                projects_list.append(new_project)
                if write_projects(projects_list):
                    message = f"Project '{new_project}' added successfully!"
                else:
                    error = "Failed to save project."
                    projects_list.pop()

        elif 'delete_index' in request.form:
            try:
                idx = int(request.form.get('delete_index'))
                if 0 <= idx < len(projects_list):
                    deleted = projects_list.pop(idx)
                    if write_projects(projects_list):
                        message = f"Project '{deleted}' deleted."
                    else:
                        projects_list.insert(idx, deleted)
                        error = "Failed to delete from file."
            except:
                error = "Invalid delete request."

        elif 'update_project' in request.form:
            try:
                idx = int(request.form.get('update_index'))
                new_name = request.form.get('updated_name', '').strip()
                if not new_name or len(new_name) > 100 or idx < 0 or idx >= len(projects_list):
                    error = "Invalid update."
                else:
                    old = projects_list[idx]
                    projects_list[idx] = new_name
                    if write_projects(projects_list):
                        message = f"Project updated: '{old}' → '{new_name}'"
                    else:
                        projects_list[idx] = old
                        error = "Failed to save update."
            except:
                error = "Invalid update request."

    return render_template('projects.html', projects=projects_list, message=message, error=error)

# --- Stocks Route ---
@app.route('/stocks', methods=['GET', 'POST'])
def stocks():
    stock_data = None
    error = None
    ticker = ""

    if request.method == 'POST':
        ticker = request.form.get('ticker', '').strip().upper()
        if not ticker:
            error = "Please enter a ticker symbol."
        else:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': ticker,
                'apikey': ALPHA_VANTAGE_API_KEY
            }
            try:
                response = requests.get(url, params=params)
                data = response.json()

                if "Time Series (Daily)" in data:
                    time_series = data["Time Series (Daily)"]
                    latest_date = sorted(time_series.keys())[0]  # Most recent date
                    prices = time_series[latest_date]

                    stock_data = {
                        'ticker': ticker,
                        'date': latest_date,
                        'open': float(prices['1. open']),
                        'high': float(prices['2. high']),
                        'low': float(prices['3. low']),
                        'close': float(prices['4. close']),
                        'volume': int(prices['5. volume'])
                    }
                elif "Note" in data:
                    error = "API call frequency limit reached. Please wait a minute or use your own key."
                elif "Error Message" in data:
                    error = "Invalid ticker symbol or API error."
                else:
                    error = "Unexpected response from stock API."

            except Exception as e:
                error = f"Network error: {str(e)}"

    return render_template('stocks.html', stock_data=stock_data, error=error, ticker=ticker)

if __name__ == '__main__':
    app.run(debug=True)