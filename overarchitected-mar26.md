# OverArchitected: March 2026 Recap

I've been thinking about how to write with LLMs without... writing with LLMs. The problem with editing machine-generated text is that you end up smoothing out your own voice to match theirs, or smoothing out theirs to match yours, and either way you get this uncanny middle ground that sounds like neither of you.

So here's the experiment: I fed the transcript from this month's OverArchitected episode to Claude Opus and let it summarize each section. I didn't edit a single word of its output. Instead, I just respond to it — in my own voice, completely unedited. The machine does the recap, I do the commentary. You'll see which is which.

---

> **Opus:** *The podcast where Nick and Holly talk about new Databricks features and shoehorn them into one architecture to see if it's actually realistic. This month's theme: The 2026 Winter Olympics. Every feature gets wired into an architecture for ingesting and making sense of Olympic data.*

---

## The Thumb Incident

> **Opus:** *Nick sliced off a piece of his thumb cooking, calmly Tupperwared it with ice, and went to the hospital. His wife nearly tossed the container thinking it was leftovers. Doctors couldn't save it. Holly: "would you give this a whole thumbs up or 0.9 of a thumbs up?"*

I don't have much to say to this. It's true. It happened. The thumb is recovering quite well.

---

## Feature 1: Autoloader File Events — Now Automatic

> **Opus:** *Autoloader handles data ingestion with built-in checkpointing. Previously, setting up file events (SQS on AWS, ADLS queues on Azure) for event-driven ingestion was a manual pain. Now when you create an external location in Unity Catalog, Databricks automatically provisions the cloud resources. Event-driven ingestion out of the box, on both clouds.*
>
> *In the architecture: Olympic data from all venues and sensors lands via Autoloader into bronze.*

Autoloader is now mature enough that I can admit I didn't really understand what the hype was all about when we first released it. It's just Spark Structured Streaming with a file based source, right? Wrong. It's much faster than file based sources. All thanks to the file events queue. Now Databricks can orchestrate all that for you, even if it's an external location. It really goes to show you the power of iterating under an API surface area.

---

## Feature 2: New Foundation Models on Databricks

> **Opus:** *Three new models on the Foundation Model API: Claude Opus 4.6, Claude Sonnet 4.6 (both Anthropic), and Gemini 3.1 Pro (Google). Serving them through Databricks gets you instrumentation, inference tables, AI gateway, and PII detection out of the box.*
>
> *In the architecture: A three-model pipeline for bronze-to-silver. Sonnet (cheap) categorizes raw data by sport. Opus (smarter) checks data quality — flags outliers like curling at 100mph. Gemini sub-categorizes further (athlete vs. audience vs. venue data).*

I've since tried Sonnet, and it's great, but, once you get a taste for the best models... why bother changing? For daily driving I think you want the best model possible - you can always optimize once you have specific workloads that require some LLM endpoint (whole other ball game). I **still** haven't tried Gemini but I did see a tweet that said something like "Gemini is beating everyone in the benchmarks and still nobody uses it". That made me laugh. Also, as an aside, I actually personally prefer codex 5.3 these days but our internal tooling is currently Claude Code... so, Claude for work, Codex for pleasure.

---

## Feature 3: Stateless Streaming Performance Improvements

> **Opus:** *Stateful streaming has gotten all the love recently — now stateless gets some too. AQE (adaptive query execution), dynamic shuffle partition adjustment, and auto-optimized shuffle are all now available in stateless streaming. No configuration needed.*
>
> *Holly and Nick debate whether this matters when you're calling AI models in a stream. Nick argues the FM-powered categorization creates naturally skewed partitions (hockey finals >> curling), so AQE absolutely applies. Holly concedes but is not thrilled about being "lectured about my own feature."*

LOL. Thank you Holly, as always, for putting up with me :). As for real time streaming and performance... this is a REAL sleeper. Ali's been hammering this point on LI: Spark is now as good and in many places better than the other streaming engines. If you have stuff in Flink or w/e else, but you have access to Databricks... stop doing that!

