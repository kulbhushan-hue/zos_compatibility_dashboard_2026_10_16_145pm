# z/OS Compatibility Dashboard: Mainframe and watsonx Assistant Deployment

This guide covers deploying the dashboard in an IBM Z environment and, optionally,
connecting it to **IBM watsonx Assistant**.

## Important: two different IBM AI services

The dashboard's optional generated answers currently use **watsonx.ai** and the
Granite model through `ibm-watsonx-ai`. This is not the same service as
**watsonx Assistant**.

- The dashboard works without either service: its Ask tab displays matching
  compatibility rows.
- Configure watsonx.ai credentials to enable the existing Granite-generated
  answers. See `DEPLOY_CODE_ENGINE.md` for a Code Engine example.
- Connecting a watsonx Assistant requires an HTTPS API/webhook that Assistant can
  call. The Streamlit app in this package is a browser application and does not
  currently expose that webhook API. A link from Assistant to the dashboard is
  possible without that API; querying dashboard data inside an Assistant action
  requires additional API integration.

## 1. Choose where the dashboard will run

### Recommended: z/OS Container Extensions (zCX)

Use zCX when the application must run in the z/OS environment as a Linux
container. zCX setup, networking, registry access, TLS, and operational
permissions are managed by your z/OS and network administrators. Ask them to
provision an instance and confirm the supported image architecture and container
deployment process for your z/OS release.

### Alternative: Linux on IBM Z

Run the container on an existing Linux on IBM Z server or virtual machine. This
usually provides the most familiar Docker/Podman workflow while keeping the
application on IBM Z.

### Native z/OS UNIX System Services (USS)

Native USS is not the recommended deployment for this package. The app depends
on Streamlit, pandas, scikit-learn, NumPy/SciPy, and Excel libraries; confirm
that compatible runtimes and packages are supported on your specific USS
environment before choosing this route. zCX or Linux on IBM Z avoids much of
that dependency-porting work.

## 2. Prerequisites and deployment decisions

Arrange these items before deployment:

- An IBM Z environment: provisioned zCX, or Linux on IBM Z; supported CPU and
  memory allocation (the Code Engine example uses 1 vCPU and 4 GB as a starting
  point, not a sizing guarantee).
- An administrator-approved container registry reachable from the runtime.
- A build host with Docker/Buildx or Podman and access to the project source.
- An approved inbound route to the dashboard, DNS name, HTTPS certificate, and
  firewall rules. Streamlit uses WebSockets; the proxy/load balancer must allow
  WebSocket upgrades and long-lived connections.
- An authentication/access-control decision. Do not expose compatibility data
  or an unauthenticated dashboard publicly unless that is explicitly approved.
- If using watsonx.ai: an IBM Cloud API key, watsonx.ai project ID or space ID,
  region URL, and a model ID enabled for that project.
- IBM's public Software Product Compatibility Reports (SPCR) and public APAR
  pages do not require a separate IBM API key for the dashboard's read-only
  lookup. Downloading/acquiring some PTFs can still require IBMid/support
  entitlement through IBM Shopz or Fix Central.
- If using watsonx Assistant data lookup: an Assistant instance, permission to
  configure actions/webhooks, and an HTTPS-reachable webhook API. If the API
  remains private to the mainframe network, configure an approved private
  connection or API gateway; Assistant must be able to reach the endpoint.

## 3. Prepare and validate the application image

1. Copy/extract the complete project folder onto an approved build host. Keep
   `app.py`, `compatibility_db.py`, `rag_engine.py`, `vendor_details.py`,
   `requirements.txt`, `Dockerfile`, `.dockerignore`, and the entire `data`
   directory together.
2. Check the target's architecture with the zCX/Linux administrator. IBM Z
   Linux images normally use `linux/s390x`; do not assume an image built for an
   x86 workstation will run there.
3. Build on an IBM Z Linux build host, or use a correctly configured multi-
   architecture builder. Example with Docker Buildx:

   ```sh
   docker buildx build --platform linux/s390x --load -t zos-compat:1 .
   ```

   Buildx `--load` support depends on the configured builder. If it cannot load
   the target image locally, build/push directly to an approved registry or
   build natively on IBM Z.
