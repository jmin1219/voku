# Voku Architecture Diagrams

> Visual documentation for v0.3 knowledge-first architecture.
> Last Updated: 2026-01-31

---

## 1. Graph Schema (Kuzu ER Diagram)

```mermaid
erDiagram
    RootNode {
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
    
    RootNode ||--o{ InternalNode : "CONTAINS"
    RootNode ||--o{ LeafNode : "CONTAINS"
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

## 3. System Architecture (Full Stack)

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React + TypeScript)"]
        chat[Chat Interface]
        graph[Graph View]
        pages[Domain Pages]
    end
    
    subgraph Backend["Backend (FastAPI)"]
        routers[Routers]
        services[Services]
        extraction[LLM Extraction]
    end
    
    subgraph Storage["Storage Layer"]
        subgraph SQLite["voku.db (SQLite)"]
            nodes_table[(nodes)]
            edges_table[(edges)]
            templates_table[(templates)]
            transactions[(transactions)]
            merchants[(merchants)]
        end
        sessions_json[JSON Sessions]
        registry[Variable Registry]
    end
    
    subgraph LLM["LLM Providers"]
        groq[Groq API]
        ollama[Ollama Local]
    end
    
    chat --> routers
    graph --> routers
    pages --> routers
    
    routers --> services
    services --> extraction
    services --> SQLite
    services --> sessions_json
    services --> registry
    
    extraction --> groq
    extraction --> ollama
```

---

## 4. Data Flow: Conversation → Graph

```mermaid
sequenceDiagram
    participant U as User
    participant C as Chat UI
    participant B as Backend
    participant L as LLM
    participant G as Graph DB
    
    U->>C: "Finished 5K run at 24:30"
    C->>B: POST /chat/message
    B->>L: Extract structured data
    L-->>B: {type: "session", domain: "fitness", metrics: {...}}
    
    B->>G: Create basic node
    Note over G: session-2026-01-30-2k-row
    
    B->>G: Create edges
    Note over G: fitness --contains--> session
    Note over G: plan-12-week --references--> session
    
    B->>B: Batch update (every few seconds)
    B-->>C: Updated graph state
    C-->>U: Node appears in graph view
```

---

## 5. Organization Layer Flow

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
| Graph Schema | Kuzu data model with goal-anchored fields | "Here's the technical implementation" |
| Goal-Anchored Flow | How intentions flow through the system | "This is what makes it personal, not a knowledge base" |
| Stated vs Revealed | Core value proposition | "Voku surfaces self-deception — where stated ≠ revealed" |
| System Architecture | Full stack overview | "Here's how it all connects" |
| Data Flow | Runtime behavior | "Here's what happens when you chat" |
| Organization Layer | Hidden cognitive workspace | "Voku reasons before proposing" |
