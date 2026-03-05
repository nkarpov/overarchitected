---
title: "OverArchitected: February 2026"
date: 2026-02-04
subtitle: "Nick Karpov & Holly Smith"
youtube_id: "vzu06KGTOrQ"
sections:
  - heading: "New Connectors in LakeFlow Connect"
    timestamp: "0:36"
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
    docs:
      - label: "Create skills for Databricks Assistant"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2026/january#create-skills-for-databricks-assistant"
      - label: "Assistant on the documentation site"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#databricks-assistant-on-the-documentation-site"
      - label: "Assistant Agent Mode (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#databricks-assistant-agent-mode-is-now-in-public-preview"
  - heading: "forEachBatch() in Spark Declarative Pipelines"
    timestamp: "10:57"
    docs:
      - label: "forEachBatch for SDP (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#foreachbatch-for-lakeflow-spark-declarative-pipelines-is-available-public-preview"
  - heading: "Foundation Models — Claude 4.5, GPT 5.2, Haiku"
    timestamp: "15:38"
    docs:
      - label: "Claude Opus 4.5"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/november#anthropic-claude-opus-45-now-available-as-a-databricks-hosted-model"
      - label: "Claude Haiku 4.5"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#anthropic-claude-haiku-45-now-available-as-a-databricks-hosted-model"
      - label: "OpenAI GPT 5.2"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#openai-gpt-52-now-available-as-a-databricks-hosted-model"
  - heading: "Delta Sharing to Iceberg Clients"
    timestamp: "19:26"
    docs:
      - label: "Delta Sharing to external Iceberg clients (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#delta-sharing-to-external-iceberg-clients-is-in-public-preview"
  - heading: "Knowledge Assistant is GA"
    timestamp: "22:06"
    docs:
      - label: "Agent Bricks Knowledge Assistant GA"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2026/january#agent-bricks-knowledge-assistant-is-now-generally-available"
  - heading: "Lakebase Autoscaling"
    timestamp: "27:05"
    docs:
      - label: "Lakebase autoscaling (public preview)"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#lakebase-autoscaling-now-in-public-preview"
      - label: "Lakebase SQL editor read-write access"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#connect-to-lakebase-autoscaling-from-the-sql-editor-with-read-write-access"
      - label: "Lakebase autoscaling ACL support"
        url: "https://docs.databricks.com/aws/en/release-notes/product/2025/december#lakebase-autoscaling-acl-support"
---

This is the February episode — covering 60 days of releases because, as Holly put it, the holidays happened. The theme is Valentine's Day. Holly decides they should use Jira tickets to play matchmaker for Databricks employees. Nick goes along with it. An HR intervention is implied.

Oh and that little video floating in the corner? It follows you as you scroll. Each section jumps to that part of the episode automatically. Drag it around, resize it, toss it wherever you want.

## New Connectors in LakeFlow Connect

> The connectors team shipped eight new connectors over the holiday break: **Microsoft Dynamics 365** (public preview), **Jira**, **Confluence**, **Salesforce** (now with incremental loads), **Meta Ads**, **Excel file reading**, **NetSuite**, and **PostgreSQL**. Holly demos setting up the Jira connector — creating an app in the Atlassian developer console, configuring OAuth scopes, then wiring it up as a connection in Databricks.

> **In the architecture:** Jira data lands in a Delta table via the new connector. This becomes the raw data source for the Valentine's Day matchmaking app — profiles, tickets, comments, emoji reactions, everything you'd need to algorithmically determine romantic compatibility between coworkers.

Connectors are basically your lifeblood. Without them your workspace is DOA. We're iterating insanely fast here and this release just goes to show that. If you don't see a connector for your service... make some noise and we'll build it.

## Databricks Assistant — Skills, Agent Mode, and Docs

> Three updates to Databricks Assistant. First, it's now live on docs.databricks.com with a chat interface. Second, Agent Mode (the version that can interact with your workspace) is in public preview. Third, and most interesting: **skills** — an open standard originally from Anthropic, now open source. Skills are bundled instructions, scripts, and assets organized into folders that the agent can progressively discover and load, rather than dumping everything into context at once. Nick demos a Casper's trivia skill that dynamically loads when you ask about Casper's.

> **In the architecture:** Skills help the development team build the Jira matchmaking app more effectively — repo structure guidance, deployment patterns, things the assistant can learn incrementally rather than having it all front-loaded.