4. Run a test build and verify all declared dependencies install for the target
   architecture. In particular, test scikit-learn/NumPy/SciPy and
   `ibm-watsonx-ai`; availability of compatible Python wheels can depend on
   Python version and package releases.
5. At application startup, the dashboard fetches each distinct vendor URL linked
   by the CSV records. Allow outbound HTTPS to the approved IBM, Broadcom, BMC,
   Rocket, and Precisely domains. Page text is cached in process memory for six
   hours. Fetch failures are shown in the dashboard and do not stop it.
   For IBM rows, it also queries the public IBM SPCR JSON reports by exact
   product and VRM, reads z/OS requirement notes, follows cited APAR pages, and
   extracts PTF identifiers listed under applicable component levels. These
   IBM lookups do not use an API key and are cached for 24 hours.
6. Test locally or in a staging environment:

   ```sh
   docker run --rm -p 8080:8080 zos-compat:1
   ```

   Open `http://localhost:8080`, check the dashboard tabs and maintenance
   details column, test a matrix filter, download an Excel workbook, and check
   the Ask tab. Confirm the vendor CSVs were included in the image.

## 4. Publish the image to an approved registry

Use the registry and authentication method approved for your environment. For
example, after logging in and creating a registry namespace:

```sh
docker tag zos-compat:1 REGISTRY_HOST/NAMESPACE/zos-compat:1
docker push REGISTRY_HOST/NAMESPACE/zos-compat:1
```

Replace `REGISTRY_HOST/NAMESPACE` with your actual registry path. Do not put
registry passwords, API keys, or watsonx credentials in the image, source code,
or a committed file.

## 5. Deploy on zCX or Linux on IBM Z

### zCX

1. Have the z/OS administrator provision and configure zCX, including CPU and
   memory, persistent/log storage as required, IP connectivity, DNS, firewall,
   and access to the approved registry.
2. Have the administrator or authorized zCX operator pull the published image
   and create a service/container using the site's supported zCX procedure.
3. Configure the container to listen on port `8080`. The included Dockerfile
   starts Streamlit on `0.0.0.0:8080`.
4. Configure a stable service route and TLS-terminating reverse proxy or
   gateway. Preserve WebSocket support through the proxy.
5. Apply site-approved restart, monitoring, log-retention, authentication, and
   patching policies.
6. Validate through the final HTTPS URL from an authorized client network.

zCX access and container-management commands differ by z/OS release and local
configuration; use the IBM documentation for the installed z/OS release and
your site's runbook rather than copying Linux-host Docker commands onto USS.

### Linux on IBM Z

1. Pull the image from the approved registry on the Linux host.
2. Start it under the site's container runtime. Example:

   ```sh
   docker run -d --name zos-compat --restart unless-stopped \
     -p 8080:8080 REGISTRY_HOST/NAMESPACE/zos-compat:1
   ```

3. Restrict direct access to port 8080 and publish the app behind the approved
   HTTPS reverse proxy/load balancer. Configure WebSocket pass-through.
4. Verify the application and logs, then test it through the final HTTPS URL.

## 6. Configure optional watsonx.ai (Granite) answers

The existing code reads these environment variables:

- `WATSONX_APIKEY`
- `WATSONX_PROJECT_ID` **or** `WATSONX_SPACE_ID`
- `WATSONX_URL` (defaults to the US South endpoint)
- `WATSONX_MODEL_ID` (defaults to `ibm/granite-3-3-8b-instruct`)

1. Confirm that the chosen model is available to the watsonx.ai project/space
   and that network policy permits outbound HTTPS from the dashboard runtime to
   the watsonx.ai regional endpoint.
2. Store credentials in your platform's secret manager (for example, a
   protected zCX/container secret mechanism or Linux secret store). Inject them
   as runtime environment variables; do not bake them into the image.
3. Restart/redeploy the application with the secret values injected.
4. Check the sidebar for the assistant configuration status and test the Ask
   tab. If unavailable, the app displays matching source rows instead of
   generated answers.

