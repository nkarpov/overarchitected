---
title: "OverArchitected: February 2026"
date: 2026-02-04
subtitle: "Nick Karpov & Holly Smith"
youtube_id: "vzu06KGTOrQ"
sections:
  - heading: "New Connectors in LakeFlow Connect"
    timestamp: "0:36"
    tag: "GA / Beta"
    docs:
      - label: "Jira connector (beta)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#jira-connector-beta"
      - label: "Confluence connector (beta)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#confluence-connector-beta"
      - label: "Microsoft Dynamics 365 (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#microsoft-dynamics-365-connector-public-preview"
      - label: "Salesforce incremental loads"
        url: "https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/salesforce-formula-fields"
      - label: "PostgreSQL connector (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#postgresql-connector-in-lakeflow-connect-public-preview"
      - label: "Meta Ads (beta)"
        url: "https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/meta-ads-source-setup"
      - label: "Read Excel files (beta)"
        url: "https://docs.databricks.com/aws/en/query/formats/excel"
      - label: "NetSuite connector"
        url: "https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/netsuite-source-setup"
  - heading: "Databricks Assistant — Skills, Agent Mode, and Docs"
    timestamp: "5:15"
    tag: "Public Preview"
    docs:
      - label: "Create skills for Databricks Assistant"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2026/january#create-skills-for-databricks-assistant"
      - label: "Assistant on the documentation site"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#databricks-assistant-on-the-documentation-site"
      - label: "Assistant Agent Mode (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#databricks-assistant-agent-mode-is-now-in-public-preview"
  - heading: "forEachBatch() in Spark Declarative Pipelines"
    timestamp: "10:57"
    tag: "Public Preview"
    docs:
      - label: "forEachBatch for SDP (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#foreachbatch-for-lakeflow-spark-declarative-pipelines-is-available-public-preview"
  - heading: "Foundation Models — Claude 4.5, GPT 5.2, Haiku"
    timestamp: "15:38"
    tag: "GA"
    docs:
      - label: "Claude Opus 4.5"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/november#anthropic-claude-opus-45-now-available-as-a-databricks-hosted-model"
      - label: "Claude Haiku 4.5"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#anthropic-claude-haiku-45-now-available-as-a-databricks-hosted-model"
      - label: "OpenAI GPT 5.2"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#openai-gpt-52-now-available-as-a-databricks-hosted-model"
  - heading: "Delta Sharing to Iceberg Clients"
    timestamp: "19:26"
    tag: "Public Preview"
    docs:
      - label: "Delta Sharing to external Iceberg clients (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#delta-sharing-to-external-iceberg-clients-is-in-public-preview"
  - heading: "Knowledge Assistant is GA"
    timestamp: "22:06"
    tag: "GA"
    docs:
      - label: "Agent Bricks Knowledge Assistant GA"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2026/january#agent-bricks-knowledge-assistant-is-now-generally-available"
  - heading: "Lakebase Autoscaling"
    timestamp: "27:05"
    tag: "Public Preview"
    docs:
      - label: "Lakebase autoscaling (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#lakebase-autoscaling-now-in-public-preview"
      - label: "Lakebase SQL editor read-write access"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#connect-to-lakebase-autoscaling-from-the-sql-editor-with-read-write-access"
      - label: "Lakebase autoscaling ACL support"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#lakebase-autoscaling-acl-support"
---

## New Connectors in LakeFlow Connect

> **What is it?** Eight new connectors for LakeFlow Connect: Microsoft Dynamics 365, Jira, Confluence, Salesforce (now with incremental loads and formula field support), Meta Ads, Excel file reading, NetSuite, and PostgreSQL. These are fully managed, no-code ingestion pipelines that land data directly into Delta tables.
>
> **Is it for you?** If you're currently running custom scripts or third-party ETL tools to get data from any of these sources into Databricks, this replaces all of that. Set up a connection, pick your tables, and data flows automatically with checkpointing and error handling.
>
> **Try it** Navigate to your workspace, go to Data Ingestion > LakeFlow Connect, and create a new connection. OAuth setup takes about 5 minutes for most connectors.

Connectors are basically your lifeblood. Without them your workspace is DOA. It's hard to believe I spent years of my life in the field implementing exactly these types of connectors, which can now be deployed with just a few clicks. We're iterating insanely fast here and this release just goes to show that. I don't expect any slowdown anytime soon! If you don't see a connector for your service... make some noise and we'll build it.

## Databricks Assistant — Skills, Agent Mode, and Docs

> **What is it?** Three updates. The Assistant now lives on docs.databricks.com as a chat interface. Agent Mode lets the Assistant interact directly with your workspace (run queries, create clusters, etc.) and is in public preview. And **skills** — an open standard from Anthropic — let you bundle instructions, scripts, and context into folders that the agent discovers progressively instead of loading everything at once.
>
> **Is it for you?** Agent Mode is for anyone who wants to operate their workspace conversationally. Skills are for teams who want to encode their specific workflows, patterns, and tribal knowledge so the Assistant can learn them incrementally.
>
> **Try it** Open any notebook and click the Assistant icon. For Agent Mode, toggle it on in the Assistant panel. For skills, create a `.skills/` folder in your repo with a `SKILLS.md` file describing available capabilities.

All the assistants. EVERYWHERE. Databricks assistant is taking over every surface area of the product and I love it. There's still some hard lines between this assistant and that assistant, but I think we all see where this is going, so, expect many more updates here in the coming months. For now, asking the assistant to "create a skill based on what we've done here" at the end of any piece of work is an absolute must.

