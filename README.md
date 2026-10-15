# Viscan Dental Assistant — Take-Home Project

## Project Overview

The Viscan Dental Assistant is a web application developed as part of the Viscan AI Engineer take-home assignment. It helps users retrieve dental reports, prepare draft reports from clinical notes, and ask questions about previously retrieved reports.

The application uses synthetic patient data and runs locally through a FastAPI backend with a web-based chat interface.

### Features

- **Patient Report Retrieval:** Finds dental reports using natural-language requests and handles ambiguous patient names or missing reports.
- **Clinical Dictation:** Converts typed clinical observations or speech transcripts into structured draft reports containing findings, anatomical sites, source text, and uncertainty details.
- **Contextual Follow-up:** Allows users to ask follow-up questions about a selected report without repeating the patient details when the reference is clear.
- **Report Summaries:** Summarizes the latest report for a specified patient.
- **Report History:** Retrieves previous reports for the selected patient and lists the reports available in the synthetic dataset.
- **Report-based Questions:** Answers questions using the selected report and displays supporting evidence.
- **Chat Interface:** Provides a single interface for conversations, report previews, draft editing, and source evidence.
- **Speech Input:** Supports browser-based speech-to-text where the browser provides the required functionality.
- **Groq Integration:** Uses the Groq API for language interpretation and response generation when configured. A deterministic fallback mode is available when Groq is disabled.
- **Automated Testing:** Includes tests for report retrieval, ambiguous patient matching, contextual follow-up, and safe handling of clinical dictation.

## Important Notice

This project is intended only for demonstration and technical evaluation. It is not a medical device and must not be used to make clinical decisions.

All patient and report records are synthetic. Do not enter real patient information.

Every generated draft must be reviewed and approved by a qualified clinician before any clinical use.

## Technology Stack

- Python 3.9.13
- FastAPI
- Uvicorn
- Groq API
- Pydantic
- HTML, CSS, and JavaScript
- Pytest
- Synthetic JSON files for patient and report data

## Requirements

Before starting, make sure you have the following installed:

1. Python 3.9.13
2. A code editor such as Visual Studio Code
3. A terminal or command prompt
4. Internet access for installing packages, loading Google Fonts, and making Groq API requests when enabled

A Groq API key is optional. The application can run in fallback mode without one.

## Project Structure

The project contains the following main files and folders:

viscan_dental_assistant/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── data_store.py
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── patient_service.py
│   │   ├── report_service.py
│   │   ├── dictation_service.py
│   │   ├── conversation_service.py
│   │   └── intent_service.py
│   └── data/
│       ├── patients.json
│       └── reports.json
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── tests/
├── requirements.txt
├── .env.example
├── README.md
├── ARCHITECTURE.md
├── API_EXAMPLES.md
└── demo_script.md

The `app` directory contains the backend and application logic. The `services` folder separates patient lookup, report retrieval, dictation, conversation handling, and language-model integration. The `data` folder contains the synthetic records.

The `frontend` directory contains the chat interface and its styling. The `tests` directory contains the automated tests.

## Step 1: Open the Project Folder

Extract the project ZIP file if you have not already done so.

Open the extracted folder in Visual Studio Code or your preferred editor.

Open a terminal in the project root directory. This is the folder containing `app`, `frontend`, and `requirements.txt`.

## Step 2: Create a Virtual Environment

A virtual environment keeps the project's Python packages separate from other Python projects on your computer.

### Windows PowerShell

Run these commands one at a time:

py -3.9 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade "pip<25.2"
```

If PowerShell blocks activation, use the Windows Command Prompt instructions below instead.

### Windows Command Prompt

py -3.9 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade "pip<25.2"

### macOS or Linux

python3.9 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade "pip<25.2"

After activation, the terminal should show `(.venv)` near the beginning of the command line.

If the Python 3.9 launcher is unavailable, use your installed Python 3.9.13 executable to create the environment.

## Step 3: Install the Dependencies

With the virtual environment activated, run:

python -m pip install -r requirements.txt

Wait for the installation to finish. If an installation error occurs, check that the virtual environment is active and that you are running the command from the project root.

You can check the Python version with:


python --version


It should display Python 3.9.13.

## Step 4: Configure the Groq API

Groq integration enables more flexible interpretation of user requests and natural-language responses.

### Option A: Run without a Groq API key

If you do not have an API key, you can use the application's fallback mode.

Open the `.env.example` file and follow the project's environment configuration. Create a `.env` file in the project root and set:


GROQ_ENABLED=false

Save the file.

The fallback mode supports common report retrieval, previous-visit requests, report listing, and source-grounded summaries. More flexible natural-language requests may require Groq to be enabled.

### Option B: Run with Groq

1. Visit [Groq Console](https://console.groq.com/keys).
2. Sign in and create an API key.
3. Copy `.env.example` to a new file named `.env` in the project root.
4. Open `.env` and configure the following values:


GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
GROQ_ENABLED=true

Replace `your_groq_api_key` with your actual key.

The model name above is the configured example. Check the [Groq model documentation](https://console.groq.com/docs/models) to confirm that the model is available to your account. If it is not, update `GROQ_MODEL` to a currently supported model.

**Keep your API key private.** Do not put it in frontend JavaScript, commit the `.env` file to Git, or include it in screenshots or demo recordings.

## Step 5: Start the Application

Make sure your virtual environment is active and your terminal is in the project root.

Run:

uvicorn app.main:app --reload


When the server starts successfully, open the following address in your browser:

**Application:** [http://127.0.0.1:8000](http://127.0.0.1:8000)

The interactive API documentation is available at:

**API documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Keep the terminal running while using the application. To stop the server, press `Ctrl + C`.

If the port is already in use, stop the other process using it or start the application on another available port.

## Step 6: Test the Application

Once the website opens, try the following requests in the chat interface.

### Test 1: Retrieve the latest report

Enter:

Could you bring up Priya Sharma's most recent panoramic report?

Check that the application returns the matching synthetic report with its report ID, date, and findings.

### Test 2: Handle an ambiguous patient name

Enter:

Open Priya latest OPG report


If the name matches more than one synthetic patient, the assistant should ask for clarification instead of silently choosing a patient.

### Test 3: Summarize the selected report

After retrieving a report, enter:

Summarize it in simple language


Check that the answer refers to the selected report and displays the supporting evidence.

### Test 4: Retrieve a previous visit

Enter:


Show me the report from the previous visit for this patient.


Check that the application retrieves the appropriate earlier report for the selected patient.

### Test 5: List synthetic reports

Enter:


Give me all patient reports.


The application should display records from the bundled synthetic dataset only.

### Test 6: Create a draft report

Enter:

Generate a draft from this observation: Lower right third molar is horizontally impacted.


Inspect the generated draft. Check the structured findings, anatomical site, source text, and clinician-review requirement.

The draft should not introduce unsupported observations.

### Test 7: Handle missing information

Try requesting a report for a patient who does not exist.

The application should explain that the patient or report could not be found. It should not create a report to fill the gap.

### Test 8: Try speech input

If your browser supports the Web Speech API, use the Dictate option to enter a spoken request.

Review the transcribed text before submitting it. Speech recognition availability and behavior depend on the browser.

## Step 7: Run the Automated Tests

Open a second terminal in the project root, activate the same virtual environment, and run:

python -m pytest -q

The tests are configured to use deterministic behavior without requiring a Groq API key.

Check the output to confirm that the tests pass. If a test fails, read the error message and resolve the issue before recording the demo.

The tests cover important application behavior, including:

- Correct report retrieval
- Ambiguous patient identity
- Contextual follow-up
- Conservative handling of clinical dictation

## Step 8: Try the API Directly

FastAPI provides an interactive interface for testing the backend without using the chat interface.

1. Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
2. Find the endpoint you want to test.
3. Expand it and select **Try it out**.
4. Enter the required request data.
5. Select **Execute**.
6. Review the response and status code.

The project includes `API_EXAMPLES.md`, which provides example requests and responses for the main workflows.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Checks application health |
| `GET /api/patients` | Lists synthetic demo patients |
| `POST /api/reports/retrieve` | Retrieves a report from a natural-language request |
| `POST /api/dictation/draft` | Converts a clinical transcript into a structured draft |
| `POST /api/chat` | Handles chat requests and contextual follow-up |
| `GET /api/reports/REP001` | Retrieves a specific report by ID |

Example request for report retrieval:

{
  "query": "Open Priya Sharma latest OPG report",
  "session_id": "demo"
}


Example request for clinical dictation:

{
  "transcript": "Lower right third molar is horizontally impacted."
}

The exact response fields depend on the endpoint implementation. Refer to `/docs` and `API_EXAMPLES.md` for the current request and response formats.

## Application Architecture

The application separates language interpretation from report retrieval and validation.

1. The user submits a typed request or a speech transcript through the web interface.
2. The backend interprets the request and identifies the intended workflow.
3. Patient and report services query the synthetic JSON data.
4. Deterministic validation handles identity matching, missing reports, and other workflow rules.
5. The response includes the retrieved report, generated draft, or answer with supporting evidence.
6. The frontend displays the response and maintains conversation context for follow-up requests.

When Groq is enabled, the language model assists with request interpretation and response generation. When it is disabled, supported workflows use deterministic fallback logic.

The architecture and request flow are described in more detail in `ARCHITECTURE.md`.

## Privacy and Security

The application is designed for local demonstration using synthetic records.

- The Groq API key is stored in the backend environment configuration and is not sent to browser code.
- Request models use input validation.
- Missing or ambiguous patient requests are handled without silently inventing a result.
- Draft reports retain source text and require clinician review.
- Conversation state is stored in memory and is cleared when the application restarts.
- Authentication and patient-level authorization are not implemented.

Before using a system like this with real patient records, additional work would be required for authentication, authorization, secure storage, encryption, audit logging, privacy compliance, request limits, and operational monitoring.

## Known Limitations

- Patient matching uses simplified rules and is not suitable for production patient identification.
- Session data is stored in memory and is not persistent or designed for multiple application workers.
- Source-text checks provide a basic safeguard but cannot guarantee clinical correctness.
- Browser speech-to-text support varies, so typed input remains available.
- Groq model availability, API limits, response times, and usage costs depend on the provider and account.
- The application has not been clinically validated and should not be used for diagnosis or treatment decisions.

## Additional Documentation

The project includes the following supporting files:

- `ARCHITECTURE.md` — Application components, request flow, and design decisions.
- `API_EXAMPLES.md` — Example API requests and responses.
- `demo_script.md` — Suggested sequence for the project demonstration.
- `.env.example` — Environment variable template.
- `requirements.txt` — Python package dependencies.

## Project Deliverables

The submission contains the application source code, synthetic patient and report data, setup instructions, architecture documentation, API examples, and automated tests.

The project demonstrates report retrieval, clinical dictation, contextual follow-up, and report-based question answering within a local proof of concept.