## 7. Connect IBM watsonx Assistant

There are two supported approaches, depending on what you want Assistant to do.

### Option A: Link to the dashboard

This is the simplest option and does not require code changes:

1. Deploy and secure the dashboard at its HTTPS URL.
2. In watsonx Assistant, create an action that explains the dashboard's purpose
   and provides a link to that URL.
3. Publish/preview the Assistant and verify the link is available only to
   audiences authorized to use the dashboard.

Assistant will not query compatibility records with this approach; the user
opens the dashboard to search and review them.

### Option B: Let Assistant query compatibility data

This requires an additional application API; it is not included in the current
Streamlit-only implementation.

1. Implement an HTTPS webhook/API service that reads the same compatibility
   CSV data and supports the intended lookups, such as vendor, product, VRM,
   z/OS version, compatibility status, and PTF requirement.
2. Define strict request validation and return only the fields needed by the
   Assistant action. Treat `Unverified` as unknown, never as compatible.
3. Add authentication/authorization, TLS, request timeouts, rate limits, input
   size limits, and audit logging. Do not expose the container's filesystem or
   unrestricted query access.
4. Deploy the API on the mainframe-side runtime or an approved API platform.
   Provide Assistant a stable HTTPS URL it can reach. Set up private networking
   or an approved gateway if the service must not be public.
5. In watsonx Assistant, create an action for the compatibility lookup and
   configure its webhook according to the current Assistant interface/API.
   Map action variables to the API request and map the response fields into
   user-facing action steps.
6. Test successful matches, unknown products/VRMs, unverified support, PTF
   cases, unauthorized requests, timeouts, and unavailable API behavior in
   preview before publishing.
7. Keep the Assistant's wording grounded in the returned records and include a
   reminder to confirm compatibility on the vendor's live source before making
   production changes.

Consult IBM's current watsonx Assistant documentation for the webhook
configuration and request/response format supported by your Assistant plan and
interface. The format can vary by integration type.

## 8. Updates, operations, and troubleshooting

- To update compatibility data, change the appropriate CSV in `data/`, rebuild
  and publish a new image tag, then redeploy using the site's change process.
- To update application code or dependencies, build and test a new image; do
  not edit a running container as the deployment mechanism.
- Monitor application/container logs, memory/CPU, availability, and proxy
  WebSocket errors. Keep an operational owner for updating vendor sources.
- The PTF / USERMOD / SYSMOD / Prerequisites column is best-effort extraction
  from linked pages, not a complete or authoritative maintenance catalogue.
  Vendor page layouts, authentication, network policy, or absent text can limit
  results. Verify each item at the linked vendor source; an empty or failed
  extraction never means no maintenance is required.
- IBM SPCR notes can cite APARs; public APAR pages sometimes expose PTF IDs
  (also usable as SMP/E SYSMOD identifiers). An APAR is not itself a PTF.
  USERMODs are not inferred when IBM has not explicitly published one. Confirm
  the correct PTF for your installed component level, and obtain it through
  your entitled IBM service channel.
- A blank or incomplete matrix usually means the `data` directory was omitted
  from the image or the CSV schema is invalid.
- If the page loads but interactive widgets disconnect, check WebSocket
  forwarding, idle timeouts, and proxy buffering.
- If Granite answers are unavailable, check the injected secrets, project/space
  access, model availability, DNS, and outbound TLS connectivity. The matrix
  remains usable without Granite.
- If Assistant cannot invoke the webhook, check that its URL is HTTPS, reachable
  from Assistant, and returns the exact response format required by the
  configured Assistant integration.

## 9. IBM documentation and project references

- [z/OS Container Extensions documentation](https://www.ibm.com/docs/en/zos/3.2.0?topic=zcx-zos-container-extensions)
- [IBM watsonx Assistant documentation](https://cloud.ibm.com/docs/watson-assistant)
- [IBM watsonx.ai documentation](https://www.ibm.com/docs/en/watsonx/saas)
- [Existing Code Engine deployment guide](./DEPLOY_CODE_ENGINE.md)
