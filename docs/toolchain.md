# Toolchain: authoring and validating semantic models on a Mac

Models here are authored by hand (or by an agent) as TMDL text in PBIP layout, validated locally with the Tabular
Object Model (TOM) on .NET, and proven end to end in a Fabric workspace when needed.

## What works where

| Step | macOS, no Desktop | Needs Windows + Power BI Desktop | Needs a Fabric workspace (capacity on) |
|---|---|---|---|
| Author TMDL (tables, columns, measures, relationships, M, refresh policy) | Yes, plain text | | |
| Parse TMDL, build the TOM object graph, `Model.Validate()`, round-trip | **Yes**, `tools/TmdlCheck` | | |
| Best-practice rule checks (descriptions, formats, keys, relationships, DAX hygiene) | **Yes**, `tools/TmdlCheck` | Tabular Editor BPA | Semantic Link Labs `run_model_bpa` in a notebook |
| DAX syntax and semantic check of measures | No (no engine on macOS) | Yes | **Yes**, on deploy and query |
| Run the Power Query M and load data | No (no mashup engine) | Yes | **Yes**, refresh |
| Query results (DAX) | No | Yes (DAX query view) | **Yes**, executeQueries REST API |
| Incremental refresh partitions | No | No (Desktop only loads the RangeStart/RangeEnd window) | **Yes** |
| Report authoring, visual check | No | Yes | Yes (web authoring) |
| Power BI Modeling MCP (Microsoft) | Hosted server only | Local server (Desktop or XMLA) | Hosted server, via XMLA |

### The Power BI Modeling MCP

Microsoft's [powerbi-modeling-mcp](https://github.com/microsoft/powerbi-modeling-mcp) edits models through TOM over an
Analysis Services connection: a running Power BI Desktop instance, or a Fabric workspace's XMLA endpoint (Write
permission on the model). It also opens PBIP/TMDL folders. Its README says the **local server doesn't support macOS;
on a Mac, use the hosted (remote) Power BI Authoring MCP server**, which is the one Microsoft recommends for authoring
models in a Fabric workspace anyway. So on this Mac the MCP route is: hosted MCP -> XMLA -> a workspace on an active
capacity. It's not installed here; the TMDL + TOM route below needs nothing but .NET.

## Local validation (TOM on macOS)

```sh
export DOTNET_ROOT=/opt/homebrew/opt/dotnet/libexec
dotnet run --project tools/TmdlCheck -- models/<name>/<Name>.SemanticModel/definition
```

`tools/TmdlCheck` (.NET 10, `Microsoft.AnalysisServices.NetCore.retail.amd64` 19.84.1; managed code, runs on
Apple silicon natively) does four things:

1. `TmdlSerializer.DeserializeDatabaseFromFolder`: TMDL syntax and object errors come back with file and line
   (`TmdlFormatException`, `TmdlSerializationException`).
2. `Model.Validate()`: TOM's own consistency checks (references between objects, sort-by targets, relationship ends).
3. A round trip TMDL -> TOM -> TMDL -> TOM, proving the object graph is complete.
4. Thirty rules modelled on Microsoft's Best Practice Analyzer set (descriptions, format strings, display folders,
   summarizeBy, hidden foreign keys, `isKey`, sort-by columns, a marked date table, auto date/time off, relationship
   direction and cardinality, data types, fixed decimal, DIVIDE, no IFERROR, column/measure reference style, unknown
   references). Error rules fail the run (exit 1).

Proven against deliberately broken copies: it catches TMDL syntax errors with the line, a wrong relationship column,
missing sort-by columns, a `/` division and a reference to a measure that doesn't exist.

**What it can't see:** whether DAX parses or evaluates (`[Trips] +` or a wrong function signature passes), whether
the M runs, and data problems (orphan keys, duplicate dimension keys). Those need the engine: the workspace below.

## Deploying and testing in Fabric

A Fabric workspace (here called **Semantic Models Lab**) on a small F2 capacity, holding only models from this repo. The capacity is **paused** except
while a test runs; an F2 bills per minute while active.

```sh
CAP=/subscriptions/<subscription>/resourceGroups/<resource-group>/providers/Microsoft.Fabric/capacities/<capacity>
WS=<workspace-id>
fab=~/.local/bin/fab

# 1. Resume the capacity (about 30 s)
az resource invoke-action --action resume --ids $CAP -o none

# 2. Deploy the PBIP semantic model (TMDL) as an item; -f overwrites the existing item
$fab import "Semantic Models Lab.Workspace/NYC Taxi Trips.SemanticModel" \
    -i models/nyc-taxi/NycTaxi.SemanticModel -f
DS=$($fab get "Semantic Models Lab.Workspace/NYC Taxi Trips.SemanticModel" -q id | tr -d '"')

# 3. First deploy only: anonymous credentials on each Web data source
$fab api -A powerbi "groups/$WS/datasets/$DS/datasources"      # gatewayId + datasourceId per source
$fab api -A powerbi -X patch "gateways/<gatewayId>/datasources/<datasourceId>" -i cred.json
#   cred.json: {"credentialDetails":{"credentialType":"Anonymous","credentials":"{\"credentialData\":\"\"}",
#               "encryptedConnection":"Encrypted","encryptionAlgorithm":"None","privacyLevel":"Public"}}

# 4. Refresh. applyRefreshPolicy=false loads the single RangeStart..RangeEnd partition;
#    true builds the incremental-refresh partitions (3 years: too much for an F2 test).
echo '{"type":"full","applyRefreshPolicy":false,"retryCount":0}' > refresh.json
$fab api -A powerbi -X post "groups/$WS/datasets/$DS/refreshes" -i refresh.json
$fab api -A powerbi "groups/$WS/datasets/$DS/refreshes?\$top=1"   # poll until Completed / Failed

# 5. DAX checks (models/<name>/tests/*.dax), one query per call
$fab api -A powerbi -X post "groups/$WS/datasets/$DS/executeQueries" -i query.json
#   query.json: {"queries":[{"query":"EVALUATE ..."}],"serializerSettings":{"includeNulls":true}}

# 6. Pause the capacity
az resource invoke-action --action suspend --ids $CAP -o none
```

What this proves that TOM on the Mac can't: the service accepts the definition (DAX in every measure and calculated
column compiles; a bad one fails the import or the refresh), the M runs against the live public URLs, data lands with
the types the model declares, relationships resolve (referential-integrity query), and measures return the expected
numbers, checked against figures computed independently from the raw files.

Next steps it enables: Microsoft's BPA in the service (a Fabric notebook with `semantic-link-labs`,
`labs.run_model_bpa(dataset, workspace)`), and the hosted Power BI Modeling MCP over the workspace's XMLA endpoint.

Gotchas found on the first deploy:

- **The credential test calls the data source root.** A `Web.Contents` root that answers 403 (the bare CloudFront host
  does) fails "set credentials", and the API has no "skip test connection". Point `Web.Contents` at a folder that
  answers 200 (`…/trip-data/`, `…/misc/`) and put the file name in `RelativePath`; each folder is its own data source.
- `RelativePath` keeps the data source static, so the service can refresh a query that builds file names from
  parameters.
