# z/OS Compatibility Dashboard
## Simple presentation story and speaker notes

This guide follows the PowerPoint deck `zOS_Compatibility_Dashboard_Story.pptx`.
It is written as a presentation script: each section has the slide message,
simple talking points, and an optional line to say aloud.

## Presentation in one sentence

This dashboard brings vendor z/OS compatibility information into one place,
checks an organization's product inventory against it, and helps teams spot
migration risks before they make production changes.

## Slide 1 — z/OS Compatibility Dashboard

**On the slide**
- Vendor support, product inventory, and migration readiness in one view.
- IBM Z | z/OS migration planning.

**Say**
"This is a dashboard to help a team understand whether the software products it
uses are reported as compatible with a target z/OS release."

## Slide 2 — The challenge

**On the slide**
- Compatibility details live across different vendor websites and spreadsheets.
- Teams need to check products, versions, support status, and maintenance.
- Missing information can be mistaken for a green light.

**Say**
"Before a z/OS upgrade, teams may need to check many products across several
vendors. That information is spread out and can be hard to compare. The
dashboard organizes the available statements, while keeping unknown information
visible."

## Slide 3 — The solution

**On the slide**
- One dashboard for six vendors and three z/OS releases.
- Search, filter, and compare the compatibility records.
- Check an inventory and download an Excel report.

**Say**
"The dashboard brings IBM, Broadcom, BMC, Rocket, Precisely, and ASG records
together. A user can choose a z/OS release, explore the matrix, check an
inventory, and export the result."

## Slide 4 — How the parts work together

**On the slide**
1. Vendor CSV files hold the compatibility records.
2. The compatibility layer loads, cleans, matches, filters, and summarizes them.
3. The Streamlit app displays the dashboard and user workflows.
4. The RAG layer finds relevant rows and can ask Granite to explain them.

**Say**
"Think of the solution as four connected parts. The CSV files are the source
records. The compatibility module prepares and checks those records. The app
shows them to people. The optional RAG feature finds relevant records for a
question and can use Granite to write a short explanation."

## Slide 5 — The dashboard (App)

**On the slide**
- **Overview:** headline counts, status charts, vendor summary, and items to review.
- **Compatibility matrix:** filter by release, vendor, status, PTF, and search text.
- **Maintenance details:** best-effort extraction of PTF, USERMOD, SYSMOD, prerequisite, and corequisite text from linked vendor pages; IBM APAR-linked PTF IDs where publicly listed.
- **Check my products:** choose products or upload an inventory.
- **Ask watsonx:** ask a natural-language question about the records.
- **Sources:** open vendor reference pages.

**Say**
"The app is the front door. The Overview gives a quick snapshot. The matrix is
for detailed research. The inventory checker answers questions about a selected
set of products. The Ask tab searches the same data, and Sources helps users
verify the information with vendors."

## Slide 6 — The compatibility data (CompatibilityDB)

**On the slide**
- Reads `data/*_compat.csv` and combines the records.
- Normalizes missing fields and removes duplicate Vendor + Product + VRM rows.
- Supports z/OS 3.2, 3.1, and 2.5.
- Matches inventory by vendor, product, and VRM.
- Creates Excel workbooks with clickable source links.

**Say**
"The compatibility module is the data steward. It combines the vendor files,
keeps the rows in a consistent shape, and provides the lookup and reporting
functions. VRM means Version, Release, and Modification—the product version
being checked. When a product cannot be matched, the app reports it rather
than silently calling it compatible."

## Slide 7 — Understanding the result

**On the slide**
- **Yes:** the data says compatible for the selected release.
- **No:** the data says not compatible.
- **In Progress:** the vendor reports support is in progress.
- **Unverified:** no vendor statement was found in this data.
- **PTF required:** check and apply the vendor-listed maintenance as required.

**Say**
"These statuses are not interchangeable. In particular, Unverified does not
mean Yes. It means the data we have does not establish compatibility, so the
team needs to check the vendor source. Even a Yes result may require a PTF."

## Slide 8 — The RAG assistant

**On the slide**
- **Retrieve:** TF-IDF searches product, vendor, version, status, PTF, and comments.
- **Ground:** only the matching compatibility rows are passed to the answer step.
- **Generate (optional):** watsonx.ai Granite explains those rows.
- Without credentials, the app still displays the matching rows.

**Say**
"RAG means Retrieval-Augmented Generation. First, the system searches the
compatibility records for rows that match the question. If watsonx.ai is
configured, Granite receives those rows and writes an explanation. If it is
not configured, users still get the matching records. The AI is an explainer;
the structured vendor data remains the source of truth."

**Technical note for Q&A**
The current retriever uses TF-IDF and cosine similarity. It is keyword/statistical
text matching, not a vector database or a live vendor search. The optional model
is watsonx.ai Granite. This is not a direct watsonx Assistant integration.

## Slide 9 — A user journey

**On the slide**
1. Pick a target release, such as z/OS 3.2.
2. Review the portfolio status and items needing attention.
3. Filter or search the matrix, or upload an inventory with Vendor, Product, VRM.
4. Review blockers, PTF needs, and unverified items.
5. Open vendor sources and export an Excel report.

**Say**
"A migration planner starts with the target release, looks at the risks, checks
the organization's product list, and follows the source links for anything
that needs confirmation. The Excel export makes it easier to share the results
with the wider project team."

## Slide 10 — Trust, limits, and next steps

**On the slide**
- Compatibility data is a snapshot, not a live vendor feed.
- Confirm statuses, PTFs, and dates with the vendor before production changes.
- Protect the app and keep API keys in a secret manager.
- watsonx.ai Granite is included; Assistant webhook/API integration is separate.

**Say**
"The dashboard helps organize research; it does not replace vendor confirmation
or production change controls. Compatibility statuses depend on the supplied
CSV data. Maintenance details are best-effort text fetched from linked vendor
pages; for IBM, public SPCR/APAR reports are checked without an API key and
published PTF IDs are extracted when available. Results may be incomplete or
unavailable. Downloading some PTFs may require IBM support entitlement. The optional Granite answers depend
on watsonx.ai credentials. If we want watsonx
Assistant to query the data directly, we need to add and secure an HTTPS API
that Assistant can call."

## Closing line

"The value is a clearer, traceable starting point for z/OS migration planning:
know what is supported, see what needs attention, and verify the evidence before
making a production decision."

## Questions to be ready for

**Is the data live?**  
Compatibility statuses come from the packaged CSV files. The app also fetches
linked vendor pages at startup; IBM SPCR/APAR pages are queried for product-
specific service references and PTF IDs where published. Neither process
replaces a human check of current vendor statements.

**Does Unverified mean unsupported?**  
No. It means this dataset does not contain a vendor statement for that product
and release. It must be checked.

**Does the AI decide compatibility?**  
No. The compatibility status comes from the structured records. Granite may
explain retrieved rows but should not replace the source record or vendor page.

**Is watsonx Assistant already connected?**  
No. The app optionally calls watsonx.ai Granite. Assistant can link users to the
dashboard today; direct data lookup requires a separate webhook/API.

**What happens if Granite is not configured?**  
The dashboard still works. The Ask tab shows matching rows instead of a
generated answer.

## Accuracy note for the presenter

The packaged CSVs currently contain 240 distinct Vendor + Product + VRM rows
across the six vendors. Counts can change when the source files are updated.
Describe them as records in the supplied dataset, not as the complete vendor
catalogue or an official IBM certification. The visual style is IBM
Carbon-inspired; this project is not represented as an IBM-certified product.
