# PrismBB Genomics: Clinical Variant Interpretation Workspace
**Full Project Documentation**

---

## 1. Executive Overview

PrismBB Genomics is an end-to-end, locally-hostable multi-agent bioinformatics platform designed to accelerate and secure the interpretation of clinical genomic sequencing data (VCF files). Unlike traditional purely generative AI wrappers that are prone to hallucinating clinical facts, this platform uses a deeply grounded **hybrid pipeline architecture**:

1. **Deterministic Baseline:** Strict, mathematical variant normalization, annotation, and ranking using established biological databases (Ensembl VEP, gnomAD, ClinVar, PanelApp, OMIM).
2. **Agentic Copilot:** An autonomous multi-agent system powered by the Gemini 2.0 Flash and DeepMind AlphaGenome APIs that strictly reads from the immutable SQL database to answer queries, fetch real-time PubMed literature, and predict regulatory effects without guessing variant constraints.

## 2. Core Features & Capabilities

### 2.1 Drag-and-Drop VCF Ingestion
*   Validates `.vcf` and `.vcf.gz` formatting, parsing the `#CHROM` headers.
*   Supports user-provided **Target Gene Lists** (e.g., *BRCA1, TP53*) and **Clinical HPO Phenotypes** (e.g., *HP:0001250*) to drive phenotype-aware prioritization.
*   Automatically detects genome build (GRCh38 vs. GRCh37).
*   Utilizes `bcftools` to proactively split multi-allelic variants and left-align INDELs before downstream processing.

### 2.2 Advanced Deterministic Annotation
Variants are pushed through a rigorous local or REST-based pipeline:
*   **Ensembl VEP:** Extracts canonical transcripts, HGVS.c/p notations, consequence classifications, and functional impacts.
*   **gnomAD Population Frequencies:** Filters out common benign polymorphisms (AF > 1%).
*   **ClinVar Integration:** Anchors variants with known, peer-reviewed clinical significance (Pathogenic / Benign).
*   **Genomics England PanelApp:** Connects variants to their officially recognized gene-disease panels.

### 2.3 The 6-Factor Composite Ranking Engine
Instead of dumping thousands of variants on a clinician, the system mathematically scores and sorts candidates:
*   **Rarity (25%):** Ultra-rare or novel variants score higher than variants seen globally.
*   **Transcript Impact (25%):** High-impact structural changes (stop-gains, frameshifts) take precedence.
*   **Clinical Evidence (20%):** Known ClinVar Pathogenic variants receive a massive boost.
*   **Phenotype Match (15%):** If a variant intercepts a gene associated with the patient's provided HPO terms, it ranks higher.
*   **Inheritance Patterns (10%):** Homozygous variants in recessive genes.
*   **Panel Evidence (5%):** High-confidence (Green) PanelApp gene membership.

### 2.4 Google DeepMind AlphaGenome Integration
As part of our advanced toolset, the platform integrates **Google's AlphaGenome API**. 
*   **Purpose:** Deep-learning inference for non-coding, unclassified, and intronic variants where standard VEP struggles.
*   **Capabilities:** Predicts splicing disruption, transcription factor binding site (TFBS) loss, and chromatin accessibility changes.

### 2.5 Multi-Agent System (Gemini 2.0 Flash)
The conversational "Copilot" chat interface is an orchestration of specialized autonomous agents:
*   **Orchestrator Agent:** Maintains conversational state and intelligently routes distinct scientific queries to its sub-agents via function declarations (Tool Calling).
*   **Literature Agent:** Constructs programmatic HTTP requests to the NCBI E-utilities API to pull the latest primary literature (PubMed) regarding a specific gene-phenotype interaction.
*   **AlphaGenome Agent:** Connects to the newest DeepMind pathways for variant effect prediction.
*   **Reporting Agent:** Compiles structured, clinician-ready export drafts documenting the evidence for the highest-priority variants.

### 2.6 Ultra-Clean Clinical UI
The overarching frontend follows a strict **minimalist, clinical light-mode design**:
*   Deep slate text (`#0F172A`) against pure white and light-slate surfaces ensures maximum data legibility.
*   **Dynamic Landing Page:** A sophisticated 2-column layout guiding the user to upload VCFs alongside an infinite-sliding logo track of the integrated data sources.
*   **Variant Detail Views:** Clear, grid-based breakdown of population frequencies, prediction scores, and exact genomic coordinates.

---

## 3. Technology Stack & Architecture

### Backend (Python)
*   **Framework:** FastAPI (Asynchronous Python 3.10+).
*   **Database:** PostgreSQL 15, managed via SQLAlchemy (asyncpg engine).
*   **Agent Orchestration:** Google Generative AI SDK (`google-generativeai`) configured with structured tool calling.
*   **Bioinformatics Tools:** Base VCF ingestion leverages custom python iterators paired strictly with `bcftools` subprocesses. External lookups rely on `httpx`.

### Frontend (TypeScript)
*   **Framework:** Next.js 14+ (App Router).
*   **Styling:** Tailwind CSS with a custom set of CSS variables (`globals.css`) tuned explicitly for high-contrast hospital-grade dashboards.
*   **Animations:** Framer Motion (`motion/react`) used for fluid state transitions and the floating dashboard effects.
*   **Icons:** Lucide React.
*   **Charts:** Recharts for dynamic visual distribution of variant impacts.

### Infrastructure
*   **Deployment:** Docker Compose handles the orchestration of the Postgres DB, FastAPI app, NextJS UI app, and an internal Redis task queue.
*   **Security:** APIs communicate with Next.js securely within the Docker network context. Local database constraints ensure HIPPA-friendly compliance (no VCF data is ever stored remotely).

---

## 4. Database Schema Structure
The `vcfdb` database operates under a standard relational structure:

1.  **`jobs` Table:** Tracks the upload sessions. Stores VCF file metadata, job state (`PENDING`, `ANNOTATING`, `COMPLETED`), phenotype inputs, and high-level QC statistics (total variants, transition/transversion ratio).
2.  **`variants` Table:** The core massive storage unit. Represents standard parsed VCF records appended with the 6-factor ranking score, VEP transcript impacts, ClinVar links, and computed genotypes. Maps via `job_id` foreign keys.
3.  **`annotations` Table:** (Optional caching) Caches raw JSON text from Ensembl or NCBI to prevent API rate-limiting on identical coordinates.
4.  **`audit_logs` Table:** An immutable ledger ensuring every computational step applied to a `job_id` is recorded over time (e.g., "Filtered 1,200 common SNPs", "Invoked AlphaGenome for Intron-5").

---

## 5. Development Setup & Execution

1.  **Environment Variables (`.env`)**
    ```env
    POSTGRES_USER=vcf
    POSTGRES_PASSWORD=vcfpass
    POSTGRES_DB=vcfdb
    GEMINI_API_KEY=AIzaSy...
    ALPHAGENOME_API_KEY=AIzaSy...
    NCBI_API_KEY=optional_key
    ```
2.  **Run System via Docker Compose**
    ```bash
    docker-compose up --build
    ```
3.  **Access points:**
    *   **Clinical Interface:** `http://localhost:3000`
    *   **Backend API Swagger:** `http://localhost:8000/docs`
    *   **Postgres DB:** `localhost:5432`

---

*This document serves as the master specification defining the capabilities, architecture, and purpose of the PrismBB Genomics VCF Interpretation Agent codebase.*
