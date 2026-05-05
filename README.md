# Portfolio Contact Form — AWS Serverless

```
learnDeployment/
├── frontend/
│   └── index.html          # Static portfolio page (upload to S3)
├── backend/
│   └── contact_handler.py  # Lambda function (Python 3.12)
└── infrastructure/
    ├── template.yaml       # AWS SAM template
    └── samconfig.toml      # Deployment defaults
```

## Architecture

```
Browser → S3 (static site) → API Gateway (HTTP API) → Lambda → SES
```

## Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI installed (`pip install aws-sam-cli`)
- Two verified email addresses in Amazon SES (sandbox) or a verified domain

## Deploy

### 1. Build and deploy the backend

```bash
cd infrastructure
sam build
sam deploy --guided    # first time — saves answers to samconfig.toml
```

After deploy, copy the **ApiEndpoint** from the Outputs.

### 2. Wire up the frontend

Open `frontend/index.html` and replace:

```js
const API_ENDPOINT = 'https://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com/prod/contact';
```

with the URL from the SAM output.

### 3. Upload the frontend to S3

```bash
aws s3 cp frontend/index.html s3://<FrontendBucketName>/index.html
```

Visit the **FrontendWebsiteUrl** from the SAM output.

## Environment Variables (Lambda)

| Variable | Description |
|---|---|
| `SES_SENDER_EMAIL` | Verified SES sender address |
| `NOTIFY_EMAIL` | Where contact notifications are delivered |
| `ALLOWED_ORIGIN` | Frontend origin for CORS (`*` in dev, your domain in prod) |

## Moving out of SES sandbox

By default SES only sends to verified addresses. To send to anyone, request
production access in the AWS console under **SES → Account dashboard → Request production access**.
