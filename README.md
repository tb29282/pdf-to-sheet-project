# PDF to Sheet Converter

A Streamlit web application that converts PDF documents to editable spreadsheets using Google Document AI.

## Features

- Secure login system
- PDF document upload and preview
- Automatic data extraction using Google Document AI
- Editable spreadsheet view
- CSV download functionality

## Prerequisites

- Python 3.8+
- Google Cloud account with Document AI API enabled
- Google Cloud service account with appropriate permissions

## Environment Variables

The following environment variables need to be set:

```bash
APP_PASSWORD=your_app_password
GOOGLE_CLOUD_PROJECT_ID=your_project_id
DOCUMENT_AI_PROCESSOR_ID=your_processor_id
DOCUMENT_AI_LOCATION=us  # or your preferred region
GOOGLE_APPLICATION_CREDENTIALS=path_to_your_service_account_key.json
```

## Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables
4. Run the application:
   ```bash
   streamlit run pdf_files/app.py
   ```

## Deployment to Streamlit Cloud

1. Push your code to a GitHub repository

2. Visit [Streamlit Cloud](https://share.streamlit.io/) and sign in

3. Create a new app and select your repository

4. Set the following:
   - Main file path: `pdf_files/app.py`
   - Python version: 3.8+

5. Add the required environment variables in Streamlit Cloud's secrets management:
   - Go to App Settings > Secrets
   - Add each environment variable as listed above

6. Deploy the application

## Security Notes

- Never commit sensitive credentials to the repository
- Always use environment variables for sensitive data
- The Google Cloud service account key should be stored securely
- Regularly rotate the app password and other credentials

## License

MIT License 