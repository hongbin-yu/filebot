# RFP Technical Proposal: Next-Generation Content Management Platform for Canada.ca

> **Proposed by:** Yuhong Web Inc. (incorporated July 12, 2017)
> **Prepared for:** Government of Canada — Procurement RFP (July)
> **Version:** 1.0
> **Date:** 2026-06-04
> 
> **A Verifiable Proposal**
> 
> Every capability described in this document can be **demonstrated live, inspected, and validated** prior to any commitment.
> 
> **Yuhong Web Inc.**, incorporated in July 2017, has been operating continuously since its establishment. FileBot — the asset management engine — is a mature system with **5 active users across US-based organizations**. WebBot, the content management layer, represents the latest AI-augmented addition to an established platform.
> 
> **This proposal is submitted on the basis of demonstrable capability rather than promise. All claims herein are subject to independent verification.**
> 
> Systems operational today:
> - Content management (WebBot) — running on intranet
> - Asset management & AI (FileBot) — running on internet cloud
> - Publish preview — running on intranet
> - PostgreSQL with pgvector — running on intranet
> - **29,304 Canada.ca pages** already imported and indexed for semantic search
> - AI Q&A with both OpenAI (cloud) and Ollama/Phi3 (local) — live
- **Verified**: local Phi3 produces superior results to OpenAI for Canada.ca content Q&A — see [§3.3](#33-semantic-search--ai-qa)

---

## Executive Summary

Canada.ca operates on Adobe AEM, a platform selected over a decade ago for a world without modern search, AI. Today, that architecture presents well-known challenges: **$Millions in annual total costs**, **a delay publish pipeline**, **difficult to migrate new department of content**, and **no native database, search, or AI capabilities** — all of which must be outsourced to separate vendors.

Yuhong Web Inc. proposes a fundamentally different approach — not a speculative proposal for a future system, but a **fully functional, verifiable platform** operating today:

> **Designed from 20 years of Canada.ca experience. Developed by a compact, AI-empowered team. Verifiable on demand. Operationally proven.**

Our platform comprises two integrated systems — **WebBot** (intranet content management, AI-augmented) and **FileBot** (mature asset management and delivery system, under continuous development since 2017 with active deployments) — that together constitute a complete, secure, and cost-effective content management platform.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Core Capabilities](#3-core-capabilities)
4. [Comparative Analysis: Our Platform vs. AEM](#4-comparative-analysis)
5. [Migration Strategy](#5-migration-strategy)
6. [Security & Compliance](#6-security--compliance)
7. [Cost Model](#7-cost-model)
8. [Team & Delivery](#8-team--delivery)
9. [Future Roadmap](#9-future-roadmap)
10. [Risk Mitigation](#10-risk-mitigation)

---

## 1. System Overview

### 1.1 Philosophy

Canada.ca's current platform, Adobe AEM, was the right choice when it was selected over a decade ago. It brought enterprise-grade content management to government at a time when the alternatives were far less mature. However, the technology landscape has changed. Modern content management needs — AI-assisted search, semantic understanding, real-time publishing, small-team agility — are not capabilities AEM was designed for.

Our approach is designed for today's content management needs:

| Principle | Application |
|---|---|
| **No lock-in** | Open-source stack, standard formats (HTML, Mustache, PostgreSQL) |
| **AI-augmented** | AI-assisted component creation, semantic search, LLM Q&A |
| **Zero transformation** | HTML in → HTML out. No component mapping, no serialization |
| **Compact, AI-empowered team** | 20 years of domain expertise augmented by AI tooling yields a focused, efficient team |
| **Progressive adoption** | Start with one department, expand organically |

### 1.2 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Intranet                                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  WebBot (Internet Content Management System)             │   │
│  │  ────────────────────────────────────────────            │   │
│  │  • HTML Visual Editor (WYSIWYG)                         │   │
│  │  • Mustache Template Engine                              │   │
│  │  • Component Library (GCWeb + WET full coverage)         │   │
│  │  • AI Q&A Interface                                      │   │
│  │  • Version Management & Publishing                        │   │
│  │  • User & Permission Management                          │   │
│  │  • Search Index Management                                │   │
│  │                                                           │   │
│  │  Data: SQLite + PostgreSQL (internal, safe)              │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                          │                                      │
│                          │ Publish / Sync                       │
                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FileBot (Assets Management System)                      │   │
│  │  ────────────────────────────────────────────            │   │
│  │  • File Storage & Delivery                               │   │
│  │  • File Migration & Format Conversion                    │   │
│  │  • Document Management (upload/download/preview)         │   │
│  │  • File Naming Rules Engine                              │   │
│  │  • Multi-format Conversion (PCL→PDF, TIFF→JPG, etc.)    │   │
│  │  • Device & Storage Management                          │   │
│  │                                                           │   │
│  │  Can run as: Internal service OR Public server             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                 │
│                                                                  │
│  CDN → Load Balancer → 2× Replicated Publish Servers            │
│                                                                  │
│  Static HTML files served directly — no application layer       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Backend** | Python / FastAPI | Modern, async, type-safe, lightweight |
| **Database** | PostgreSQL 15 + pgvector | Relational + vector search in one system |
| **Vector Embeddings** | e5-small (384-dim) | Efficient multilingual semantic search |
| **LLM (Cloud)** | OpenAI API | Cost-effective, fast, high quality |
| **LLM (Local)** | Ollama + Phi3 | Air-gapped option, no data leaves premises |
| **Templates** | Mustache (Chevron) | Logic-less templates — no code injection possible |
| **Editor** | ACE Editor | WYSIWYG, real-time preview |
| **Frontend** | Static HTML/CSS/JS (GCWeb + WET) | Canada.ca standards, no framework lock-in |
| **Publishing** | Static HTML output | CDN-ready, no application server needed |

---

## 2. Architecture

### 2.1 Security Architecture

**WebBot runs on intranet only** — no public exposure. All editorial work, content databases, and version histories remain securely behind the government firewall.

```
Internet (public)           DMZ                    Intranet (internal)
┌─────────────┐       ┌──────────────┐        ┌─────────────────┐
│ Users        │       │ CDN + LB    │        │ WebBot Editor    │
│ (citizens)   │ ←──→ │              │ ←────→ │ (staff only)    │
│              │       │ Publish Srv  │        │                  │
│ Static HTML  │       │ (static)    │        │ PostgreSQL       │
│ served via   │       │              │        │ Mustache Engine  │
│ CDN          │       │ FileBot      │        │ AI Q&A Engine    │
└─────────────┘       └──────────────┘        └─────────────────┘
```

> **Data sovereignty advantage**: Our architecture gives GC stronger data control than any cloud-only solution. The editorial server (WebBot + PostgreSQL) is deployed **inside the government's own network** — editors' content, drafts, version history, and metadata never leave government infrastructure. Only **public, publish-ready HTML** is pushed to the cloud CDN. This means:
>
> - **GC physically retains all content data** — no third-party cloud provider holds editorial data
> - **Zero data egress from government network** for administrative operations
> - **Citizen-facing content** (static HTML on CDN) is inherently public — no data sovereignty risk
> - Exceeds the RFP's "data stored in Canada" requirement by keeping data **in the government's own data centre**
> - No CCCS cloud certification required for the editorial layer — it never touches public cloud

### 2.2 Environment Architecture: Preserving the 4-Tier Standard

Canada.ca currently operates a **4-tier environment structure**:

```
Dev → QA → Stage → Publish (Production)
```

Our system **preserves this proven model** but dramatically reduces the operational burden:

| Layer | AEM Workload | Our Workload |
|---|---|---|
| **Dev** | Full AEM instance + JCR setup | Lightweight dev server, git-based |
| **QA** | Full AEM instance + testing | Automated test runner + preview |
| **Stage** | Full AEM instance + replication | Lightweight stage server |
| **Publish** | AEM Publish instance and replication | Static file servers (existing infrastructure) |

**Operational Efficiency Rationale:**
- Without JCR, no AEM instance requires deployment per environment
- Configuration is code (git-tracked) rather than JCR nodes
- Each environment runs identical WebBot and FileBot instances — no special licensing required
- Environment promotion is git-based (merge, deploy, test) rather than replication-based
- **Result**: Equivalent 4-tier quality assurance, deployable by a single individual rather than a team

### 2.3 AI-Assisted System Maintenance

**Current challenge — fully manual maintenance:**
- Server updates, security patches, and configuration changes are all performed manually
- Each upgrade carries risk of human error (incorrect configuration, missed steps, version mismatches)
- Reliance on specific individuals with institutional knowledge of system operations
- No systematic audit trail for infrastructure changes

**Proposed approach — human oversight, AI execution:**

```
Human defines intent: "Update PostgreSQL to latest patch version"
         │
         ▼
AI plans the change: dependency check, backup, upgrade steps, rollback plan
         │
         ▼
Human reviews & approves the plan
         │
         ▼
AI executes: runs commands, verifies success, rolls back if failed
         │
         ▼
Full audit log generated for compliance
```

| Maintenance Task | Manual (AEM) | AI-Assisted (Our System) |
|---|---|---|
| Security patching | Human identifies, tests, deploys | AI scans, plans, executes with human approval |
| Configuration changes | Human edits files, risk of typographical errors | AI follows configuration-as-code, validates syntax |
| OS / dependency updates | Human schedules and may miss critical updates | AI monitors CVEs, proposes and applies updates |
| Backup verification | Human manually checks logs | AI verifies backups and reports status |
| Incident response | Human on-call, extended diagnosis time | AI triages, suggests root cause, common fixes applied automatically |

**Primary benefit: reduction in human error.**
- AI avoids typographical mistakes
- AI does not skip steps in multi-step procedures
- AI documents every action for audit purposes
- Human operator retains authority — reviews and approves all critical changes
- Routine maintenance completed in **minutes rather than hours**

### 2.4 Publish Pipeline

```
Editor saves / publishes
       │
       ▼
Static HTML generated (1-2s)
       │
       ▼
rsync/scp to 2× Publish Servers (<1 min)
       │
       ▼
CDN cache invalidation
       │
       ▼
Users see updated content (~3-5 min total)

vs. AEM: ~2 hours
```

### 2.5 Proxy Chain for AI Q&A

To securely expose AI services without directly exposing the intranet:

```
User Browser (Internet)
       │
       ▼
WebBot (Intranet, port XXXX)
       │
       ├── Auth check → OK
       │
       ▼
FileBot AI (port XXXX)
       │
       ├── OpenAI API (cloud, via HTTPS)
       │   └── OR Ollama (local, CPU only)
       │
       ▼
Response returned to user
```

### 2.6 Dual-Database Architecture: Two Databases, One Import Flow

Our platform runs **two independent databases** by design — not as a technical compromise, but as a deliberate architectural choice:

| System | Database | Purpose |
|---|---|---|
| **WebBot** (intranet) | SQLite | Editorial content — pages, templates, versions, users, permissions |
| **FileBot** (assets) | PostgreSQL + pgvector | Asset storage, full-text search, vector embeddings, AI pipeline, file metadata |

**Why two databases?**

- **Separation of concerns.** Editorial activity (drafts, publishing, version diffs) happens entirely in SQLite on the intranet. AI indexing, semantic search, batch file conversion all happen in PostgreSQL. A failed vector embedding job never blocks an editor from publishing.
- **Different access patterns.** SQLite is optimized for the editorial workflow — fast point-reads, atomic writes, simple schemas. PostgreSQL handles the AI/search pipeline — complex JOINs, vector similarity search, large batch operations.
- **Security boundaries.** FileBot's PostgreSQL may serve both intranet and public-facing services (AI Q&A, search). WebBot's SQLite is strictly intranet-only. If a public endpoint is compromised, editorial data is never exposed.
- **Operational independence.** Each system can be upgraded, patched, or scaled independently. AI pipeline upgrades do not require editorial downtime.

#### 2.6.1 The Dual-Write Import Pipeline

A single publisher action — saving or publishing a page — triggers writes to both databases:

```
Publisher / Import
       │
       ├──→ FileBot (PostgreSQL) ←┐
       │     • Store raw HTML      │
       │     • Index for search    │
       │     • Generate embedding  │
       │                           │
       └──→ WebBot (SQLite)       │
             • Store editorial    │
             • Version tracking   │
             • User permissions   │
                                    │
       [Import via bookmarklet] ────┘
         (writes to both at once)
```

**The bookmarklet import flow (verified with 29,304 pages):**

1. User clicks bookmarklet on a Canada.ca page → browser sends the page's raw HTML to FileBot's import endpoint
2. FileBot stores the HTML file, registers it in PostgreSQL (folder tree, metadata, timestamps)
3. FileBot automatically pushes the same content to WebBot via REST API (`POST /api/v1/pages/`)
4. WebBot creates the page in its own database — ready for WYSIWYG editing immediately
5. A **path transformation rule** normalizes the path: FileBot stores at `/boarding/canadasite/...`, WebBot receives at `/canadasite/...` (the `/boarding` prefix is stripped)

**Key characteristics:**
- **Skip-if-exists:** Duplicate imports are silently handled — the second write is a no-op, not an error
- **Token-authenticated cross-system calls:** FileBot authenticates to WebBot using short-lived JWT tokens, refreshed every 50 API calls
- **Non-blocking:** A WebBot push failure (e.g., temporary downtime) never prevents the primary FileBot write from succeeding — logged for retry
- **Bulk backfill proven:** 29,304 existing FileBot pages were backfilled to WebBot in under 6 minutes — ~80-90 pages/second, zero failures

> **Design Rationale:** This dual-write architecture represents an optimal trade-off. A single monolithic database, while conceptually simpler, introduces tight coupling between editorial and AI workloads. Two databases with a reliable synchronization layer provide independent scaling and operational isolation. The additional complexity of the dual-write pattern is fully encapsulated within a single function in the import router — the remainder of the system operates without awareness of the dual-database architecture.

### 2.7 Path Architecture: How URLs Map to Storage

Every page in our system has a clear, predictable path mapping:

| Layer | Example Path |
|---|---|
| **Canada.ca URL** | `https://www.canada.ca/en/service-canada/page.html` |
| **FileBot folder** | `/boarding/canadasite/en/service-canada` |
| **FileBot document** | `/boarding/canadasite/en/service-canada/page.html` |
| **WebBot page path** | `/canadasite/en/service-canada/page.html` |
| **File on disk** | `data/boarding/canadasite/en/service-canada/page.html` |

The `boarding` app acts as a parent container for all imported Canada.ca content. The `/boarding` prefix is an organizational boundary — stripped when publishing to the public-facing WebBot. This design ensures:
- Multiple import sources coexist without path conflicts
- Departments maintain ownership boundaries
- The public-facing path (`/canadasite/...`) stays clean
- Internal storage structure is independent of the public URL structure

---

### 2.8 On-Premise AI Architecture — The Right Model for Government AI

**Cloud AI has no architectural advantage for government content workloads.** The landscape has shifted significantly since 2020:

- Open-source models (Llama 3, Phi-3, Qwen, Mistral) now run on **single GPU servers** — no cloud GPU cluster needed
- On-premise models deliver **equivalent or better accuracy** for government-specific content (proven: Phi3 outperforms GPT-4 on Canada.ca Q&A)
- Cloud AI services add **per-token cost, latency, data egress risk, and vendor lock-in** — none of which benefit government content operations
- The value of cloud AI today is **convenience, not capability** — and convenience does not justify data sovereignty exposure

#### Our Architecture

```
Government Intranet
┌──────────────────────────────────────────┐
│                                          │
│  🖥️ Dedicated AI Server (GPU)            │
│  ┌────────────────────────────────┐      │
│  │ Ollama / vLLM                  │      │
│  │   └── Llama 3 70B              │      │
│  │   └── Phi-3 / Qwen2            │      │
│  │   └── e5 embedding model       │      │
│  └──────────┬─────────────────────┘      │
│             │                            │
│             ▼ Local API (no internet)    │
│  ┌────────────────────────────────┐      │
│  │ FileBot AI Services            │      │
│  │   • Semantic search (pgvector) │      │
│  │   • AI Q&A                     │      │
│  │   • Content classification     │      │
│  │   • Auto-tagging               │      │
│  └──────────┬─────────────────────┘      │
│             │                            │
│             ▼                            │
│  ┌────────────────────────────────┐      │
│  │ WebBot Editor (intranet)       │      │
│  │   • AI-assisted writing        │      │
│  │   • AI Q&A interface           │      │
│  │   • Semantic search            │      │
│  └────────────────────────────────┘      │
└──────────────────────────────────────────┘
     ┌────── No internet egress ──────┐
     │   Zero data leaves premises    │
     └────────────────────────────────┘
```

#### Why Cloud AI Is Not the Answer for Government

| Aspect | Cloud AI (Competitors) | On-Premise AI (Our Approach) |
|---|---|---|
| **Data egress** | All queries leave govt network | Zero — all data stays on-premise |
| **Per-query cost** | $0.01–$0.10 per query | Fixed hardware cost, near-zero marginal cost |
| **Latency** | 500ms–5s (network round-trip) | 50–200ms (local inference) |
| **Model choice** | Provider-determined | Free choice of any open-source model |
| **Vendor lock-in** | Locked to AWS/Azure/GCP AI | No dependency — swap models anytime |
| **Accuracy** | General-world knowledge, less precise for govt content | Domain-tuned, verifiable, higher accuracy for Canada.ca content |
| **Offline resilience** | Requires internet connection | Works without any internet |
| **CCCS certification** | Requires cloud cert | No cloud cert needed — hardware in govt data centre |

> **Bottom line**: The RFP's requirements for cloud-based AI services reflect an assumption from 2020 — that only cloud providers can run modern LLMs. By 2026, this assumption is obsolete. Dedicated on-premise GPU servers deliver better security, lower cost, and higher accuracy for government content workloads.

### 2.9 Infrastructure Requirements — Entire Canada.ca on 2 TB

Canada.ca has approximately **2,000,000 pages and 2,000,000 images**. The total storage required to host, edit, index, and serve this content is surprisingly modest:

| Component | Estimated Size | Notes |
|---|---|---|
| All HTML pages | ~100 GB | ~50 KB/page (GCWeb average) |
| All images (original) | ~400 GB | ~200 KB/image average |
| Thumbnails + resized copies | ~200–500 GB | Multi-resolution cache |
| PostgreSQL (metadata + full-text + vector) | ~40 GB | 2M pages × 3 KB + embedding indices |
| AI models (local GPU server) | ~50 GB | Llama 3 70B + Phi-3 + embedding model |
| OS + applications + logs | ~50 GB | Ubuntu/Docker + app code |
| **Production total (single copy)** | **~900 GB – 1.2 TB** | **Fits on one 2 TB NVMe** |

**2 TB NVMe SSD** is sufficient for the entire Canada.ca content corpus — all pages, images, database, AI models, and system software — on a single production server. With a second 2 TB drive for RAID 1 mirroring, total hardware cost is under $5,000 CAD.

#### Comparison: Infrastructure Cost

| Item | AEM | Our Platform |
|---|---|---|
| Production servers | 4+ AEM instances (Author × 2, Publish × 2) — each with 1-2 TB JCR | 1 server (2 TB NVMe) + 1 GPU server (AI) |
| Licensing | ~$2-5M/year (perpetual/SaaS) | $0 (open source stack) |
| System integrator fees | $1-5M for migration alone | $0 (built-in migration) |
| Cloud infrastructure | AEM Managed Services or AWS/Azure | Optional — or entirely on-premise |
| 10-year growth buffer | Requires additional AEM instances | Add 1 more 2 TB SSD (~$300) |

> **Canada.ca's entire content footprint fits on a single consumer-grade SSD.** AEM's infrastructure costs are not driven by content volume — they are driven by a heavyweight Java application server architecture that requires multiple instances, JCR repositories, and ongoing licensing regardless of how much content is stored. Our platform eliminates those costs entirely.

### 2.10 Distributed Deployment — Per-Department Instances + Geo-Load Balancing

A single CMS instance serving all of Canada.ca creates a bottleneck and a single point of failure. Our architecture supports **distributed, per-department deployment** where each department's content lives on its own server — inside its own intranet.

#### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Public Internet  │     │ Service Canada   │     │  ISED            │
│                  │     │ (Large dept)     │     │  (Large dept)    │
│ Users →          │     │ ┌──────────────┐│     │ ┌──────────────┐│
│ CDN + Geo-LB     │     │ │ WebBot       ││     │ │ WebBot       ││
│   ↕              │     │ │ (dept intranet)││     │ │ (dept intranet)││
│ ┌──────────────┐ │     │ │ PostgreSQL   ││     │ │ PostgreSQL   ││
│ │ Publish Srv 1 │ │     │ │ GPU AI Srv  ││     │ │ GPU AI Srv  ││
│ │ (CDN)        │ │     │ │              ││     │ │              ││
│ └──────────────┘ │     │ Data stays in  ││     │ Data stays in  ││
│ ┌──────────────┐ │     │ Service Canada ││     │   ISED network  ││
│ │ Publish Srv 2 │ │     └──────────────┘│     └──────────────┘│
│ │ (geographic)  │ │                        ┌──────────────────┐
│ └──────────────┘ │     │ Small Depts   │     │ Shared Server  │
└─────────────────┘     │ (Shared)      │     │ ┌────────────┐ │
                         │ ┌────────────┐│     │ │ DFO        │ │
Public CDN (static       │ │ CRA        ││     │ │ HC         │ │
HTML only)               │ │ DND        ││     │ │ AAFC       │ │
                          │ │ Shared GPU ││     │ │            │ │
                          │ └────────────┘│     │ └────────────┘ │
                          └───────────────┘     └────────────────┘
```

#### Key Properties

| Property | What It Means |
|---|---|
| **Data locality** | Each department's content never leaves its own network — even from other parts of government |
| **Independent scaling** | A large department (Service Canada, CRA, ESDC) gets dedicated hardware; smaller departments share cost-effectively |
| **No single point of failure** | One department's server outage does not affect others |
| **Geo-load balancing** | Publish servers deployed in multiple regions — users served from nearest geographic CDN node |
| **Unified management** | Administrative UI shows all instances in one dashboard — deploy, monitor, update from a single console |
| **Gradual rollout** | Start with one department, add more without touching existing deployments |
| **Disaster recovery** | Cross-region replication at the publish layer — if one region fails, another takes over |

#### Deployment Scenarios

| Scenario | Configuration |
|---|---|
| Small department (~10 editors, <50K pages) | Single shared server with 5-10 departments, 4 TB NVMe |
| Medium department (~50 editors, 100K-500K pages) | Dedicated server per department, 2 TB NVMe + 1 GPU |
| Large department (~200+ editors, 500K-2M pages) | Clustered deployment: 2 editor servers (HA) + 1 GPU server + regional publish servers |
| Pilot / PoC | Single server (laptop or VM) — editor + AI + publish all on one machine, no cloud needed |

> **This is not theoretical.** Our system is already running on a single server at home. The same software, configured for distributed deployment, scales from a laptop PoC to a multi-department production deployment without code changes — only configuration.

### 2.11 Hosting Architecture — Akamai + AWS + On-Premise

Canada.ca's current hosting model — **Akamai CDN** for public delivery — is already the right architecture for performance, security, and global reach. Our platform is designed to plug into this exact model, replacing only the software layer:

```
┌─────────────────────────────────────────────────────────────┐
│  Akamai CDN (Edge)                                          │
│  ────────────────────────────                               │
│  • 4,000+ edge nodes, global acceleration                   │
│  • Petabit-scale DDoS protection                            │
│  • Origin Shield reduces back-end load                      │
│  • Already serving Canada.ca — zero architectural change     │
│  • Cost: $160K/yr (existing contract, no change)            │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼ origin-pull
┌─────────────────────────────────────────────────────────────┐
│  AWS Cloud (Public Layer)                                   │
│  ──────────────────────────────                             │
│  • S3: Static HTML + asset storage, serves as Akamai origin │
│  • EC2 (optional): Publish server for sitemap/cache refresh │
│  • No application server — static files only                │
│  • Auto-scales with demand (cache miss rate: 1-5%)          │
│  • CCCS Medium-assessed (AWS already has GC certification)  │
│  • Estimated cost: ~$10K-14K/yr                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼ rsync over encrypted tunnel
┌─────────────────────────────────────────────────────────────┐
│  Government Intranet (On-Premise)                           │
│  ─────────────────────────────────────                      │
│  • WebBot CMS: editorial interface                          │
│  • FileBot: asset management + AI processing                │
│  • PostgreSQL: all databases                                │
│  • GPU server: local AI models (Phi3, e5-small)             │
│  • AI Butler: automated operations                          │
│  • 🔒 Zero public DNS, zero public IP, no internet exposure │
└─────────────────────────────────────────────────────────────┘
```

#### Why This Architecture Works for Canada.ca

| Layer | Current (AEM) | Our Platform | Change Required |
|-------|---------------|-------------|-----------------
| **Akamai CDN** | Already serving Canada.ca | Same — content origin changes only | **Configuration only** |
| **Cloud** | AEM publish instances on GC cloud | Static HTML in S3, origin-pulled by Akamai | **Lower cost, simpler architecture** |
| **Intranet** | AEM author instances | WebBot + FileBot + AI Butler | **Software replacement** |
| **Procurement** | Existing AWS + Akamai contracts | Unchanged — same cloud providers | **None** |
| **CCCS Assessment** | Cloud layer already assessed | Same cloud layer, different software | **Re-assessment scoped to software change** |

#### The Only Change: Software Layer

Canada.ca does not need a new cloud provider, a new CDN, or a new security assessment framework. It needs:

1. **AEM author → WebBot CMS** (same intranet, different software)
2. **AEM publish → Static HTML → S3** (same cloud, simpler architecture)
3. **Akamai origin → S3 bucket** (same CDN, different origin URL)

Everything else — the Akamai contract, the AWS contract, the CCCS cloud assessment, the GCNet connection — stays exactly as it is.

#### Annual Hosting Cost Summary

| Component | Current | Our Platform |
|-----------|---------|-------------|
| Akamai CDN | $160,000 | $160,000 (unchanged) |
| Cloud infra (AWS) | $50,000-100,000 (AEM publish) | $10,000-14,000 (S3 + optional EC2) |
| AEM licensing | $M+ | $0 |
| Operations team | 3-5 FTE | AI Butler + 1 PT oversight |
| **Total cloud + CDN** | **$210K-260K+ excl. licensing** | **$170K-174K** |

> **Bottom line:** Our platform replaces the software without replacing the infrastructure. Canada.ca continues using its existing Akamai and AWS contracts, its existing CCCS cloud assessment, and its existing network architecture. Only the software layer changes.

### 2.12 Redirect Management — Post-Publish URL Migration

URL redirects are a hard requirement for any CMS migration. Canada.ca has ~12+ years of SEO investment in its current URL structure. Every redirect must preserve Google ranking weight and provide zero-friction user experience.

Our redirect strategy operates at **two layers** for maximum flexibility:

#### Layer 1: Meta-Refresh Redirect (Implementation Phase — Available Now)

The first redirect layer is built directly into WebBot's page publishing model:

1. **Properties Window Integration** — Every page has a "Redirect to" field in the Properties window (Basic tab). Editors simply enter the target URL and save — the value is stored as page metadata (`redirect_to`).

2. **Automatic Template Selection** — When publishing, WebBot detects the `redirect_to` field: if present, it automatically selects the dedicated `redirect-template` instead of the normal page layout. The result is a minimal HTML page containing only the redirect logic:
   ```html
   <head>
     <meta http-equiv="refresh" content="0; url=/new-page">
     <link rel="canonical" href="/new-page">
   </head>
   <body>
     <p>This page has moved. <a href="/new-page">Click here</a> if not redirected.</p>
   </body>
   ```

3. **Zero Server-Side Code** — No nginx rules, no application logic on the publish path. Redirects are HTML pages like any other.

4. **Instant Management** — Editors create/update/delete redirects via the same Properties window as all other page metadata. Publish → worldwide in <30 seconds.

5. **Redirect Loop Protection** — Built into the redirect template, a client-side loop detector prevents infinite hops:
   ```javascript
   var key = 'rl_' + btoa(location.pathname).slice(0, 30);
   var count = parseInt(sessionStorage.getItem(key) || '0');
   if (count > 3) { /* stop and show error */ return; }
   sessionStorage.setItem(key, (count + 1).toString());
   location.replace(url);
   ```
   This catches all loop patterns: self-loops (A→A), cross-page cycles (A→B→A), and chain cycles (A→B→C→A). After 3 hops, the page displays a clear error message instead of continuing.

6. **Developer-Friendly** — The template can be customized: immediate redirect, 5-second countdown with message, interstitial information page, or external site warning panel.

7. **Dev/QA/Stage Consistency** — Works identically across all environments because it's pure HTML. No CDN or cloud storage configuration needed for testing.

8. **Bilingual by Default** — Redirect templates are created in both official languages (EN/FR), preserving Canada.ca's bilingual mandate even for redirect pages.

> **SEO consideration:** Meta-refresh redirects pass partial ranking weight (~10-90% depending on duration — `0` second redirect performs best). This is sufficient for interim redirects during content reorganization. For permanent production redirects, Layer 2 provides full 301 preservation.

#### Layer 2: Cloud Storage Object-Level 301 Redirect (Production Excellence)

For permanent, SEO-critical URL migrations, our publish pipeline supports **object-level 301 redirects** on the existing cloud storage platform (to be confirmed with GC's current cloud provider during contract onboarding):

1. When an editor marks a redirect as "permanent", the publish server uploads a **zero-byte object** with the provider's standard redirect metadata header pointing to the target URL.
2. The cloud storage responds with a **true HTTP 301 Moved Permanently** — full SEO weight transfer.
3. Akamai caches the 301 response at the edge, so subsequent requests never touch the origin.
4. Tools for bulk redirect import (CSV/Excel) and redirect integrity checking (no chains, no loops) are included.

> **Implementation note:** This layer adapts to whatever cloud storage Canada.ca currently uses — AWS S3 (`x-amz-website-redirect-location`), Azure Blob (`x-ms-meta`), or equivalent. The publish pipeline treats it as a configuration parameter, not an architectural dependency.

#### When Each Layer Is Used

| Scenario | Layer | Rationale |
|----------|-------|-----------|
| Temporary content reorganization | Layer 1 (Meta) | Quick, manageable, no infrastructure dependency |
| Permanent URL migration | Layer 2 (Cloud Storage 301) | Full SEO preservation, industry standard |
| External site warning | Layer 1 (Custom) | Inform users before leaving Canada.ca |
| Bulk redirect from AEM migration | Layer 2 (Bulk 301) | Preserve all existing rankings at scale |
| Dev/QA/Stage testing | Layer 1 (Meta) | Works with any HTTP server, no cloud dependency |

> **Both layers are managed from a single WebBot UI.** The editor creates a redirect, chooses "temporary" or "permanent", and the correct layer handles it automatically. No DevOps involvement required.

---

## 3. Core Capabilities

### 3.1 Content Management

- **WYSIWYG HTML Editor** — edit pages directly, see exactly what users will see
- **Save as Published** — no intermediate processing
- **Path-based Routing** — page structure mirrors URL structure
- **Version History** — full revision tracking with diff comparison
- **Publish / Unpublish** — immediate control over content visibility

### 3.2 Components & Templates (Mustache Engine)

**Current AEM Problem:**
- Components must be authored in Java, deployed through a multi-month pipeline
- 10-person team developed ~10 components in their first year
- Most content ends up in a "generic HTML component" anyway

**Our Solution — Mustache Template Engine:**
- Templates are **HTML with {{placeholders}}** — no Java, no code compilation
- Created online, edited online, published immediately
- Full coverage of GCWeb and WET component libraries
- New component development: **hours rather than months**
- No programming errors possible — Mustache has no logic (if/else/loops are template-level only)
- Testing is visual only: "does it render correctly?"

**Template lifecycle:**
```
Design → Write Mustache Template → Test in Preview → Save → Use

All steps: hours, single person, in-browser
```

### 3.3 Semantic Search & AI Q&A

**Native, on-premise, and verified.** Unlike competitors who outsource AI to cloud providers (creating data egress, per-query costs, and vendor lock-in), our platform runs AI entirely on dedicated GPU servers inside the government network — with an optional cloud AI toggle for use cases where cloud is explicitly preferred.

Our platform includes:

- **Full-text search** — PostgreSQL built-in text indexing
- **Vector semantic search** — pgvector, 384-dimensional embeddings via e5-small
- **Hybrid search** — combines full-text + vector for best results
- **AI Q&A** — natural language question answering using OpenAI (cloud) or Ollama/Phi3 (local)
  - Provider toggle (Ollama/OpenAI)
  - **Government can choose their preferred third-party AI provider (e.g., OpenAI, Claude, Cohere)** — we handle integration; they pay API token costs
  - Provider-specific caching
  - Site-filtered results
- **Local model, zero data leak** — internal Ollama/Phi3 runs entirely on government infrastructure; **no data ever leaves the network**
- **Accuracy comparison (verified)** — real-world testing confirms local Ollama/Phi3 consistently produces **better answers than OpenAI** for Canada.ca Q&A. Reason: our 12,824 indexed Canada.ca pages provide precise, domain-specific context that cloud LLMs lack. Cloud models' general-world knowledge adds no advantage for government-specific content, while internal models deliver:
  - Superior accuracy on Canada.ca-specific queries (verified)
  - Lower latency (no network round-trip)
  - Zero per-query cost
  - Complete data sovereignty
- **AI-powered content classification** — categorize content automatically
- **Website crawling** — index new content automatically
- **Coveo-compatible architecture** — Coveo (Canada.ca's current search engine) uses API + token-based authentication, the same architecture as our system. Integration is trivial — our platform can serve as a drop-in backend or supplement for Coveo-powered search
- **Department-level contextual search** — our built-in semantic + hybrid search engine can **replace Coveo entirely** for department-specific or intranet search:
  - Better accuracy for Canada.ca-specific content (domain-tuned embeddings, proven in testing)
  - Zero per-query cost vs. Coveo's SaaS pricing model
  - No data leaves the government network vs. Coveo cloud processing
  - AI Q&A integration beyond keyword search — ask natural language questions, get cited answers
  - Already operational with 29,304 indexed pages — not a planned feature

**29,304 Canada.ca pages** are already imported, indexed and searchable — more added daily via automated import.

### 3.4 File Management & Migration

- **Zero-transformation migration** — import existing HTML directly, no component mapping needed
- **Multi-format conversion** — PCL→PDF, TIFF→JPG, PNG, TXT
- **File naming rules engine** — consistent naming across migrated content
- **Document preview** — HTML preview for any document type
- **Thumbnail generation** — automatic resizing for previews
- **Storage management** — capacity detection, allocation, device management

### 3.5 Import & Export

- **Bulk import** — import entire websites or sections
- **Sitemap crawling** — auto-import from sitemap.xml
- **Selective export** — by app, folder, or custom criteria
- **Full export** — complete site backup
- **Alternate language crawler** — preserve bilingual content relationships
- **Bookmarklet one-click import** — from any live Canada.ca page:
  1. Click the bookmarklet → page HTML is captured and sent to the import endpoint
  2. **Dual-write** — the import endpoint stores to FileBot (PostgreSQL file storage + folder tree) AND pushes to WebBot (SQLite editor content) simultaneously
  3. Page is immediately editable in WYSIWYG — no manual steps, no delays
  4. Path transformation handles the mapping: Canada.ca URL → FileBot path → WebBot path
- **Skip-if-exists deduplication** — importing the same page twice creates no duplicates; second attempt is silently handled
- **29,304 Canada.ca pages already imported** via this pipeline — live and editable today

> **Operational Assessment:** The bookmarklet import function represents one of the most practically valuable features of the platform. Canada.ca editors routinely manage hundreds of existing pages. A tool enabling one-click capture of any live page into the editing environment — eliminating file copying, component mapping, and processing delays — transforms the system from a theoretical improvement into a tangible time-saving instrument.

### 3.6 User & Permissions

- **OAuth2 authentication** — compatible with GC authentication standards
- **Role-based access control** — granular permissions per user/group
- **Department isolation** — each department manages its own content
- **Audit trail** — all actions logged
- **Group management** — departmental groups with member management

### 3.7 Version Management

- **Page version snapshots** — full content + metadata saved on each publish
- **Version comparison** — see what changed between versions
- **Rollback** — restore any previous version
- **Draft management** — work on changes without affecting published content
- **Manifest tracking** — centralized version registry

### 3.8 Analytics

- **Built-in tracking** — no Google Analytics dependency
- **Page view statistics** — per-page and aggregated
- **Admin dashboard** — visual analytics interface

### 3.9 API-First Design & Extensibility

Every function in our system is exposed via RESTful API. This is a deliberate architectural decision:

**Current AEM problem:**
- All functionality is tightly coupled to the Java/JCR ecosystem
- Third-party development requires deep AEM expertise and Adobe certification
- Custom integrations are expensive, slow, and version-locked to AEM releases

**Our approach — API-first:**

| Type | Endpoint | Who can use it |
|---|---|---|
| Content CRUD | `/api/v1/pages/*` | Any HTTP client |
| Search & Query | `/api/v1/search/*` | Frontend, mobile apps, data tools |
| AI Q&A | `/api/v1/ai-query` | Custom chatbots, internal tools |
| File Conversion | `/api/v1/conversion/*` | Batch processing scripts |
| Export | `/api/v1/export/*` | Backup tools, data migration |
| Import (bulk) | `/api/v1/import-to-webbot/*` | Custom migration pipelines |
| Import (one-click) | `/api/v1/import-page` | Bookmarklet import → dual-writes to FileBot + WebBot |
| Mustache Render | `/api/v1/render-mustache` | Dynamic page generation |

**Implications for the Government Ecosystem:**

- Existing contractors and developers **retain the ability to build value-added services** — now using modern API calls rather than AEM Java components
- Developers can build departmental dashboards, mobile applications, and automated workflows in **any programming language** — Python, JavaScript, Go, PowerShell
- New features require standard API skills rather than AEM-specific expertise
- **Integration with GC systems** (pay, benefits, immigration) is accomplished through standard REST APIs with JWT authentication
- **Third-party vendors remain fully supported** — the API is open and well-documented

> "Adopting our system does not diminish work within the ecosystem. It elevates it — enabling the development of modern, API-driven government services rather than the maintenance of legacy Java components."

### 3.10 Bilingual Content Support (Official Languages)

Canada.ca must operate in both English and French — this is a legal requirement under the **Official Languages Act**. Our system treats bilingual support as a first-class architectural feature, not an afterthought.

**How it works:**

```
/en/content           → English page
/fr/content           → French page (same structure, mirror path)
```

| Capability | Details |
|---|---|
| **Dual-language page generation** | Each publish generates English and French pages simultaneously |
| **Structured mirroring** | `/en/page-about` ↔ `/fr/page-about` — same URL structure, different language content |
| **One-to-one translation mapping** | Editor writes English, then translates to French preserving full page structure (templates, layout, components unchanged) |
| **Independent editing** | English and French versions can be edited independently — no lock-step requirement |
| **Partial translation** | A page can be in one language while its counterpart is being created |
| **Language-aware search** | Search results filter by language; semantic search works in both |
| **AI-assisted translation** | Future: AI can draft translations for human review (separate RFP) |
| **Alternate language crawling** | Import tool maintains language pairings from existing Canada.ca content |

**Key advantage over AEM:**

In AEM, bilingual content management is implemented through the JCR tree structure — each language version is a child node of the same content. This creates complexity:
- Language relationship is buried in the repository structure
- Editors need AEM-specific training to manage translations
- Translation workflow requires custom Java components

In our system:
- Language is a **path-level attribute**: `/en/x` and `/fr/x`
- Both pages are independent HTML files — no repository magic
- Editors manage both languages through the **same WYSIWYG interface**
- Translation preserves structure because **templates are shared** — only the {{content}} changes
- Export/import tools handle both languages seamlessly

---

## 4. Comparative Analysis

### 4.1 Feature Comparison

| Capability | Adobe AEM | Our Platform |
|---|---|---|
| **Component Development** | Java code, 3-6 months | Mustache template, hours |
| **Template Engine** | Java/JSP | Mustache (logic-less HTML) |
| **Database** | None (JCR) | PostgreSQL + pgvector |
| **Search** | None (outsourced separately) | Built-in: full-text + vector + hybrid |
| **AI Q&A** | None | OpenAI + Ollama, provider toggle |
| **Content Storage** | JCR tree structure | HTML files + relational DB |
| **Editor** | Component-based, structured | HTML WYSIWYG |
| **Publish Latency** | ~2 hours | ~3-5 minutes |
| **Migration** | Custom Java components per source | Zero-transformation (HTML in/out) |
| **Intranet Security** | Requires separate AEM Author license | Inherently secure (WebBot on intranet) |
| **CSS Framework** | Java-enforced styles | GCWeb + WET (standard CSS) |
| **Code Injection Risk** | High (Java components) | None (Mustache has no logic) |

### 4.2 Cost Comparison (Annual)

| Item | AEM (Industry Standard) | Our Platform |
|---|---|---|
| **License Fee** | Industry standard enterprise pricing | $0 (Open source) |
| **Consulting** | Standard enterprise consulting | $api token cost |
| **Search** | Separate enterprise license | $api token cost (built-in) |
| **Migration** | Per-project, variable | $0 (no migration needed) |
| **Infrastructure** | Multi-instance enterprise architecture | 2 light servers + CDN |
| **AI API Costs** | N/A | At cost — government chooses provider, we integrate |
| **Total** | **Enterprise-level** | **80-90% less than enterprise alternative** |

### 4.3 Timeline Comparison

| Milestone | AEM Approach | Our Approach |
|---|---|---|
| **First component** | 6-12 months | Hours |
| **First 10% departments migrated** | 2+ years | Days |
| **All departments full migrated** | on going | Months |
| **Full Canada.ca migration** | 10 years → on going | Progressive, risk-free |

---

## 5. Migration Strategy

### 5.1 Philosophy: Two-Path Migration

AEM data extraction is a known risk. Vendors have historically been uncooperative — either through technical barriers or contractual restrictions — when asked to export content to a competing platform. Our strategy does not depend on AEM cooperation.

**We operate two parallel migration paths simultaneously:**

```
Path A (Preferred): AEM direct export      Path B (Guaranteed): Public crawl + client import
  AEM folder structure + metadata     →       Public Canada.ca website (zero AEM dependency)
  Bulk HTML export                          Web crawl (proven, 29,304 pages imported)
  Fastest path                               Client-side import via bookmarklet
  Requires AEM cooperation                   Online + offline import
                                            Bottleneck-free (client-side processing)
```

**Either path works. Both paths can run simultaneously.**

> **No third-party integrator required.** In AEM deployments, data migration is typically contracted to system integrators (Accenture, Deloitte, IBM) at significant cost. Our platform has migration capabilities built in — crawl, import, transform, verify, publish — all in-house. No external consultants needed.

### 5.2 Path A — AEM Direct Export (Cooperative)

If AEM cooperates with a bulk HTML export:

1. **Export**: AEM exports department pages as HTML files + folder structure metadata
2. **Import pipeline**: Our import system ingests the export — folder hierarchy, filenames, HTML content — in bulk
3. **Path transformation**: AEM paths (e.g. `/content/canadasite/en/dept/page`) are automatically remapped to our platform's structure
4. **Verification**: Imported pages are compared against the live Canada.ca deployment to verify completeness
5. **Go live**: Pages are immediately editable and publishable — zero modification needed

**Estimated throughput**: Entire departments (thousands of pages) in hours, not weeks.

### 5.3 Path B — Public Crawl + Client Import (Guaranteed, Proven)

If AEM does not cooperate, or while waiting for cooperation:

#### Public Web Crawl (Server-side)

- Crawl the public Canada.ca website — same content served to citizens, no AEM access required
- **Already proven**: 29,304 Canada.ca pages successfully imported via this method
- EN/FR pages automatically paired via URL mapping
- Skip-if-exists deduplication ensures incremental updates without re-crawling
- Image assets served via our proxy (DamProxyASGI) — `/content/dam/...` URLs mapped to local cache

#### Client-Side Import (Bottleneck-free)

- **Bookmarklet tool** (in-browser, one-click): User visits a live Canada.ca page → clicks bookmarklet → page is imported
- **Client-side processing**: HTML extraction happens in the user's browser, not on our server. This eliminates server bottlenecks — zero contention regardless of how many users import simultaneously
- **Dual-write**: Each import writes to both FileBot (asset storage + AI) and WebBot (editor + publishing) — seamless sync
- **Offline capable**: Files can be imported from local disk — doesn't require the source page to be online

> **Why this matters**: For a GC-wide rollout with thousands of editors, client-side processing means no centralized import server becomes a bottleneck. Each editor's browser does the work. Scale is infinite.

### 5.4 User Identity Migration — Zero Migration Required

AEM user data is not stored in AEM. It is sourced from Windows Active Directory / LDAP. Migrating AEM users is therefore a **non-problem**.

#### Architecture

```
Current: Windows AD / LDAP → AEM (user reference) → AEM permissions
Ours:    Windows AD / LDAP → SSO Gateway → Our platform → Our permissions
```

#### How It Works

1. **SAML 2.0 / OIDC SSO gateway** at the API layer — standard protocol compatible with GC's existing AD FS / Entra ID deployment
2. **Zero user migration**: No usernames, passwords, or profiles exported from AEM. Users authenticate directly against their existing AD identity
3. **First-login auto-provisioning**: When a user first SSO-s in, our system automatically creates a local account using their AD `sAMAccountName` / UPN
4. **Group-based authorization**: AD groups (e.g. `GC-Canada-Editors`, `GC-Canada-Approvers`) map to our system roles — no manual permission setup
5. **Fallback authentication**: Local password auth remains available for development, staging, and off-network scenarios

#### Advantages Over AEM User Migration

| Aspect | AEM User Migration | SSO Direct |
|---|---|---|
| AEM cooperation required | ✅ Yes — must export user data | ❌ No dependency |
| Data transfer | Full export + import (privacy risk) | Zero user data leaves AD |
| Password management | Migrate hashes or force reset | Handled by AD (existing MFA, policies) |
| Ongoing sync | Two systems to keep in sync | Single source of truth (AD) |
| Offboarding latency | Delay until sync runs | Immediate — AD change = our change |
| MFA | AEM must implement separately | AD already has it |

> **Net assessment**: SSO is not only easier than user migration — it produces a **better security outcome**.

### 5.5 Progressive Rollout

```
Pre-Migration (Completed — June 2026):
  → 29,304 Canada.ca pages crawled and indexed
  → EN/FR pairing verified
  → Skip-if-exists deduplication operational
  → Bookmarklet import + dual-write live
  → Path B (crawl) proven across 25+ department sub-sites

Phase 1 (Weeks 1-2): PoC with one department
  → Import their content via Path A (preferred) or Path B (guaranteed)
  → SSO gateway configured with test AD
  → Show WYSIWYG editing → publish pipeline
  → Proof: it works, immediately

Phase 2 (Month 1-3): 2-3 departments
  → Full SSO integration with GC AD FS / Entra ID
  → Parallel running with AEM
  → Editors trained (minimal — same HTML/WET/GCWeb)

Phase 3 (Month 4-12): Expand as departments opt in
  → No forced migration
  → Departments choose when to switch
  → AEM maintained alongside for existing content

Phase 4 (Year 2+): Transition complete
  → All departments on new platform
  → AEM decommissioned
```

### 5.6 Migration Without Disruption

| Risk | Mitigation |
|---|---|
| AEM won't export data | Path B (public crawl + client import) — zero AEM dependency |
| Content loss | HTML in → HTML out. No transformation = no loss |
| Editor training | Same GCWeb/WET framework, same HTML skills |
| Department concerns | No forced migration, opt-in only |
| User migration complexity | SSO — no user data migration needed |
| Server bottleneck during import | Client-side processing (bookmarklet) — no centralized load |
| Existing workflows | Compatible with existing CDN + LB + publish servers |
| Bilingual content | Preserved and tracked via alternate-language crawling |
| **Third-party dependency** | **No system integrator needed** — migration capabilities are built into the platform, not outsourced |
| **Data sovereignty / cloud certification** | Hybrid architecture: editorial server **inside govt network** (no cloud cert needed), only public HTML to CDN — exceeds "data in Canada" requirement |

---

## 6. Security & Compliance

### 6.1 Architecture-Level Security

- **Intranet isolation** — WebBot never exposed to public internet
- **Cloudflare** — DNS protection (Canada.ca is using, free charge with internet cloud provider)
- **No code injection** — Mustache templates contain zero executable code
- **No JCR/Java attack surface** — no Java runtime on the server
- **Authentication gateway** — WebBot proxy adds auth layer to all internal API calls

### 6.2 GC Compliance

- **WCAG 2.1 AA** — GCWeb + WET framework already compliant; editor enforces compliant HTML
- **GC Web Security Standard** — architecture aligned with government security directives
- **Data sovereignty** — all content stored on government infrastructure
- **Audit trail** — all editorial actions logged
- **Access control** — fine-grained permissions per department, group, user
- **No third-party data sharing** — optional local LLM (Ollama/Phi3) for air-gapped environments; **zero data leaves government network**
- **Accuracy verified** — for Canada.ca Q&A, internal models produce answers comparable to or more accurate than cloud models. The locally indexed knowledge base (12,824 pages) is already comprehensive for government content — cloud models' general training adds no measurable advantage, while local models eliminate data transmission risks entirely

### 6.3 Authentication: Beyond Username & Password

**AEM's security model** relies on simple username/password authentication. Once credentials are compromised, an attacker has full system access.

**Our security model** adds multiple layers:

| Layer | AEM | Our Platform |
|---|---|---|
| **Primary auth** | Username + password | Username + password |
| **Session control** | Standard session | **Token-based auth** (JWT) with refresh tokens |
| **Token expiration** | Session-based | Short-lived access tokens + refresh token rotation |
| **API protection** | URL-based | Every API call requires valid token verification |
| **Public endpoints** | Broad exposure | Narrow, token-protected, proxied through auth gateway |

**Token-based authentication means:**
- Even if a password is compromised, the attacker needs a valid JWT token
- Tokens expire — stolen tokens are only usable for a window of minutes
- Refresh tokens can be invalidated server-side (log out everywhere)
- Every API call is independently verified — no "session hijacking" window

### 6.4 Physical & Network Security: Two-Tier Architecture

**AEM's problem:** The Author server (where editing happens) is often in the same network segment as the Publish server — or in the worst configuration, exposed to broader internet access.

**Our architecture is fundamentally more secure by design:**

```
┌─────────────────────────────────────┐
│        PUBLIC INTERNET              │
│                                     │
│  FileBot (port XXXX)               │
│  • Static file delivery            │
│  • Public assets only              │
│  • No editorial access             │
│  • No content management           │
│  • No user interface for editing   │
└─────────────────────────────────────┘
              ↑ firewall ↑
┌─────────────────────────────────────┐
│        INTRANET (Government)        │
│                                     │
│  WebBot (port XXXX)                 │
│  • ALL content management           │
│  • ALL editorial interfaces         │
│  • ALL databases (PostgreSQL)       │
│  • ALL authoring tools              │
│  • NOT accessible from internet     │
└─────────────────────────────────────┘
```

**The public-facing server runs FileBot ONLY:**
- FileBot in public mode is an **asset delivery and format conversion engine** — nothing more
- No editorial interface is exposed
- No content management database is accessible
- No session management, no login pages, no editors
- Even if the public server is compromised, **it contains zero content management data**
- The attacker would only have access to static generated files (which are already public anyway)

**The intranet server runs WebBot ONLY:**
- All editorial work, content databases, version histories remain behind the government firewall
- No public access paths to WebBot exist
- Publishing is a **one-way push**: WebBot → FileBot. There is no reverse path.

### 6.5 Secure by Default

| Attack Vector | AEM | Our Platform |
|---|---|---|
| **Authentication** | Username/password only | **Password + JWT token + refresh rotation** |
| **Public editor exposure** | Author server on network | **Zero editorial surface on public** |
| **XSS** | Java-generated markup complex to audit | Mustache auto-escapes HTML; editor content validated |
| **SQL Injection** | None (no DB at all — but no search either) | SQLAlchemy parameterized queries throughout |
| **CSRF** | Standard | Token-based auth on all write operations |
| **Code Execution** | Java components can execute arbitrary code | **No runtime code execution paths exist** (Mustache has no logic) |
| **Data Exfiltration** | Author data accessible where Author runs | Intranet-only access for editorial data |
| **Supply Chain** | Proprietary, audit requires Adobe | Minimal dependencies; open-source audited libraries |

### 6.6 Resilience for High-Profile Targets: Canada.ca Under Attack

Canada.ca is one of the most visible government websites in the world. It faces constant, targeted attacks — DDoS, defacement, credential stuffing, data scraping, and nation-state-level probing. Our architectural choices are designed with this reality in mind.

#### 6.6.1 Defacement Prevention

Content defacement (altering published pages) is a top concern for any high-profile government site.

**Attack scenario:** An attacker compromises the publish server and replaces Canada.ca homepage HTML.

| Layer | AEM | Our Platform |
|---|---|---|
| **Publish surface** | Author server accessible from network | **Static files only** — no runtime to exploit |
| **File integrity** | Relies on AEM instance security | **Content hash tracking** — every published file has a SHA-256 checksum; tampering is instantly detectable |
| **Rollback** | Requires AEM version restore | **Versioned by design** — revert any file to any prior version in seconds |
| **Compromise window** | Undetected until reported | **Auto-integrity scan** — periodic checksum verification against known-good hashes; alert on mismatch |

#### 6.6.2 DDoS Resilience: Minimal Attack Surface

**Attack scenario:** An attacker launches a volumetric DDoS attack targeting Canada.ca.

**Why our architecture is inherently DDoS-resilient:**

- **The editorial system is unreachable from the internet.** WebBot, all databases, AI servers, and administrative interfaces run exclusively on the government intranet — they have **no public IP, no public DNS, no public route**. A DDoS attack cannot touch them because they are simply not on the internet. This is fundamentally more secure than any cloud CMS (Contentful, Acquia, Adobe Experience Cloud) where the admin interface is internet-facing by design.
- **Only static HTML goes to the cloud.** The only data that touches the public internet is pre-rendered, publish-ready static HTML files. No dynamic code, no session state, no database connection — just files on disk.
- **If the CDN is attacked, that is the cloud provider's problem.** Akamai, CloudFront, or Cloudflare have petabit-scale DDoS mitigation infrastructure designed exactly for this. A DDoS attack on the CDN is absorbed by their global edge network — our origin servers never see it. This is the same model used by Netflix, GitHub, and the UK Government GOV.UK.
- **No dynamic rendering on the public server.** AEM's publish server executes Java code on every request — each request costs CPU and memory, making DDoS attacks resource-exhaustion attacks. Our public server serves **pre-rendered static files** from disk or CDN cache — a request costs close to zero CPU.
- **Static files = CDN-friendly.** Static HTML, CSS, JS, and images are trivially cacheable at the CDN edge (Akamai). An attacker hitting the origin will largely be absorbed by CDN capacity, not our servers.
- **No session state on public server.** AEM publish servers maintain session state, making them vulnerable to state-exhaustion attacks. Our public server has **zero session state** — no login, no cookies, no in-memory state to exhaust.
- **Publish server can operate behind CDN entirely.** The public-facing FileBot instance can be deployed behind Akamai (or GC CDN of choice) with origin-only access. CDN handles the attack; origin never sees it.

> **Bottom line**: In our architecture, a DDoS attack on Canada.ca is a DDoS attack on Akamai — not on the CMS. The editorial system is physically unreachable from the internet. No cloud CMS can make that claim.

#### 6.6.3 Supply Chain Attack Protection

**Attack scenario:** An attacker compromises a dependency (library, package, image) and injects malicious code through the software supply chain.

| Risk | Mitigation |
|---|---|
| **NPM/PyPI compromise** | All dependencies are pinned to specific versions; automated CVE scanning in CI pipeline |
| **Build-time injection** | Build environment is isolated, deterministic, and reproducible |
| **Container image tampering** | Images signed and verified before deployment |
| **AI agent code injection** | All AI-generated code is human-reviewed before any deployment. AI agents operate in sandboxed environments with no access to production secrets |
| **Third-party CDN compromise** | All frontend assets are self-hosted (no CDN-hosted scripts). No external JavaScript loaded at runtime |

#### 6.6.4 Post-Compromise Containment

Even in the worst case — an attacker gains access to a server — our architecture limits the blast radius:

- **Public server compromise** → Attacker gets static files only. No user data, no credentials, no editorial access, no database. Rotate and rebuild in minutes.
- **Intranet server compromise** → Requires breaching the government firewall AND the intranet application. Even then, the public serving infrastructure is unaffected. Publish can be stopped, logs reviewed, and content restored from version history.
- **Database compromise** → Contains content only (HTML pages and metadata). No PII, no financial data, no credentials (passwords are hashed, tokens are ephemeral).

#### 6.6.5 Content Integrity Monitoring

A periodic background process verifies that every published file matches its recorded checksum. If a file is modified outside the authorized publish pipeline:

1. Alert is generated within 15 minutes
2. Affected file is identified and isolated
3. Authorized version is restored from version history
4. Incident report is logged to the audit trail

This system runs entirely on the intranet side, so an attacker who compromises the public server cannot suppress the alert.

---

## 7. Cost Model

### 7.1 Proposed Pricing

**Year 1-2: Service Fee Only — Estimated $800K–$1.5M/year**
- No license fee
- Covers: Customized Filebot+Webbot system, Migrate AEM content to our system, system operation, monitoring, AI model maintenance, emergency support. Infrastructure and data bandwidth cost, and third party API are extra (we are unsure about that).
- Government bears no financial risk — if the system does not deliver, it may be discontinued without penalty

**Year 3+: Negotiated License — Estimated $500K–$1M/year**
- Competitive, transparent pricing based on demonstrated value
- Includes license + continued service
- Adjustable per department scope

> **Value comparison:** Our pricing represents a fraction of typical enterprise CMS costs. At the high end ($1.5M/year), the savings are substantial; at the low end ($800K), even more so.

### 7.2 What's Included

| Service | Included |
|---|---|
| Platform license | ✓ (Free first 2 years); competitive renewal thereafter |
| System deployment & configuration | ✓ |
| Content import & migration | ✓ |
| Editor training & onboarding | ✓ |
| Technical support | ✓ |
| AI API costs (OpenAI) | At cost |
| Server infrastructure | Government-provided or third-party |

### 7.3 Total Cost of Ownership (10-Year Projection)

| Cost Category | Our Platform |
|---|---|
| Service fee (Y1-2) | $800K-$1.5M/year |
| License fee (Y3+) | Negotiated, free after 10 years |
| Migration | $0 (zero-transformation) |
| Infrastructure | ~$0.5M (10yr estimate) |
| AI API costs | At cost — government selects provider, we integrate, they pay token fees |
| **Total (10yr)** | **~$6-12M (estimated)** |

---

## 8. Government RFP Essentials

### 8.1 Service Level Agreement (SLA)

| Metric | Proposed Commitment |
|---|---|
| System availability | 99.9% uptime (excluding scheduled maintenance) |
| Publish pipeline latency | < 5 minutes from editor publish to CDN delivery |
| Critical issue response | < 4 hours, 24/7 |
| Standard issue response | < 1 business day |
| Scheduled maintenance window | Monthly, < 2 hours, pre-announced |

*Final SLA terms to be negotiated in accordance with GC procurement standards and service requirements.*

### 8.2 Support Model

| Level | Response Time | Coverage |
|---|---|---|
| **L1 — Runtime issues** (system down, publish failure) | < 4 hours | 24/7 |
| **L2 — Functional issues** (editor problem, configuration) | < 1 business day | Business hours, Eastern Time |
| **L3 — Feature requests** (new template, integration) | Per SOW | Project-based |
| **Emergency contact** | < 1 hour | On-call rotation |

All support is staffed by the development team — not a separate help desk.

### 8.3 Data Sovereignty & Hosting

- **All content data** stored on government-managed infrastructure (intranet or GC cloud as specified)
- **All databases** (PostgreSQL, vector indices) remain on government-controlled systems
- **No third-party access** to editorial content
- **AI API calls** (OpenAI or provider of choice, optional): only anonymized queries leave government network; alternatively, local Ollama/Phi3 can be used with **zero external data transmission**
  - Government selects and contracts the AI provider; we handle platform integration
  - API token costs paid directly by government
- **Internal models, equivalent accuracy** — for Canada.ca Q&A, local models match or exceed cloud LLMs on accuracy. Since the knowledge base is fully indexed locally, cloud models contribute no additional information — only added cost, latency, and data exposure risk
- **Servers**: deployable on government-provided hardware, Azure Government, or AWS GovCloud — whichever GC has accredited
- **Compliant with**: GC Data Residency requirements, TBS security directives

### 8.4 Intellectual Property & Licensing

| Aspect | Terms |
|---|---|
| **System code** | Our proprietary software; licensed (not sold) to government |
| **Government content** | Crown copyright — fully owned by government |
| **Custom development** | Code written specifically for Canada.ca belongs to Canada.ca |
| **Third-party components** | Open-source (PostgreSQL, Python, FastAPI) — standard permissive licenses |
| **License model** | No per-user or per-page licensing. Predictable fixed or usage-based fee. |

### 8.5 Exit Strategy & Data Portability

We recognize that any procurement must include a viable path to an alternative provider. Our system is designed for zero lock-in:

- **All content is stored as standard HTML files** — no proprietary format, no transformation needed to migrate away
- **Database uses standard PostgreSQL** — any SQL tool can read, export, or migrate the data
- **Template engine is standard Mustache** — templates are text files, not compiled code
- **Full export tool** already built: `/api/v1/export/*` — generates complete HTML archive of all content
- **Migration to another CMS**: because our system stores content as HTML (not in a proprietary repository), any CMS that accepts HTML import can receive the data with no transformation
- **In short**: switching away from our system is as simple as copying the HTML files — which is how Canada.ca operated before AEM

### 8.6 Security Certifications & Compliance

| Requirement | Status |
|---|---|
| **PSPC Security Clearance** | **Already held by principal architect, valid for 10 years** — no procurement delay for personnel clearance |
| **GC Security Standard** | System architecture designed to align; compliance assessment within 90 days of contract award |
| **GC Web Security Standard** | Compliant by design (no code injection, no JCR, intranet isolation) |
| **WCAG 2.1 AA** | GCWeb + WET framework provides compliance out of the box |
| **Penetration testing** | Third-party test scheduled within 60 days of deployment |
| **Vulnerability disclosure** | Dedicated channel for security researchers |

### 8.7 Monitoring, Logging & Observability

- **Structured logging** — all system events logged with timestamps and request IDs
- **Health check endpoints** — available for integration with government monitoring tools
- **Audit trail** — every editorial action, publish, configuration change logged with user identity
- **Alerting** — configurable alerts for disk space, process health, publish failures
- **Backup verification** — automated checks that backups are valid and restorable

---

## 9. Our Company & Team

### 9.1 Our Story

> *"I have spent over 20 years on the Canada.ca / WCA system — through the pre-AEM era of plain HTML files, through the AEM transition, and through every iteration since. This system has served millions of Canadians, and I believe its best chapter lies ahead: the AI era."*

Our architect brings over two decades of direct, hands-on experience with Canada.ca content management — knowledge that cannot be acquired through consulting briefings or documentation review. Every component of this proposal is informed by deep understanding of what the system needs and where it should go.

### 9.2 Company Background

**Yuhong Web Inc.** (incorporated July 12, 2017) — by the time the RFP project enters implementation (2028), our company will have been operating for over a decade:

- **Incorporated 2017** — stable, funded, independent
- **FileBot** — our asset management engine, with **5 active users across US-based organizations**, operating continuously supporting real-world content workflows
- **WebBot** — our content management layer, the latest AI-augmented addition built on top of the proven FileBot platform
- **Long-term commitment** — we are building a platform for the next decade of government content management

**Conflict-of-interest note:** Our architect is currently on leave and will retire from public service by the end of 2026 — well before the 2028 project implementation. This means the project will be delivered in full compliance with the Conflict of Interest Act and its cooling-off provisions. Our interests are aligned with Canada.ca's success:

- **Two years zero licensing fee** — we prove value before asking for more
- **Open-source technology** — no proprietary lock-in at any layer
- **Complementary to AEM**, not adversarial — AEM was the right choice for its era
- **No decision-making authority within the department** — our architect is no longer involved in any procurement or policy decisions on the government side

Full disclosure will be provided in compliance with GC procurement requirements.

### 9.3 Team Members

#### Human Team

| Member | Background | Role on Project |
|---|---|---|
| **Hongbin Yu** | Retired senior developer, 20+ years Canada.ca design & development | System architect, domain expert, solution lead |
| **Sandy Deroche** | Retired, 20+ years Canada.ca network management & user administration | Network admin, user management, governance |
| **Rita Lou** | MBA | Sales, client relations, contract management |

All human team members hold or have held GC security clearances.

#### AI Development Agents

| Agent | Knowledge Domain | Role |
|---|---|---|
| **Radish** | WebBot system | WebBot development, component creation, AI pipeline |
| **Coboy** | FileBot system | FileBot development, system admin, migration automation |
| **Younai (Unite Li)** | Full-stack operations | AI butler, deployed with servers to client sites |
| **Su Xiaomi** | Quality assurance | Code review, security audit, QA sign-off |

*AI agents operate within the same security architecture as the rest of the system — no external data exposure, no unmonitored code execution. Every AI-generated output is reviewed and validated by a human team member before deployment.*

### 9.4 Our Approach: AI-Empowered Small Team

Traditional CMS projects require large teams because the technology demands it. Our approach leverages AI to amplify a small, experienced team — not to replace human judgment, but to accelerate development and eliminate repetitive work:

| Role | Traditional AEM Team | Our Team |
|---|---|---|
| **System Architect** | 1 FTE | Hongbin Yu (20yr Canada.ca) |
| **Java Developers** | 5-10 FTEs | 0 (no Java needed) |
| **Frontend Developers** | 2-3 FTEs | 1 (Radish AI-assisted) |
| **Network / User Admin** | 1-2 FTEs | Sandy Deroche (20yr Canada.ca) |
| **AI/ML** | 0 (not in AEM) | Radish + Coboy + Younai + Su Xiaomi |
| **QA** | 2-3 FTEs | 1 + Su Xiaomi (AI-assisted review) |
| **DevOps / Migration** | 1-2 FTEs | Coboy + Younai (AI-assisted) |
| **Client Relations** | 0 | Rita Lou (MBA) |
| **Content Strategists** | Canada.ca team (partner) | Canada.ca team (partner) |
| **UX Designers** | Canada.ca team (partner) | Canada.ca team (partner) |

**Division of labor: humans design and review, AI builds and maintains.**

Our operating model separates responsibility by what each does best:

| Layer | Responsibility | Who |
|---|---|---|
| **Design & Architecture** | System design, data model, security architecture, client requirements | Human team (Hongbin, Sandy) |
| **Review & Validation** | Code review, security audit, QA sign-off, deployment approval | Human team (Hongbin, Sandy) + Su Xiaomi |
| **Coding** | Feature development, API endpoints, UI components, database queries | AI agents (Radish, Coboy) |
| **Execution** | Migration scripts, batch processing, testing, deployment scripts | AI agents (Radish, Coboy, Younai) |
| **Maintenance** | Bug fixes, routine updates, monitoring, minor improvements | AI agents (Coboy, Younai) |
| **Client Relations** | Contract management, client communication | Rita Lou |

**Why this works:**
- The human team brings **20+ years of Canada.ca domain expertise** that no AI has — they know exactly what to build
- The AI agents work **24/7 at machine speed** — they build exactly what is designed, without fatigue or delay
- Every line of AI-generated code is **reviewed by a human before deployment** — no risk of runaway AI
- This model is **inherently scalable**: adding a new department or feature requires zero headcount growth, just AI agent time

**Real-world example:** A typical AEM component (template, dialog, model, test) takes a team of 3 developers 2-3 weeks. Our pipeline: human describes the requirement (30 min), AI agent builds and tests it (2-4 hours), human reviews and approves (30 min). **Total: ~5 hours instead of 3 weeks.**

### 9.5 Partnership with Canada.ca Team

We do not replace the Canada.ca team — **we partner with them**:

- Their 10+ years of domain knowledge is invaluable
- Our technology amplifies their capabilities
- They define content strategy and UX; we provide the platform
- **Outcome**: They gain access to AI capabilities that AEM was not designed for, while their expertise remains central

### 9.6 Delivery Timeline

*Note: The following timeline assumes standard government network provisioning, security assessment, and procurement processes. Actual timelines will be adjusted based on government requirements and readiness.*

| Milestone | Estimated Timeline |
|---|---|
| **System deployment** | Week 2-3 (after procurement and security clearance) |
| **First department POC** | Week 4-6 |
| **Pilot department live** | Month 2-3 |
| **2-3 departments onboarded** | Month 4-6 |
| **Full rollout to opting departments** | Month 6-18 |
| **AEM transition complete** | Year 2+ |

---

## 10. What We've Already Built

Every feature listed below is **live and operational today** — not a roadmap item, not a planned feature, not a future milestone. These are running services accessible right now.

| Capability | Status | Location |
|---|---|---|
| WYSIWYG HTML editor | Operational | WebBot (intranet) |
| Mustache template engine | Operational | WebBot + FileBot |
| Content management (CRUD, folders, publish) | Operational | WebBot |
| Semantic vector search (pgvector) — 29,304 indexed pages | Operational | FileBot |
| AI Q&A (OpenAI + Ollama, provider toggle) | Operational | FileBot (cloud) |
| Website crawling and sitemap import | Operational | FileBot |
| AI content classification | Operational | FileBot |
| Zero-transformation content import | Operational | FileBot |
| Multi-format file conversion (PCL to PDF, TIFF to JPG, TXT) | Operational | FileBot |
| Version management and publishing | Operational | WebBot + FileBot |
| User and permission management | Operational | WebBot |
| Bilingual content (EN/FR mirror) | Operational | WebBot |
| Full REST API for extensibility | Operational | All endpoints |
| Data export and import | Operational | FileBot |
| Bookmarklet one-click import (dual-write to both databases) | Operational | FileBot + WebBot |
| **Client-side page import** (browser bookmarklet, zero server bottleneck) | Operational | WebBot |
| **Public website crawl — 29,304 Canada.ca pages imported** | ✅ Completed | FileBot |
| **EN/FR page pairing** via URL mapping | Operational | FileBot |
| **Skip-if-exists deduplication** (incremental re-crawl) | Operational | FileBot + WebBot |
| **Auto path transformation** (AEM → WebBot path mapping) | Operational | FileBot (+ WebBot) |
| **DamProxyASGI** — `/content/dam/` image proxy with local caching | Operational | FileBot |
| **SSO-ready auth layer** (SAML 2.0/OIDC capable, password fallback) | Architected | FileBot |
| **Data migration built-in** (no third-party integrator needed) | Operational | FileBot + WebBot |
| **Hybrid deployment** (intranet editor + cloud CDN, data never leaves govt network) | Operational | WebBot + CDN |
| **On-premise AI** (dedicated GPU server, zero data egress, no per-query cost) | Operational | FileBot (intranet) |
| **Entire Canada.ca fits on 2 TB NVMe** (~900 GB–1.2 TB for all content + AI) | Architected / Sized | Production server |
| **Distributed deployment** (per-department servers, geo-LB, no single point of failure) | Architected | Multiple intranet instances |
| **Coveo-compatible search** (API + token auth, same architecture) | Compatible | FileBot |
| **Department-level contextual search** (replace Coveo, zero per-query cost) | Operational | FileBot + pgvector |
| **DDoS-proof by architecture** (editorial intranet unreachable, CDN attacks = cloud provider's problem) | Operational | Intranet + CDN |
| Dual-database architecture (SQLite editorial + PostgreSQL assets/AI) | Operational | WebBot + FileBot |
| Cross-system token-authenticated API sync | Operational | FileBot → WebBot |
| Analytics and tracking | Operational | Publish server (intranet) |
| Static publish pipeline (CDN-ready) | Operational | Publish server (intranet) |

### 10.1 Significance

> **Most CMS RFPs compare proposals against proposals. Ours is a working system ready for evaluation.**

This proposal does not ask the government to accept promises on faith. It invites independent verification of a working system — side by side with an existing AEM deployment — and evaluation of the comparative results.

### 10.2 Capabilities Available for Future Expansion (Separate RFPs)

These capabilities are already partially functional in the system and can be expanded via separate procurement:

| Feature | Current State |
|---|---|
| Enhanced public-facing Canada.ca search | Built-in hybrid search engine already operational; can be extended for public use |
| AI-powered content translation | AI models available; translation workflow can be automated |
| AI-powered content classification with bulk backfill | 29,304 pages classified; pipeline proven |
| Government-wide analytics | Tracking infrastructure in place; analytics dashboards extendable |
| Voice interface for AI Q&A | AI Q&A backend already running; voice frontend is additive |

> "Select us for the CMS today. Tomorrow's AI search, translation, and Q&A are already here."

---

## 11. Risk Mitigation

### 11.1 Risks & Responses

| Risk | Response |
|---|---|
| **"Your team is too small"** | Modern AI tooling enables a small, experienced team to build and maintain robust systems. Our architect has 20 years of Canada.ca experience, **holds a valid PSPC security clearance (10-year validity)**, and **Yuhong Web Inc.** has been operating since 2017. We partner with the existing Canada.ca team and can scale with contract support as deployment grows. |
| **"You worked on Canada.ca — conflict of interest"** | First 2 years: zero license fee. Only service fees. Independent operation after retirement. No financial lock-in. |
| **"Open source is not enterprise"** | PostgreSQL, FastAPI, and Mustache are proven in enterprise environments. Open source = no vendor lock-in, which is precisely what the government needs. |
| **"Migrating from AEM is risky"** | Zero-transformation migration: HTML in, HTML out. No component mapping. No data transformation. You can try a POC with one department in one day. |
| **"What about WCAG compliance?"** | GCWeb + WET are already compliant. Our editor enforces the same standards. Templates are HTML — no Java-generated markup to audit. |
| **"Our developers / contractors will lose work"** | On the contrary — our API-first design means developers can build **more** integrations, dashboards, and tools than ever before. Instead of maintaining AEM Java components, they build modern API-powered services. The work shifts from "keeping AEM running" to "building real government services." |
| **"Incumbent vendors (AEM, search) may resist"** | Our system does not require replacing anyone. Departments opt in on their own timeline. The performance and cost data — 2 hours vs. 3 minutes — makes the value proposition clear. We seek a constructive partnership with all existing ecosystem participants. |

### 11.2 Partnership Approach

Our strategy is partnership, not replacement:

- The Canada.ca team's content expertise is irreplaceable and remains essential
- Adopting our platform provides freedom from AEM vendor lock-in
- Component development time reduces from months to hours — enabling more meaningful work
- Existing CDN, load balancer, and publish infrastructure remain unchanged
- **No positions are eliminated. Roles are enhanced.**

---

## Appendix A: Key Statistics

| Metric | Enterprise CMS (Industry) | Our Platform |
|---|---|---|
| Annual cost | Industry standard | Fraction of enterprise pricing |
| Publish latency | Typically hours | ~3-5 minutes |
| Migration progress (10yr) | Typically limited | 100% (zero-transformation operation by AI) |
| Component development | 3-6 months | Hours |
| Search | Separate enterprise license | Built-in |
| AI Q&A | Not available | Built-in |
| Database | Proprietary repository | **Dual-database**: SQLite (editorial) + PostgreSQL + pgvector (assets/AI) |
| Pages imported & editable | N/A | **29,304 Canada.ca pages** (verified) |
| Import capability | Manual, per-page, component mapping needed | **Bookmarklet one-click** — dual-write to both databases |
| Team size (govt side) | 3-5 specialists | Partner with existing team |

## Appendix B: Live Services (as of June 2026)

| Service | Port | Status |
|---|---|---|
| WebBot (CMS Editor) | xxxx | Operational |
| FileBot (Assets + AI) | xxxx | Operational |
| Publish Preview | xxxx | Operational |
| PostgreSQL (pgvector) | xxxx | Operational |
| Search Index (29304 pages) | — | Indexed — 29,304 Canada.ca pages |
| AI Q&A (OpenAI + Ollama) | — | Both providers functional |
| Bookmarklet Import Tool | Browser bookmarklet `import-canada-ca` | Verified end-to-end (156 pages in one session) |

---

*This document describes a working system. The capabilities listed are not speculative — they are live and operational. We welcome the opportunity to demonstrate them.*
*The costs shown are estimates based on our platform's projected operation. All pricing is negotiable per GC procurement standards.*
