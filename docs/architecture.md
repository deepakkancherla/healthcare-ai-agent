# Architecture

The Healthcare AI Agent uses a layered architecture. The Streamlit frontend is
an API client and does not access the agent or OpenAI directly. FastAPI validates
requests and delegates them to the singleton `HealthcareAgent`, which coordinates
LLM reasoning and registered healthcare tools.

## System Components

```mermaid
flowchart TD
    User[User] --> Streamlit[Streamlit]
    Streamlit -->|POST /chat| FastAPI[FastAPI]
    FastAPI --> HealthcareAgent[HealthcareAgent]
    HealthcareAgent --> ToolRegistry[Tool Registry]
    ToolRegistry --> ProviderSearch[Provider Search Tool]
    ToolRegistry --> Insurance[Insurance Verification Tool]
    ToolRegistry --> Appointment[Appointment Booking Tool]
```

## Request and Tool Execution Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit
    participant API as FastAPI
    participant Agent as HealthcareAgent
    participant Registry as Tool Registry
    participant Tools as Healthcare Tools

    User->>UI: Submit healthcare request
    UI->>API: POST /chat
    API->>Agent: chat(message)

    loop Until the user's goal is complete
        Agent->>Agent: Evaluate known and missing information
        Agent->>Registry: Execute requested tool
        Registry->>Tools: Validate input and invoke handler
        Tools-->>Registry: Structured result
        Registry-->>Agent: Tool result
        Agent->>Agent: Reassess goal
    end

    Agent-->>API: Final assistant response
    API-->>UI: JSON response
    UI-->>User: Display assistant message
```

## Configuration

Runtime configuration is loaded from environment variables, with local `.env`
support:

- `OPENAI_API_KEY` authenticates the backend OpenAI client.
- `BACKEND_URL` tells Streamlit where to reach FastAPI.

The service version is `1.0.0` and is exposed by the root health endpoint and
the generated OpenAPI schema.
