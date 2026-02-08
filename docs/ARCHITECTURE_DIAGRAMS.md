# Voku Architecture Diagrams

> Visual documentation for v0.3 knowledge-first architecture.
> Last Updated: 2026-02-07

---

## 1. Graph Schema (Kuzu ER Diagram)

```mermaid
erDiagram
    ModuleNode {
        string id PK
        string title
        string content
        json intentions "primary, secondary[], definition_of_done, declared_priority"
        int priority
        int research_depth
        boolean active
        timestamp declared_at
        timestamp created_at
        timestamp updated_at
    }

    InternalNode {
        string id PK
        string title
        string content
        string status "confirmed | suggested | faded | rejected"
        string source "conversation | voku | user | import"
        float confidence
        string node_purpose "observation | pattern | belief | intention | decision"
        string source_type "explicit | inferred"
        string signal_valence "positive | negative | neutral"
        timestamp valid_from
        timestamp valid_to
        timestamp recorded_at
        timestamp suggested_at
        timestamp created_at
        timestamp updated_at
    }

    LeafNode {
        string id PK
        string title
        string content
        string status
        string source
        float confidence
        string node_purpose
        string source_type
        string signal_valence
        timestamp valid_from
        timestamp valid_to
        timestamp recorded_at
        timestamp suggested_at
        timestamp created_at
        timestamp updated_at
    }

    OrganizationNode {
        string id PK
        string type "compression | priority | pattern | hypothesis | keyword | bridge"
        string title
        string content
        float confidence
        timestamp valid_from
        timestamp valid_to
        timestamp created_at
    }

    NodeEmbedding {
        string id PK
        string node_id FK
        string embedding_type "content | title | context | query"
        float_768 embedding
        string model
        timestamp created_at
    }

    ModuleNode ||--o{ InternalNode : "CONTAINS"
    ModuleNode ||--o{ LeafNode : "CONTAINS"
    InternalNode ||--o{ InternalNode : "CONTAINS"
    InternalNode ||--o{ LeafNode : "CONTAINS"
    LeafNode ||--o{ LeafNode : "SUPPORTS"
    LeafNode ||--o{ InternalNode : "SUPPORTS"
    InternalNode ||--o{ InternalNode : "SUPPORTS"
    OrganizationNode ||--o{ LeafNode : "REFERENCES"
    OrganizationNode ||--o{ InternalNode : "REFERENCES"
```

---

## 2. Goal-Anchored Knowledge Flow

```mermaid
flowchart TB
    subgraph USER["User Space (What User Sees)"]
        subgraph MODULE["Modules (Goal Containers)"]
            fitness["fitness<br/>intention: Half marathon under 2 hours"]
            career["career<br/>intention: Software engineer role"]
        end

        subgraph INTERNAL["Internal Nodes (Abstractions)"]
            pattern1["pattern: I-underestimate-social-tasks<br/>source_type: inferred<br/>signal_valence: negative"]
            belief1["belief: networking-feels-inauthentic<br/>source_type: explicit"]
        end

        subgraph LEAF["Leaf Nodes (Extracted)"]
            obs1["observation: ran-5k-2430-jan28<br/>signal_valence: positive"]
            intent1["intention: want-sub-2hr-half-marathon<br/>source_type: explicit"]
            decision1["decision: chose-kuzu-over-sqlite"]
        end
    end

    subgraph ORG["Organization Space (Voku's Hidden Workspace)"]
        compress["Compression: weekly-summary"]
        hypo["Hypothesis: stated-vs-revealed-gap"]
        keyword["Keyword: vertical-pull → compound-movement"]
    end

    MODULE --> INTERNAL
    INTERNAL --> LEAF
    ORG -.->|proposes| INTERNAL
    ORG -.->|detects patterns| LEAF

    hypo -.->|surfaces| pattern1
```

---

## 3. Stated vs Revealed: Core Query Pattern

```mermaid
flowchart LR
    subgraph STATED["What You Say You Want"]
        s1["intention: want-software-engineer-job<br/>source_type: explicit"]
        s2["intention: prioritize-interview-prep<br/>source_type: explicit"]
    end

    subgraph REVEALED["What Behavior Shows"]
        r1["pattern: 40hrs-on-side-projects-0hrs-leetcode<br/>source_type: inferred"]
        r2["pattern: avoids-networking-tasks<br/>source_type: inferred"]
    end

    subgraph VOKU["Voku Surfaces"]
        gap["🔍 Gap Detected:<br/>Stated priority ≠ Time allocation"]
    end

    STATED --> gap
    REVEALED --> gap
```