---

## Feature 4: MLflow Traces to Delta via Unity Catalog

> **Opus:** *MLflow experiment traces can now sync directly to a Delta table in Unity Catalog. One click in the Experiments UI, pick a catalog/schema, and a sync pipeline is auto-created. Traces become a queryable, shareable table — no longer trapped in the Experiments page.*
>
> *Holly: "I am a sucker for anything that just puts data in a delta table for me."*

Our trace story has been evolving. We've gone through a few iterations where one way or another traces have become available in UC. This integration isn't functionally new, but with respect to the platform I think we've found a good place for this to live. Tracing is a really hot subject... if you're on X, you've probably seen how basically anyone using an agent is self-rolling a tracing solution for both themselves and their teams. This is going to be a wild area for innovation in the coming weeks, months, years? With the pace of change of these models and harnesses... who can tell?!

---

## Feature 5: Supervisor Agent (GA)

> **Opus:** *The Supervisor Agent in Agent Bricks routes requests across up to 20 agents or tools — agent endpoints, UC functions, Genie spaces, MCP servers. Ask it a question and it figures out which sub-agent to call. Nick demos one for Casper's Kitchen that federates across two knowledge assistants and a Genie space.*
>
> *Nick prefers "router" over "orchestrator" — it's not infra, it's intelligence.*

An amazing tool for composing agents without touching a keyboard, CLI, or code. If your finding that your workspace has multiple useful genie spaces, agents, etc. ... combine them using this tool!!

---

## Feature 6: Metric Views — Window Functions and Filters

> **Opus:** *Metric views are Databricks' semantic layer — defining how metrics are calculated so humans and Genie spaces agree. New additions: window functions (rolling averages, cumulative totals), filter clauses in aggregates, and a visual UI editor (previously YAML-only). Holly discovers the UI live and is visibly pleased. Nick is slower to react.*
>
> *Metric views + Genie spaces = natural language queries that actually compute things correctly.*

Metric views are the tool to define your semantic layer with. Technically speaking they're not a new functionality, you could have always made other tables, views, etc. and just made a contract to treat those as the semantic layer. But, having these as 1st class entities in Databricks really makes that contract real and formal. Excellent feature broadly speaking, and the continuous expansion of the types of things you can define with these metric views means its something you can really trust.

---

## Feature 7: Multi-Statement Transactions (+ Delta Sharing)

> **Opus:** *Multiple SQL statements against a single table, one atomic commit. Now works with Delta Sharing — readers only ever see fully committed state. Not to be confused with multi-table transactions (coming soon, possibly in private preview).*

I really want multi TABLE transactions but I'll definitely settle for this milestone for now. There's not much to say here because as a feature in the warehouse ecosystem, it's well known. For Databricks users specifically it's been a painful gap and now it's CLOSED. Thank god. On to multi-table...

---

## The Final Architecture

> **Opus:**
> ```
> [2026 Olympics Data]
>     → Autoloader (with auto file events)
>     → Bronze (raw, unstructured)
>     → Streaming pipeline (with AQE/dynamic partitions):
>         → Sonnet 4.6: categorize by sport
>         → Opus 4.6: data quality / outlier detection
>         → Gemini 3.1 Pro: sub-categorize (athlete vs audience vs venue)
>     → Silver (categorized, validated)
>         ← MLflow trace logging (synced to Delta via UC)
>         ← Manual intervention via multi-statement transactions
>         ← Metric views (window functions, filtered aggregates)
>     → Supervisor Agent routes across:
>         - Knowledge Assistant
>         - Genie Space (with metric view context)
>         - MCP Server
>         - Custom agent endpoints
>     → Gold
> ```

---

## The Rating

> **Opus:** *Nick: 7. Holly: 8. Final answer: 1.9 thumbs up.*

---

*Hated this podcast? Why not replace us with an RSS feed: [Databricks Release Notes](https://docs.databricks.com/aws/en/release-notes/)*
