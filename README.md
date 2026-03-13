# DevOps Capstone Project: Containerized Flask Application on Google Cloud Platform

This project demonstrates a complete DevOps workflow for a containerized Python Flask application deployed on Google Cloud Platform (GCP). It covers continuous integration/continuous deployment (CI/CD), artifact management, serverless deployment, API management, database integration, and comprehensive monitoring and logging.

## Table of Contents
1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [GCP Setup](#gcp-setup)
4. [Project Structure](#project-structure)
5. [Containerized Flask Application](#containerized-flask-application)
6. [Artifact Registry Setup](#artifact-registry-setup)
7. [CI/CD Pipeline with Cloud Build](#ci/cd-pipeline-with-cloud-build)
8. [Deployment to Cloud Run](#deployment-to-cloud-run)
9. [API Gateway Configuration](#api-gateway-configuration)
10. [Firestore Database Integration](#firestore-database-integration)
11. [Monitoring with Cloud Monitoring](#monitoring-with-cloud-monitoring)
12. [Logging with Cloud Logging](#logging-with-cloud-logging)
13. [Alerts and Notifications](#alerts-and-notifications)
14. [Local Development](#local-development)
15. [Cleanup](#cleanup)

## 1. Project Overview
This capstone project showcases the deployment of a simple Flask application that interacts with a Firestore database using a robust CI/CD pipeline. The application is containerized with Docker, artifacts are stored in Google Artifact Registry, and it's deployed as a serverless service on Cloud Run. An API Gateway sits in front to manage access, while Cloud Monitoring and Cloud Logging provide observability, complemented by alerting.

## 2. Prerequisites
Before you begin, ensure you have the following installed and configured:

*   **Google Cloud SDK (gcloud CLI):** [Installation Guide](https://cloud.google.com/sdk/docs/install)
*   **Docker Desktop/Engine:** [Installation Guide](https://docs.docker.com/get-docker/)
*   **Python 3.8+:** [Installation Guide](https://www.python.org/downloads/)
*   **Git:** [Installation Guide](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

## 3. GCP Setup
Follow these steps to set up your Google Cloud project:

1.  **Login to GCP:**
    ```bash
    gcloud auth login
    ```

2.  **Set your Project ID:**
    Replace `YOUR_PROJECT_ID` with your actual GCP Project ID.
    ```bash
    gcloud config set project YOUR_PROJECT_ID
    ```

3.  **Enable Required APIs:**
    ```bash
    gcloud services enable 
        cloudbuild.googleapis.com 
        run.googleapis.com 
        artifactregistry.googleapis.com 
        apigateway.googleapis.com 
        servicemanagement.googleapis.com 
        servicecontrol.googleapis.com 
        firestore.googleapis.com 
        logging.googleapis.com 
        monitoring.googleapis.com
    ```
    This command enables Cloud Build, Cloud Run, Artifact Registry, API Gateway, Service Management, Service Control, Firestore, Cloud Logging, and Cloud Monitoring APIs for your project.

4.  **Set Default Region (Optional but Recommended):**
    Choose a region close to you, e.g., `us-central1`.
    ```bash
    gcloud config set run/region YOUR_GCP_REGION
    ```

## 4. Project Structure
The project will have the following directory structure:

```
.
├── cloudbuild.yaml
├── openapi.yaml
├── README.md
├── app/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
└── .gcloudignore
```

## 5. Containerized Flask Application
The Flask application is a simple API that demonstrates interaction with Firestore.

### `app/app.py`
```python
import os
from flask import Flask, jsonify, request
from google.cloud import firestore

app = Flask(__name__)

# Initialize Firestore DB client
db = firestore.Client()
collection_name = 'messages'

@app.route('/')
def hello_world():
    return 'Hello from Containerized Flask App on Cloud Run!'

@app.route('/messages', methods=['POST'])
def add_message():
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        request_json = request.json
        message = request_json.get('message')
        if message:
            doc_ref = db.collection(collection_name).add({'message': message})
            return jsonify({"id": doc_ref[1].id, "message": message}), 201
        return jsonify({"error": "Message field is required"}), 400
    return jsonify({"error": "Content-Type must be application/json"}), 400

@app.route('/messages', methods=['GET'])
def get_messages():
    messages = []
    docs = db.collection(collection_name).stream()
    for doc in docs:
        messages.append(doc.to_dict())
    return jsonify(messages), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

```

### `app/requirements.txt`
```
Flask==2.3.2
gunicorn==21.2.0
google-cloud-firestore==2.11.1
```

### `app/Dockerfile`
```dockerfile
# Use the official Python image as a base
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
ENV PORT 8080
EXPOSE $PORT

# Run the application using Gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

## 6. Artifact Registry Setup
Google Artifact Registry is used to store your Docker images securely.

1.  **Create an Artifact Registry Repository:**
    Choose a repository name (e.g., `flask-app-repo`) and location (e.g., `us-central1`).
    ```bash
    gcloud artifacts repositories create flask-app-repo 
        --repository-format=docker 
        --location=YOUR_GCP_REGION 
        --description="Docker repository for Flask application"
    ```

2.  **Configure Docker to Authenticate to Artifact Registry:**
    ```bash
    gcloud auth configure-docker YOUR_GCP_REGION-docker.pkg.dev
    ```

## 7. CI/CD Pipeline with Cloud Build
Cloud Build is used to automate the build and deployment process. When changes are pushed to your repository, Cloud Build will automatically build the Docker image, push it to Artifact Registry, and deploy it to Cloud Run.

### `cloudbuild.yaml`
```yaml
steps:
# Step 1: Build the Docker image
- name: 'gcr.io/cloud-builders/docker'
  args:
    - 'build'
    - '-t'
    - '${_LOCATION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO_NAME}/${_SERVICE_NAME}:${SHORT_SHA}'
    - './app' # Path to your Dockerfile and application code
  id: Build

# Step 2: Push the Docker image to Artifact Registry
- name: 'gcr.io/cloud-builders/docker'
  args:
    - 'push'
    - '${_LOCATION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO_NAME}/${_SERVICE_NAME}:${SHORT_SHA}'
  id: Push

# Step 3: Deploy the image to Cloud Run
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  args:
    - 'gcloud'
    - 'run'
    - 'deploy'
    - '${_SERVICE_NAME}'
    - '--image'
    - '${_LOCATION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO_NAME}/${_SERVICE_NAME}:${SHORT_SHA}'
    - '--region=${_LOCATION}'
    - '--platform=managed'
    - '--allow-unauthenticated' # Adjust based on your security needs
  id: Deploy
  env:
    - 'PROJECT_ID=$PROJECT_ID'

images:
  - '${_LOCATION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO_NAME}/${_SERVICE_NAME}:${SHORT_SHA}'

substitutions:
  _SERVICE_NAME: flask-app
  _AR_REPO_NAME: flask-app-repo
  _LOCATION: YOUR_GCP_REGION # e.g., us-central1
```

### Triggering the CI/CD Pipeline
1.  **Create a Cloud Build Trigger:**
    Navigate to the Cloud Build section in the GCP Console and create a new trigger.
    *   **Source:** Connect to your repository (e.g., GitHub, Cloud Source Repositories).
    *   **Event:** "Push to a branch"
    *   **Branch:** `^main$` (or your main branch)
    *   **Configuration:** "Cloud Build configuration file"
    *   **Cloud Build file location:** `cloudbuild.yaml`
    *   **Substitutions:** Define `_LOCATION`, `_AR_REPO_NAME`, and `_SERVICE_NAME` as per your project.

2.  **Grant Cloud Run Admin Role to Cloud Build Service Account:**
    The Cloud Build service account needs permission to deploy to Cloud Run.
    ```bash
    PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
    CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
    gcloud projects add-iam-policy-binding YOUR_PROJECT_ID 
        --member="serviceAccount:${CLOUD_BUILD_SA}" 
        --role="roles/run.admin"
    ```
    Replace `YOUR_PROJECT_ID`.

## 8. Deployment to Cloud Run
The CI/CD pipeline automatically deploys the latest image to Cloud Run. However, you can also manually deploy or update the service.

### Manual Deployment
```bash
gcloud run deploy flask-app 
    --image YOUR_GCP_REGION-docker.pkg.dev/YOUR_PROJECT_ID/flask-app-repo/flask-app:latest 
    --platform managed 
    --region YOUR_GCP_REGION 
    --allow-unauthenticated 
    --set-env-vars=FLASK_ENV=production
```
Replace `YOUR_PROJECT_ID` and `YOUR_GCP_REGION`.

## 9. API Gateway Configuration
API Gateway provides a unified entry point for your Cloud Run service, allowing you to manage access, authentication, and routing.

1.  **Get Cloud Run Service URL:**
    First, get the URL of your deployed Cloud Run service.
    ```bash
    gcloud run services describe flask-app --platform managed --region YOUR_GCP_REGION --format="value(status.url)"
    ```
    Copy this URL, you'll need it for the `openapi.yaml`.

2.  **`openapi.yaml`:**
    Create an `openapi.yaml` file in your project root. Replace `YOUR_CLOUD_RUN_SERVICE_URL` with the URL you obtained in the previous step.

    ```yaml
    # openapi.yaml
    swagger: '2.0'
    info:
      title: Flask API Gateway
      description: API Gateway for the Flask Cloud Run service
      version: 1.0.0
    schemes:
      - https
    produces:
      - application/json
    paths:
      /:
        get:
          summary: Hello World Endpoint
          operationId: helloWorld
          x-google-backend:
            address: YOUR_CLOUD_RUN_SERVICE_URL
            protocol: h2
          responses:
            '200':
              description: A successful response
      /messages:
        get:
          summary: Get Messages
          operationId: getMessages
          x-google-backend:
            address: YOUR_CLOUD_RUN_SERVICE_URL/messages
            protocol: h2
          responses:
            '200':
              description: A list of messages
        post:
          summary: Add a Message
          operationId: addMessage
          x-google-backend:
            address: YOUR_CLOUD_RUN_SERVICE_URL/messages
            protocol: h2
          consumes:
            - application/json
          parameters:
            - in: body
              name: body
              description: Message object
              required: true
              schema:
                type: object
                properties:
                  message:
                    type: string
          responses:
            '201':
              description: Message added successfully
    ```

3.  **Create an API Configuration:**
    ```bash
    gcloud api-gateway api-configs create flask-api-config 
        --api=flask-api 
        --openapi-spec=openapi.yaml 
        --project=YOUR_PROJECT_ID 
        --backend-auth-service-account=YOUR_CLOUD_RUN_SERVICE_ACCOUNT # (e.g., flask-app-service-account@YOUR_PROJECT_ID.iam.gserviceaccount.com)
    ```
    *   `YOUR_CLOUD_RUN_SERVICE_ACCOUNT`: This is the service account associated with your Cloud Run service. You can find it in the Cloud Run service details under "Permissions" or by running `gcloud run services describe flask-app --format="value(spec.template.spec.serviceAccountName)"`. If you haven't specified one, it defaults to the project's default compute service account.

4.  **Create an API Gateway:**
    ```bash
    gcloud api-gateway gateways create flask-gateway 
        --api=flask-api 
        --api-config=flask-api-config 
        --location=YOUR_GCP_REGION 
        --project=YOUR_PROJECT_ID
    ```

5.  **Grant Invoker Permissions to API Gateway Service Account:**
    The API Gateway's service account needs permission to invoke the Cloud Run service. The service account used by API Gateway is typically `service-<PROJECT_NUMBER>@gcp-sa-apigateway.iam.gserviceaccount.com`.
    ```bash
    PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
    API_GATEWAY_SA="service-${PROJECT_NUMBER}@gcp-sa-apigateway.iam.gserviceaccount.com"
    gcloud run services add-iam-policy-binding flask-app 
        --member="serviceAccount:${API_GATEWAY_SA}" 
        --role="roles/run.invoker" 
        --region=YOUR_GCP_REGION 
        --platform=managed
    ```
    Replace `YOUR_PROJECT_ID` and `YOUR_GCP_REGION`.

6.  **Test the API Gateway:**
    After deployment, get the gateway URL:
    ```bash
    gcloud api-gateway gateways describe flask-gateway 
        --location=YOUR_GCP_REGION 
        --format="value(defaultHostname)"
    ```
    You can then test it with `curl`:
    ```bash
    curl -X GET https://YOUR_GATEWAY_URL/
    curl -X GET https://YOUR_GATEWAY_URL/messages
    curl -X POST https://YOUR_GATEWAY_URL/messages -H "Content-Type: application/json" -d '{"message": "Hello from API Gateway!"}'
    ```

## 10. Firestore Database Integration
The Flask application integrates with Google Cloud Firestore as its NoSQL database.

1.  **Initialize Firestore in Native Mode:**
    *   Navigate to the [Firestore section in the GCP Console](https://console.cloud.google.com/firestore).
    *   Click "SELECT NATIVE MODE" to start a new Firestore database.
    *   Choose a location for your Firestore database. This should ideally be in the same region as your Cloud Run service for lower latency.
    *   Click "CREATE DATABASE".

2.  **Grant Permissions to Cloud Run Service Account:**
    Your Cloud Run service account needs permission to access Firestore.
    ```bash
    CLOUD_RUN_SA=$(gcloud run services describe flask-app --platform managed --region YOUR_GCP_REGION --format="value(spec.template.spec.serviceAccountName)")
    gcloud projects add-iam-policy-binding YOUR_PROJECT_ID 
        --member="serviceAccount:${CLOUD_RUN_SA}" 
        --role="roles/datastore.user"
    ```
    Replace `YOUR_PROJECT_ID` and `YOUR_GCP_REGION`. The `datastore.user` role provides read/write access to Firestore data.

## 11. Monitoring with Cloud Monitoring
Cloud Run services are automatically integrated with Cloud Monitoring, providing out-of-the-box metrics for requests, latency, errors, and more.

1.  **View Cloud Run Metrics:**
    *   Navigate to the [Cloud Run services page in the GCP Console](https://console.cloud.google.com/run).
    *   Click on your `flask-app` service.
    *   Go to the "METRICS" tab to see default charts for your service's performance.

2.  **Create Custom Dashboards:**
    For more tailored insights, you can create custom dashboards in Cloud Monitoring:
    *   Navigate to [Cloud Monitoring Dashboards](https://console.cloud.google.com/monitoring/dashboards).
    *   Click "+ CREATE DASHBOARD".
    *   Add charts (e.g., Line Chart, Gauge) and select metrics related to your Cloud Run service (e.g., `Cloud Run Revision/Request count`, `Cloud Run Revision/Request latencies`).
    *   You can also monitor Firestore metrics (e.g., `Firestore Database/Read operations`, `Firestore Database/Write operations`).

## 12. Logging with Cloud Logging
Cloud Run services automatically send their logs (stdout/stderr) to Cloud Logging. This allows for centralized log management and analysis.

1.  **View Logs in Log Explorer:**
    *   Navigate to [Cloud Logging's Log Explorer](https://console.cloud.google.com/logs/explorer) in the GCP Console.
    *   You can filter logs by "Cloud Run Revision" resource type and specify your service name (`flask-app`).
    *   Logs from your Flask application (e.g., print statements, errors) and Cloud Run infrastructure will be visible here.

2.  **View Logs from the Command Line:**
    ```bash
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=flask-app" --limit=100
    ```

## 13. Alerts and Notifications
Cloud Monitoring allows you to set up alerts that notify you when specific conditions or thresholds are met for your application's metrics.

1.  **Create Alerting Policy:**
    *   Navigate to [Cloud Monitoring Alerting](https://console.cloud.google.com/monitoring/alerting) in the GCP Console.
    *   Click "CREATE POLICY".
    *   **Select Metric:** Choose relevant metrics for your Cloud Run service or API Gateway (e.g., "Request count" for Cloud Run, "5xx Errors" for API Gateway).
    *   **Configure Trigger:** Define the conditions that should trigger an alert (e.g., average latency > 500ms for 5 minutes).
    *   **Configure Notification Channels:** Set up notification channels (e.g., email, PagerDuty, Slack) to receive alerts.
        *   You can manage notification channels [here](https://console.cloud.google.com/monitoring/settings/notificationchannels).
    *   **Name and Save:** Give your alerting policy a descriptive name and save it.

    **Example Alert Scenarios:**
    *   High latency (e.g., average request latency > X ms).
    *   Increased error rates (e.g., HTTP 5xx errors > Y%).
    *   Low instance count (if your Cloud Run service scales down unexpectedly).

## 14. Local Development
You can run the Flask application locally for testing and development.

1.  **Clone the Repository:**
    ```bash
    git clone YOUR_REPOSITORY_URL
    cd your-repo-name
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r app/requirements.txt
    ```

3.  **Run the Flask Application:**
    ```bash
    python app/app.py
    ```
    The application will be accessible at `http://localhost:8080`.

4.  **Local Firestore Emulator (Optional):**
    For local development with Firestore, you can use the Firebase Emulator Suite:
    *   [Install Firebase CLI](https://firebase.google.com/docs/cli#install_the_firebase_cli)
    *   Initialize Firebase project (if not already done): `firebase init` (select Firestore emulator)
    *   Start the emulator: `firebase emulators:start`
    *   Configure your Flask app to connect to the emulator (e.g., set `FIRESTORE_EMULATOR_HOST` environment variable).

## 15. Cleanup
To avoid incurring unwanted charges, follow these steps to clean up the GCP resources created by this project.

1.  **Delete API Gateway:**
    ```bash
    gcloud api-gateway gateways delete flask-gateway --location=YOUR_GCP_REGION
    gcloud api-gateway apis delete flask-api
    ```

2.  **Delete Cloud Run Service:**
    ```bash
    gcloud run services delete flask-app --region=YOUR_GCP_REGION --platform=managed
    ```

3.  **Delete Artifact Registry Repository:**
    ```bash
    gcloud artifacts repositories delete flask-app-repo --location=YOUR_GCP_REGION
    ```

4.  **Delete Cloud Build Triggers:**
    Navigate to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers) in the GCP Console and delete the trigger you created.

5.  **Delete Firestore Database:**
    *   Navigate to the [Firestore section in the GCP Console](https://console.cloud.google.com/firestore).
    *   Go to the "Data" tab, then select "Delete Database" from the three dots menu.

6.  **Disable APIs (Optional):**
    If you no longer need the enabled APIs for your project, you can disable them.
    ```bash
    gcloud services disable 
        cloudbuild.googleapis.com 
        run.googleapis.com 
        artifactregistry.googleapis.com 
        apigateway.googleapis.com 
        servicemanagement.googleapis.com 
        servicecontrol.googleapis.com 
        firestore.googleapis.com 
        logging.googleapis.com 
        monitoring.googleapis.com
    ```

7.  **Delete GCP Project (Most Comprehensive Cleanup):**
    The most thorough way to clean up is to delete the entire GCP project. This will remove all resources associated with the project.
    ```bash
    gcloud projects delete YOUR_PROJECT_ID
    ```
    You will be prompted to confirm this action.