---

## 4. System Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React + TypeScript)"]
        chat[Chat Interface]
        graph[Graph Visualization]
    end

    subgraph Backend["Backend (FastAPI)"]
        router[Chat Router]
        chat_svc[ChatService]
        extract_svc[ExtractionService]
        embed_svc[EmbeddingService]
    end

    subgraph Graph["Graph Layer"]
        graph_ops[GraphOperations]
        kuzu[(Kuzu 0.11.3<br/>ModuleNode / InternalNode / LeafNode<br/>OrganizationNode / NodeEmbedding)]
    end

    subgraph LLM["LLM Providers"]
        groq[Groq API<br/>llama-3.3-70b]
        ollama[Ollama<br/>Local Models]
    end

    subgraph Embeddings["Embedding Model"]
        bge[bge-base-en-v1.5<br/>768-dim vectors]
    end

    chat --> router
    graph --> router
    router --> chat_svc
    chat_svc --> extract_svc
    chat_svc --> embed_svc
    chat_svc --> graph_ops
    extract_svc --> groq
    extract_svc --> ollama
    embed_svc --> bge
    graph_ops --> kuzu
```

---

## 5. Data Flow: Conversation → Graph

```mermaid
sequenceDiagram
    participant U as User
    participant C as Chat UI
    participant B as ChatService
    participant L as ExtractionService
    participant E as EmbeddingService
    participant G as GraphOperations
    participant K as Kuzu

    U->>C: "I'm anxious about the co-op search"
    C->>B: POST /api/chat/
    B->>L: extract(text)
    L->>L: LLM call (Groq)
    L-->>B: [Proposition, Proposition, ...]

    loop For each proposition
        B->>E: embed(proposition.text)
        E-->>B: 768-dim vector
        B->>G: find_similar_nodes(vector, threshold=0.95)
        G->>K: Query NodeEmbedding table
        K-->>G: Similar nodes (if any)
        G-->>B: Matches above threshold

        alt No duplicate found
            B->>G: create_leaf_node(proposition)
            G->>K: CREATE LeafNode
            B->>G: store_embedding(node_id, vector)
            G->>K: CREATE NodeEmbedding
        else Duplicate found (similarity > 0.95)
            B->>B: Skip creation, increment duplicates_found
        end
    end

    B-->>C: ProcessedMessage {node_ids, propositions, duplicates_found}
    C-->>U: Nodes appear in graph
```

---

## 6. Organization Layer Flow (Planned)

```mermaid
flowchart LR
    subgraph Input["Raw Input (Daily)"]
        s1[session 1]
        s2[session 2]
        s3[session 3]
    end

    subgraph Org["Organization Layer (Voku)"]
        compress[Compress]
        prioritize[Prioritize]
        cluster[Cluster Patterns]
    end

    subgraph Output["User View"]
        weekly[Weekly Summary]
        queue[Priority Queue]
        insights[Cross-Domain Insights]
    end

    s1 --> compress
    s2 --> compress
    s3 --> compress

    compress --> weekly
    compress --> prioritize
    prioritize --> queue
    compress --> cluster
    cluster --> insights
```

---

## Quick Reference

| Diagram | Purpose | Interview Use |
|---------|---------|---------------|
| Graph Schema | Kuzu data model with embedding table | "Here's the data model — 4 node types, 6 edge types, vector storage" |
| Goal-Anchored Flow | How intentions flow through the system | "This is what makes it personal, not a knowledge base" |
| Stated vs Revealed | Core value proposition | "Voku surfaces where stated intentions ≠ observed patterns" |
| System Architecture | Full stack overview | "Here's how services compose — extraction, embedding, graph ops" |
| Data Flow | Runtime pipeline with dedup | "Here's the per-turn pipeline: extract → embed → dedup → store" |
| Organization Layer | Hidden cognitive workspace (planned) | "Phase 2: batch clustering proposes abstractions from leaves" |
