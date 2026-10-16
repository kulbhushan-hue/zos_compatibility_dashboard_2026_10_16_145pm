# Deploy on IBM Cloud Code Engine (with watsonx.ai Granite)

## 0. Prerequisites
- IBM Cloud account, `ibmcloud` CLI with plugins: `ibmcloud plugin install code-engine container-registry`
- A watsonx.ai project (note its Project ID) in the same region as WATSONX_URL
- An IBM Cloud API key: `ibmcloud iam api-key-create zos-app-key`

## 1. Test locally (optional)
    pip install -r requirements.txt
    export WATSONX_APIKEY=...  WATSONX_PROJECT_ID=...
    streamlit run app.py
Without the two variables the app still works and shows matching rows in the "Ask" tab.
At startup, the app also fetches each distinct vendor URL in the CSV records to
best-effort extract PTF, USERMOD, SYSMOD, prerequisite, and corequisite details.
Code Engine needs outbound HTTPS access to linked vendor domains. Results are
cached in memory for six hours; inaccessible pages are reported and do not mean
that no maintenance is required.
For IBM rows, the app additionally uses IBM's public SPCR and APAR pages to
match exact product/release reports and extract APAR-linked PTF identifiers.
This read-only lookup does not need an IBM API key. Downloading some fixes may
still require IBMid/support entitlement through IBM Shopz or Fix Central.

## 2. Log in and create a Code Engine project
    ibmcloud login --sso
    ibmcloud target -r us-south -g <resource-group>
    ibmcloud ce project create --name zos-compat
    ibmcloud ce project select --name zos-compat

## 3. Store the credentials as a secret (never in the image or git)
    ibmcloud ce secret create --name watsonx-creds \
      --from-literal WATSONX_APIKEY=<api-key> \
      --from-literal WATSONX_PROJECT_ID=<project-id> \
      --from-literal WATSONX_URL=https://us-south.ml.cloud.ibm.com \
      --from-literal WATSONX_MODEL_ID=ibm/granite-3-3-8b-instruct

## 4a. Deploy straight from this folder (Code Engine builds the Dockerfile)
    ibmcloud ce application create --name zos-compat \
      --build-source . --strategy dockerfile \
      --port 8080 --min-scale 1 --cpu 1 --memory 4G \
      --env-from-secret watsonx-creds

## 4b. Or build locally and push to IBM Container Registry
    ibmcloud cr namespace-add <namespace>
    docker build -t us.icr.io/<namespace>/zos-compat:1 .
    docker push us.icr.io/<namespace>/zos-compat:1
    ibmcloud ce application create --name zos-compat \
      --image us.icr.io/<namespace>/zos-compat:1 \
      --registry-secret <icr-secret> --port 8080 --min-scale 1 \
      --env-from-secret watsonx-creds

## 5. Open it
    ibmcloud ce application get --name zos-compat --output url

## 6. Update data or code
Edit the CSVs in `data/`, then run:
    ibmcloud ce application update --name zos-compat --build-source . --strategy dockerfile

## Notes
- Keep `--min-scale 1`: Streamlit uses websockets and a cold start drops sessions.
- `requests`, `beautifulsoup4`, and `pypdf` are installed through `requirements.txt` for vendor-page extraction.
- Allow outbound HTTPS egress to the approved vendor domains for maintenance-detail extraction.
- Confirm the Granite model id is listed in your region/project (watsonx.ai > Prompt Lab model list); change WATSONX_MODEL_ID in the secret if not.
- Code Engine apps are public by default; put IBM App ID / your SSO in front of it if the data is internal.
