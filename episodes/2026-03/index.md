---
title: "OverArchitected: March 2026"
date: 2026-03-04
subtitle: "Nick Karpov & Holly Smith"
youtube_id: "vzu06KGTOrQ"
sections:
  - heading: "The Thumb Incident"
    timestamp: "0:00"
    docs: []
  - heading: "Autoloader File Events — Now Automatic"
    timestamp: "1:18"
    tag: "GA"
    docs:
      - label: "file events for external locations"
        url: "https://docs.databricks.com/aws/en/connect/unity-catalog/cloud-storage/manage-external-locations#file-events"
      - label: "file events explained"
        url: "https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/file-events-explained"
  - heading: "New Foundation Models on Databricks"
    timestamp: "7:01"
    tag: "GA"
    docs:
      - label: "Claude Opus 4.6"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2026/february#anthropic-claude-opus-46-now-available-as-a-databricks-hosted-model"
      - label: "Claude Sonnet 4.6"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2026/february#anthropic-claude-sonnet-46-now-available-as-a-databricks-hosted-model"
      - label: "Gemini 3.1 Pro"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2026/february#google-gemini-31-pro-preview-now-available-as-a-databricks-hosted-model"
  - heading: "Stateless Streaming Performance"
    timestamp: "11:40"
    tag: "GA"
    docs:
      - label: "AQE in stateless streaming"
        url: "https://docs.databricks.com/aws/en/release-notes/runtime/18.0#adaptive-query-execution-and-auto-optimized-shuffle-in-stateless-streaming-queries"
      - label: "dynamic partition adjustment"
        url: "https://docs.databricks.com/aws/en/release-notes/runtime/18.0#dynamic-shuffle-partition-adjustment-in-stateless-streaming-queries"
  - heading: "MLflow Traces to Delta via Unity Catalog"
    timestamp: "16:43"
    tag: "Beta"
    docs:
      - label: "MLflow traces in Unity Catalog (Beta)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2026/january#store-and-query-mlflow-traces-in-unity-catalog-beta"
  - heading: "Supervisor Agent (GA)"
    timestamp: "24:50"
    tag: "GA"
    docs:
      - label: "Supervisor Agent GA"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2026/february#agent-bricks-supervisor-agent-is-now-generally-available"
  - heading: "Metric Views — Window Functions and Filters"
    timestamp: "28:43"
    tag: "GA"
    docs:
      - label: "window functions in metric views"
        url: "https://docs.databricks.com/aws/en/release-notes/runtime/18.0#sql-window-functions-in-metric-views"
      - label: "filter clause in aggregates"
        url: "https://docs.databricks.com/aws/en/release-notes/runtime/18.0#filter-clause-for-measure-aggregate-functions-in-metric-views"
  - heading: "Multi-Statement Transactions (+ Delta Sharing)"
    timestamp: "20:49"
    tag: "GA"
    docs:
      - label: "multi-statement transaction support"
        url: "https://docs.databricks.com/aws/en/release-notes/runtime/18.1#delta-sharing-multi-statement-transaction-support"
---

## Autoloader File Events — Now Automatic

> **What is it?** When you create an external location in Unity Catalog, Databricks now automatically provisions the cloud resources (SNS topics, SQS queues on AWS; ADLS queues on Azure) to detect file changes. Autoloader gets event-driven ingestion out of the box — no manual cloud infrastructure setup.
>
> **Is it for you?** If you're ingesting files from cloud storage at any meaningful scale, this makes Autoloader significantly faster and more efficient. Previously you had to manually configure file event notifications — now it just works when you set up your external location.
>
> **Try it** Create or update an external location in Unity Catalog. File events are enabled by default. Your existing Autoloader jobs will automatically benefit from event-driven file discovery.

Autoloader is now mature enough that I can admit I didn't really understand what the hype was all about when we first released it. It's just Spark Structured Streaming with a file based source, right? Wrong. It's much faster than file based sources. All thanks to the file events queue. Now Databricks can orchestrate all that for you, even if it's an external location. It really goes to show you the power of iterating under an API surface area.

## New Foundation Models on Databricks

> **What is it?** Three new models on the Foundation Model API: **Claude Opus 4.6** and **Claude Sonnet 4.6** (Anthropic), plus **Gemini 3.1 Pro** (Google). All served through Databricks with instrumentation, inference tables, AI Gateway, and PII detection included.
>
> **Is it for you?** If you're building anything with LLMs on Databricks — agents, data extraction, code generation — these are the latest and most capable models available. Sonnet 4.6 matches the previous Opus 4.5 at a lower price point, making it a strong default for most workloads.
>
> **Try it** Model Serving > Create Endpoint > select from Foundation Models. Pay-per-token, no provisioning. Point any OpenAI-compatible client at the endpoint URL.

I've since tried Sonnet, and it's great, but, once you get a taste for the best models... why bother changing? For daily driving I think you want the best model possible - you can always optimize once you have specific workloads that require some LLM endpoint (whole other ball game). I **still** haven't tried Gemini but I did see a tweet that said something like "Gemini is beating everyone in the benchmarks and still nobody uses it". That made me laugh. Also, as an aside, I actually personally prefer codex 5.3 these days but our internal tooling is currently Claude Code... so, Claude for work, Codex for pleasure.