As for me? I'm a CLI/TUI person and I'm still on the fence about all the tooling in the harness world. MCP servers hosting tools, SKILLS.md, AGENTS.md, CLAUDE.md... it's exhausting. My personal favorite way to work right now is to use an extremely lightweight harness ([Pi agent!!](https://pi.dev)) with as few tools as possible with an extremely capable model (the latest, duh). This forces the model to use `bash` + CLI tool. This... works insanely well. The "are CLIs good enough?" debate continues to rage on X. I ~think~ yes, but it's anyones guess how things evolve.

## forEachBatch() in Spark Declarative Pipelines

> **What is it?** Spark Declarative Pipelines (formerly DLT) now support `forEachBatch()` — giving you micro-batch control over how data is written. This unlocks custom sinks (JDBC, REST APIs), MERGE INTO operations, and any processing logic that needs to happen per-batch rather than per-record.
>
> **Is it for you?** If you've been stuck on classic Structured Streaming because SDP couldn't handle your write pattern (merges, upserts, external sinks), this is your ticket in. If your pipelines are already working with simple append/overwrite, you don't need this.
>
> **Try it** In your SDP pipeline definition, use the new `sink` parameter with a `forEachBatch` function. The syntax mirrors classic Structured Streaming's `forEachBatch` API.

This was actually my very first complaint when I saw DLT. After years in the field abusing forEachBatch() for every and any use case that didn't "fit the mold", to suddenly lose that ability in DLT was basically a non starter. If you've been stuck on classic Structured Streaming because of quirky SDP edges, it's time to take another look. This product has seriously matured.

## Foundation Models — Claude 4.5, GPT 5.2, Haiku

> **What is it?** Three new models on the Foundation Model API: Claude Opus 4.5, Claude Haiku 4.5 (both Anthropic), and GPT 5.2 (OpenAI). All available as Databricks-hosted endpoints — meaning you get inference tables, AI Gateway, PII detection, and usage tracking without any extra setup.
>
> **Is it for you?** If you're building AI features on Databricks (agents, RAG, structured extraction), these are the models to use. Hosting them through Databricks means your data stays in your environment and every call is logged and governable.
>
> **Try it** Available immediately in the AI Playground — no setup needed. For production use, enable AI Gateway (beta preview) on a foundation model endpoint to get inference tables, PII detection, rate limiting, and usage tracking.

I'm backfilling this content so I'm writing this FROM THE FUTURE MARTY! Aka. 4.5 and 5.2 are OLD NEWS. Codex 5.3 and Opus/Sonnet 4.6 are absolutely bonkers good. Start using. Check out our [March episode](/2026-03/) for the latest.

## Delta Sharing to Iceberg Clients

> **What is it?** Delta tables can now be shared to external consumers as Iceberg-formatted data via Delta Sharing. Any Iceberg-compatible client (Snowflake, Trino, Spark on another platform) can read your shared tables without needing Databricks.
>
> **Is it for you?** If you need to share data with partners or teams that aren't on Databricks but use Iceberg-compatible tools, this eliminates the need for data export/copy workflows. Your data stays in place; they read it live.
>
> **Try it** Enable Iceberg compatibility on your table (`ALTER TABLE SET TBLPROPERTIES ('delta.universalFormat.enabledFormats' = 'iceberg')`), then add it to a Delta Share. Note: deletion vectors must be disabled on the table.

I worked very closely on the Delta project for a few years. All I can say is I'm sick of discerning the difference between these things. Delta? Iceberg? Diceberg? Icelta? Who cares. Databricks supports ACID like tables on top of blob storage. That's the point. This feature, among many others, is just nailing the format wars coffin shut.

## Knowledge Assistant is GA

> **What is it?** The Knowledge Assistant in Agent Bricks is now generally available. It's a no-code RAG chatbot — point it at Unity Catalog files, volumes, or a vector search index, and it builds a question-answering agent with full citations (page numbers, source excerpts). Deployable as a serving endpoint.
>
> **Is it for you?** If your team has documentation, manuals, policies, or knowledge bases that people constantly ask questions about, this turns them into a searchable, conversational interface in minutes. No ML expertise required.
>
> **Try it** Go to Machine Learning > Agent Bricks, select Knowledge Assistant, upload your documents or point to a UC volume, and deploy. You'll have a working chatbot with citations in under 10 minutes.

As much as I'm obsessed with coding harnesses of late, I can't overlook how big this feature is. Anybody can point and click a smart knowledge assistant in a few minutes. So, either let your users build their own knowledge assistants, or spend the 5 minutes it takes to create one and expose it to them ASAP. We have a lot of demos now like [Casper's Kitchens](https://github.com/databricks-solutions/caspers-kitchens) that demonstrate exactly what the video shows. Try it!!

## Lakebase Autoscaling

> **What is it?** Lakebase — Databricks-managed PostgreSQL — now supports autoscaling in public preview, including scale-to-zero. No more manually choosing capacity units. It also ships with ACL support for fine-grained access control and read-write access from the SQL editor.
>
> **Is it for you?** If you need an operational database for serving applications, APIs, or low-latency lookups on top of your lakehouse data, Lakebase is the native answer. Autoscaling means you pay for what you use and don't manage infrastructure.
>
> **Try it** In your workspace, go to SQL > Lakebase and create a new instance. It provisions in seconds. Connect from any Postgres-compatible client or use the built-in SQL editor.

OLTP on Databricks is something many users have wanted for a very long time. I've been waiting for it since the first time I wanted to serve a Delta table live from Databricks. Now with a simple few clicks (or one API call) I can synchronize my data directly into application databases. Lakebase is serverless, autoscaling, and instant... frankly it exceeds what I could have imagined years ago. My favorite feature is git style branching. This means I can basically use production data directly in my dev environment at almost no cost. The bigger picture around Lakebase: Databricks is now totally end to end. Data platform, apps, operational data stores... the future is building on Databricks.