All the assistants. EVERYWHERE. And, now, with SKILLS.md. Personally I'm still on the fence about all the tooling in the harness world. MCP servers hosting tools, SKILLS.md, AGENTS.md, CLAUDE.md... it's exhausting. My personal favorite way to work right now is to use an extremely lightweight harness ([Pi agent!!](https://pi.dev)) with as few tools as possible with an extremely capable model (the latest, duh). This forces the model to use `bash` + CLI tool. This... works insanely well. The "are CLIs good enough?" debate continues to rage on X.

## forEachBatch() in Spark Declarative Pipelines

> A long-awaited addition. Previously, Spark Declarative Pipelines couldn't handle custom sinks, MERGE INTO operations, or anything requiring micro-batch control. Now `forEachBatch()` unlocks all of that — custom JDBC sinks, merge logic, and complex processing that previously forced you back to classic Spark Structured Streaming. Holly demos a pipeline that merges refund recommendations into a target table using the new sink syntax.

> **In the architecture:** The forEachBatch() sink writes matchmaking results out via JDBC to Cupid (who apparently lives in a cloud drawn as a heart). This is where the foundation models score compatibility and the results get pushed to the app layer.

This was actually my very first complaint when I saw DLT. After years in the field abusing forEachBatch() for every and any use case that didn't "fit the mold", to suddenly lose that ability in DLT was basically a non starter. In my view, this should have shipped Day 1. But, alas, here it is anyways. Amazing!

## Foundation Models — Claude 4.5, GPT 5.2, Haiku

> **Claude Opus 4.5**, **Claude Haiku 4.5** (Anthropic), and **GPT 5.2** (OpenAI) are now available through the Databricks Foundation Model API. Nick demos Claude Code pointed at Databricks-hosted Claude — showing the settings JSON with the workspace serving endpoint URL. He then shows inference tables capturing all his Claude Code conversations, and suggests mining those logs for common patterns to generate new skills or tools for the team.

> **In the architecture:** Foundation models power the matchmaking — analyzing Jira ticket writing styles, emoji usage, and organizational patterns to determine who's a "perfect couple." Nick draws a line from the Delta table through the FM layer into the Cupid app.

I'm backfilling this content so I'm writing this FROM THE FUTURE MARTY! Aka. 4.5 and 5.2 are OLD NEWS. Codex 5.3 and Opus/Sonnet 4.6 are absolutely bonkers good. Start using.

## Delta Sharing to Iceberg Clients

> Delta tables can now be shared to external Iceberg clients via Delta Sharing. Holly demos the setup: disable deletion vectors (not yet supported), enable Iceberg-compatible format on the table, then add it to a share. Any Iceberg client can now read it — whether self-hosted or on another platform.

> **In the architecture:** The matchmaking results get shared to HR (sorry, the "People Team") via Delta Sharing as Iceberg. Nick's commentary: "Human resources — cold as ice."

I worked very closely on the Delta project for a few years. All I can say is I'm sick of discerning the difference between these things. Delta? Iceberg? Diceberg? Icelta? Who cares. Databricks supports ACID like tables on top of blob storage. That's the point. This feature, among many others, is just nailing this coffin shut.

## Knowledge Assistant is GA

> The Knowledge Assistant in Agent Bricks is now generally available. It's essentially no-code RAG — point it at UC files or a vector search index and it builds a chatbot. Nick demos one built for Casper's Kitchens using the operations manual as the knowledge source. It handles queries with full citation (page references, excerpts). Available as a serving endpoint, usable in the playground, or as part of a multi-agent orchestrator.

> **In the architecture:** A Knowledge Assistant plugs into the agent layer, fed by a vector search index that's populated via forEachBatch(). It's part of the larger agent that powers the Cupid app.

As much as I'm obsessed with coding harnesses of late, I can't overlook how big this feature is. Anybody can point and click a smart knowledge assistant in a few minutes. We have a lot of demos now like [Casper's Kitchens](https://github.com/databricks-solutions/caspers-kitchens) that demonstrate exactly what the video shows. Try it!!

## Lakebase Autoscaling

> Lakebase (Databricks-managed Postgres) now supports autoscaling in public preview — including scale-to-zero. No more choosing capacity units. Also ships with ACL support and SQL editor read-write access. Holly demos spinning up a new instance from the new Lakebase UI, noting how fast it provisions.

> **In the architecture:** Lakebase is the operational database underneath the Cupid app (built with Databricks Apps). Data flows from the Delta table via reverse ETL into Lakebase, which serves the matchmaking results to the app. Nick: "This is the first time we've had the actual end user fully as the focus of our architecture."

The thing about Lakebase is it fills the final gap on Databricks: OLTP. Serverless Postgres, autoscaling, BRANCHING(!!)... all instant. This feature will take you (and us with you) to the moon. With this feature Databricks is totally end to end: data platform, apps, operational data stores... the future is building on Databricks.

## The Final Architecture

> ```
> [Jira Connector]
>     → Delta Table (tickets, profiles, comments, emojis)
>     → Spark Declarative Pipeline (forEachBatch):
>         → Foundation Models (Claude 4.5 / GPT 5.2): matchmaking scoring
>         → JDBC sink → Cupid (in the cloud/heart)
>         → Vector Search Index → Knowledge Assistant
>     → Delta Sharing as Iceberg → HR / People Team
>     → Reverse ETL → Lakebase (autoscaling)
>         → Cupid App (Databricks Apps)
>     ← Development Skills (repo structure, onboarding)
>     ← Claude Code + inference tables
> ```

## The Rating

> Nick: **8**. Holly calls it "a seven for architecture, minus 10 for use case." They agree it's the first time the architecture has a real end user — even if that user is a fictional deity in a heart-shaped cloud. Holly: "We'll get fired, but it's a 10 out of 10."