## Stateless Streaming Performance

> **What is it?** Three performance optimizations are now available for stateless streaming queries: **Adaptive Query Execution (AQE)** rebalances skewed partitions at runtime, **dynamic shuffle partition adjustment** right-sizes partitions based on actual data volume, and **auto-optimized shuffle** reduces overhead. All enabled by default — no configuration needed.
>
> **Is it for you?** If you have stateless streaming jobs (map, filter, projection — anything without aggregations or joins) that process unevenly distributed data, these optimizations reduce processing time and resource waste automatically.
>
> **Try it** Nothing to do — these are enabled by default on DBR 18.0+. Check your streaming query's execution plan to see AQE and optimized shuffle in action.

LOL. Thank you Holly, as always, for putting up with me :). As for real time streaming and performance... this is a REAL sleeper. Ali's been hammering this point on LI: Spark is now as good and in many places better than the other streaming engines. If you have stuff in Flink or w/e else, but you have access to Databricks... stop doing that!

## MLflow Traces to Delta via Unity Catalog

> **What is it?** MLflow experiment traces can now sync directly to a Delta table in Unity Catalog. One click in the Experiments UI — pick a catalog and schema — and a sync pipeline is created automatically. Every trace (sessions, calls, responses, latencies) becomes a queryable, shareable table.
>
> **Is it for you?** If you're running agents or LLM-powered features and need observability beyond the MLflow UI — dashboards, anomaly detection, cost analysis, or sharing trace data with other teams — this puts your traces where all your other governed data lives.
>
> **Try it** Go to your MLflow Experiment, click the Delta Sync button, select a destination catalog/schema, and name your table. The sync pipeline starts automatically.

Our trace story has been evolving. We've gone through a few iterations where one way or another traces have become available in UC. This integration isn't functionally new, but with respect to the platform I think we've found a good place for this to live. Tracing is a really hot subject... if you're on X, you've probably seen how basically anyone using an agent is self-rolling a tracing solution for both themselves and their teams. This is going to be a wild area for innovation in the coming weeks, months, years? With the pace of change of these models and harnesses... who can tell?!

## Supervisor Agent (GA)

> **What is it?** The Supervisor Agent in Agent Bricks is now GA. It's a routing layer that combines up to 20 different agents or tools — agent endpoints, Unity Catalog functions, Genie spaces, and external MCP servers — into a single conversational interface. You ask a question, it figures out which sub-agent to call.
>
> **Is it for you?** If your workspace has multiple specialized agents, Genie spaces, or tool endpoints and you want a single entry point that intelligently routes between them, this is it. No code required — configure it entirely through the UI.
>
> **Try it** Go to Machine Learning > Agent Bricks > Supervisor Agent. Select up to 20 agents or tools from your workspace, give it a system prompt, and deploy. Test it in the playground before serving.

An amazing tool for composing agents without touching a keyboard, CLI, or code. If your finding that your workspace has multiple useful genie spaces, agents, etc. ... combine them using this tool!!

## Metric Views — Window Functions and Filters

> **What is it?** Metric views — Databricks' semantic layer for defining how metrics are calculated — now support **window functions** (rolling averages, cumulative totals, trailing period counts) and **filter clauses in aggregate functions** (e.g., sum only women's events). There's also a new visual UI editor as an alternative to YAML definitions.
>
> **Is it for you?** If you use Genie spaces or need consistent metric definitions across your organization, metric views ensure everyone computes things the same way. Window functions and filters expand what you can define without writing one-off SQL.
>
> **Try it** Navigate to your catalog, find or create a metric view, and use the new UI editor to define measures with window functions. Connect the metric view to a Genie space for natural language querying.

Metric views are the tool to define your semantic layer with. Technically speaking they're not a new functionality, you could have always made other tables, views, etc. and just made a contract to treat those as the semantic layer. But, having these as 1st class entities in Databricks really makes that contract real and formal. Excellent feature broadly speaking, and the continuous expansion of the types of things you can define with these metric views means its something you can really trust.

## Multi-Statement Transactions (+ Delta Sharing)

> **What is it?** Execute multiple SQL statements against a single table as one atomic commit — no partial updates visible to readers. Now also works with Delta Sharing, meaning shared table consumers only ever see fully committed state.
>
> **Is it for you?** If you need to update and delete from the same table in a single logical operation (data corrections, end-of-period closings, conditional cleanup), this prevents anyone from seeing an intermediate state. Essential for shared datasets where consistency matters.
>
> **Try it** Wrap your statements in `BEGIN TRANSACTION` / `COMMIT`. Works in notebooks, SQL editor, and dbSQL. No configuration needed.

I really want multi TABLE transactions but I'll definitely settle for this milestone for now. There's not much to say here because as a feature in the warehouse ecosystem, it's well known. For Databricks users specifically it's been a painful gap and now it's CLOSED. Thank god. On to multi-table...

