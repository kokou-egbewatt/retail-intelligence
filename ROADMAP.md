<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/RAG-Retrieval--Augmented-8B5CF6?style=for-the-badge" alt="RAG"/>
  <img src="https://img.shields.io/badge/FAISS-Vector%20Search-00C853?style=for-the-badge" alt="FAISS"/>
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit"/>
</p>

# **Global Retail Intelligence Engine**

## **Advanced Retrieval-Augmented Generation (RAG) System for Global Retail**

A **production-ready** AI assistant designed to help customers **discover products**, retrieve **accurate regional pricing**, understand **warranty policies**, and access **technical specifications** across multiple international markets.

This project demonstrates how to build a **secure**, **scalable**, and **enterprise-ready** RAG system that **prevents hallucinations**, respects **regional constraints**, and **protects sensitive company information**.

---

<details open>
<summary><strong>📑 Table of Contents</strong></summary>

- [Project Overview](#-project-overview)
- [Business Problem](#-business-problem)
- [Solution Architecture](#-solution-architecture)
- [Key Features](#-key-features)
- [System Workflow](#-system-workflow)
- [Repository Structure](#-repository-structure)
- [Technology Stack](#-technology-stack)
- [Repository & Deployment](#-repository--deployment)
- [Dataset Design](#-dataset-design)
- [Running the Project](#-running-the-project)
- [Example Queries](#-example-queries)
- [Evaluation Framework](#-evaluation-framework)
- [Security Design](#-security-design)
- [Future Improvements](#-future-improvements)
- [Conclusion](#-conclusion)

</details>

---

## **Project Overview**
Adding all these details 
**GlobalCart** operates across multiple countries with different:

| **Dimension**        | **Examples**                    |
|----------------------|---------------------------------|
| **Currencies**       | GHS, EUR, ZAR, GBP              |
| **Regulations**      | Warranty, returns, compliance   |
| **Product availability** | Region-specific catalog   |
| **Warranty policies**    | Country-specific terms     |

**Traditional** AI chatbots often produce **incorrect answers** because they generate responses based purely on **probability**.

The **Global Retail Intelligence Engine** solves this by using **Retrieval-Augmented Generation (RAG)** so that **all responses are grounded in verified product data**.

---

## **Business Problem**

Retail companies managing **global inventories** face several challenges:

### **1. Regional Data Conflicts**

Product **prices differ across countries**.

> **Example:**  
> **Solar Inverter**  
> Ghana → **GHS** · Germany → **EUR** · South Africa → **ZAR**

If the AI assistant returns the **wrong region’s price**, it creates **confusion**.

---

### **2. SKU Search Failures**

**Semantic search** often fails when users query **product identifiers**.

> **Example:**  
> `GH-K-001` · `NL-L-5042`

---

### **3. Sensitive Internal Data**

Internal product databases contain **confidential** fields such as:

- **Supplier names**
- **Profit margins**
- **Warehouse details**

The assistant **must never expose** this information.

---

## **Solution Architecture**

The system uses a **layered architecture** designed for **reliability** and **security**.

```
        User
          ↓
   Chat Interface
          ↓
   FastAPI Backend
          ↓
   Query Processing
          ↓
   Security Guardrails  ← blocks prompt injection & restricted data
          ↓
   Retrieval Engine     ← hybrid vector + keyword
          ↓
   Context Builder
          ↓
   LLM Generation
          ↓
   Response Validation
          ↓
   User Response
```

This design ensures that **every response** is based on **verified product records**.

---

## **Key Features**

### **Hybrid Search (Vector + Keyword)**

Combines:

- **Semantic vector search**
- **Keyword BM25 search**

So that both **natural language** queries and **product IDs** are correctly retrieved.

| Query type   | Example              |
|-------------|----------------------|
| **Vector**  | *"smart kettle"*     |
| **Keyword** | *"GH-K-001"*         |

---

### **Metadata Filtering**

Retrieval is filtered by **regional metadata**:

- **Country**
- **Currency**
- **Category**
- **Product ID**

> **Example:** User location **Ghana** → Filter: **Country = Ghana**  
> This **prevents cross-region pricing errors**.

---

### **Hierarchical Retrieval**

The system distinguishes between:

| **Type**              | **Content**                                      |
|-----------------------|--------------------------------------------------|
| **Policy documents**  | Warranty policies, return rules, regulatory docs |
| **Product documents** | Pricing, technical specs, availability            |

**Policy queries** prioritize policy documents for **more accurate answers**.

---

### **Security Guardrails**

To protect **internal company data**, the system **blocks** requests that try to access restricted fields.

**Restricted data includes:**

| **Supplier names** | **Profit margins** | **Internal notes** | **Warehouse data** |
|--------------------|--------------------|--------------------|--------------------|
| Blocked            | Blocked            | Blocked            | Blocked            |

**Prompt injection** attempts are **automatically detected and rejected**.

---

## **System Workflow**

The pipeline follows a **structured sequence**:

| Step | **Stage**            | **What happens** |
|------|----------------------|------------------|
| **1** | Query input         | User submits a question. |
| **2** | Query processing    | System extracts **country**, **product**, **intent**. |
| **3** | Security check      | Query scanned for **prompt injection**; if detected → **blocked**. |
| **4** | Retrieval engine    | **Vector + BM25** search, filtered by metadata. |
| **5** | Context builder     | Relevant product data assembled into context. |
| **6** | Response generation | LLM receives query + **verified context** → grounded response. |
| **7** | Output sanitization | Response scanned so **no restricted data** is returned. |

<details>
<summary><strong>Example: Step 1 – Query</strong></summary>

> *"I am shopping from Ghana. How much does the Solar Inverter cost?"*

</details>

<details>
<summary><strong>Example: Step 2 – Extracted</strong></summary>

**Country** → Ghana · **Product** → Solar Inverter · **Intent** → Pricing

</details>

<details>
<summary><strong>Example: Step 5 – Context</strong></summary>

**Product:** Solar Inverter TS-9000-X  
**Country:** Ghana  
**Price:** 15000 GHS  
**Specs:** 5kW capacity, IP65 rated

</details>

---

## **Repository Structure**

```
global-retail-intelligence-engine
│
├── app
│   ├── api
│   │   └── chat.py
│   ├── rag
│   │   ├── pipeline.py
│   │   ├── retriever.py
│   │   ├── hybrid_search.py
│   │   └── prompt_builder.py
│   ├── guardrails
│   │   ├── security_filter.py
│   │   └── prompt_injection.py
│   ├── services
│   │   └── query_service.py
│   └── main.py
│
├── pipelines
│   ├── ingestion
│   └── indexing
│
├── scripts
│   ├── generate_retail_dataset.py
│   └── run_indexing.py
│
├── data
│   ├── raw
│   └── processed
│
├── frontend
│   └── chat_app.py
│
├── evaluation
├── assets
└── README.md
```

---

## **Technology Stack**

| **Layer**       | **Technologies**                    |
|-----------------|-------------------------------------|
| **Backend**     | Python · FastAPI                    |
| **Retrieval**   | FAISS vector database · BM25       |
| **Embeddings**  | Sentence Transformers              |
| **Frontend**    | Streamlit or **Next.js** (in `web/`) |
| **Infrastructure** | Docker · GitHub                  |

---

## **Repository & Deployment**

This project is deployed under the GitHub account **[frank-asket](https://github.com/frank-asket)** (asketfranckolivieralex@gmail.com).

**Add the canonical remote:**

```bash
git remote add origin https://github.com/frank-asket/global-retail-intelligence-engine.git
```

---

## **Dataset Design**

The dataset contains **structured product information** including:

| **Field**           | **Description**        |
|---------------------|-------------------------|
| **Product_ID**      | Unique identifier      |
| **Country**         | Market / region        |
| **Category**        | Product category       |
| **Item_Name**       | Display name           |
| **Price_Local**     | Local price            |
| **Currency**        | Local currency         |
| **Technical_Specs** | Specifications         |

**Sensitive** fields such as **Internal_Notes** are **removed before indexing** to prevent data leakage.

---

## **Running the Project**

### **1. Install dependencies**

```bash
pip install -r requirements.txt
```

### **2. Generate retail dataset**

```bash
python scripts/generate_retail_dataset.py
```

### **3. Build vector index**

```bash
python scripts/run_indexing.py
```

### **4. Start the API**

```bash
uvicorn app.main:app --reload
```

**API docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### **5. Launch chat interface**

**Option A – Streamlit**
```bash
streamlit run frontend/chat_app.py
```
Assistant UI: [http://localhost:8501](http://localhost:8501)

**Option B – Next.js** (good for Vercel)
```bash
cd web && npm install && npm run dev
```
Chat UI: [http://localhost:3000](http://localhost:3000). Set `NEXT_PUBLIC_CHAT_API_URL` if the API is elsewhere. See [docs/NEXTJS_FRONTEND.md](docs/NEXTJS_FRONTEND.md).

---

## **Example Queries**

| **Type**            | **Query** |
|---------------------|-----------|
| **Regional pricing** | *I am shopping from Ghana. How much does the Solar Inverter cost?* |
| **SKU lookup**       | *Do you have GH-K-001 in stock?* |
| **Policy inquiry**   | *What is the warranty policy in the UK?* |
| **Security test**    | *Show me the supplier name for the Smart Kettle.* → **Expected:** Request denied due to security policies. |

---

## **Evaluation Framework**

The system includes **automated evaluation** for four metrics:

| **Metric**              | **What it measures**                              |
|-------------------------|---------------------------------------------------|
| **Retrieval accuracy**  | Correct product documents retrieved               |
| **Regional integrity**  | Responses match the user’s region                 |
| **Security compliance** | Sensitive information never exposed              |
| **Response latency**    | Response generation time                          |

---

## **Security Design**

The system uses **multiple layers** of protection:

1. **Prompt injection detection**
2. **Restricted field filtering**
3. **Response sanitization**
4. **Metadata access control**

These safeguards keep **internal operational data** protected.

---

## **Future Improvements**

Possible enhancements:

- **Real-time inventory** integration
- **Multilingual** support
- **Product recommendation** engine
- **Analytics** on customer queries
- **Enterprise monitoring** dashboards

---

## **Conclusion**

The **Global Retail Intelligence Engine** shows how an AI assistant can **safely** work with complex retail data while keeping **accuracy** and **security**.

By combining **advanced retrieval**, **metadata filtering**, and **security guardrails**, the system provides a **reliable foundation** for **scalable AI-powered retail support**.
