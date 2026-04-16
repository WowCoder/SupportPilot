## gstack

Use /browse from gstack for all web browsing. Never use mcp__claude-in-chrome__* tools.

Available skills:
- **Think/Plan**: `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`
- **Build/Review**: `/review`, `/design-review`, `/investigate`, `/codex`
- **Test/QA**: `/qa`, `/qa-only`, `/browse`, `/setup-browser-cookies`
- **Ship**: `/ship`, `/document-release`, `/retro`
- **Safety**: `/careful`, `/freeze`, `/guard`, `/unfreeze`
- **Maintenance**: `/gstack-upgrade`

If gstack skills aren't working, run `cd .claude/skills/gstack && ./setup` to build the binary and register skills.

## Agentic RAG Architecture

SupportPilot uses an Agentic RAG system with LangGraph orchestration. Key components:

### Architecture
- **Query Router**: Routes queries to simple or agentic path based on keywords/patterns
- **Retrieval Agent**: LangGraph state machine (query_understanding → planning → tool_execution → synthesis)
- **Tools**: vector_search, bm25_search, metadata_filter, ensemble_retrieval (RRF fusion)
- **Small-to-Big**: Default retrieval strategy (small chunks for indexing, large chunks for return)

### File Locations
- `rag/core/`: Core modules (tool.py, container.py, config.py, observability.py)
- `rag/tools/`: Retrieval tools (vector_tool.py, bm25_tool.py, filter_tool.py, ensemble_tool.py)
- `rag/agents/`: Agent and router (retrieval_agent.py, router.py, states.py, nodes/*)
- `config/rag_config.yaml`: Configuration (agent settings, tool params, Small-to-Big sizes)

### Usage
```python
# Simple retrieval with auto-routing
from rag.service import rag_service
results = rag_service.retrieve(query="高并发的原则", k=5, use_small_to_big=True)

# Direct agentic retrieval
from rag.agents.retrieval_agent import retrieval_agent
result = retrieval_agent.run(query="对比 A 和 B", session_id="conv_123")
```

### Key Decisions
- Chat memory system stays independent (QueryRewriter in app/services/ retained)
- rag_utils.py kept for document processing (ingestion), not retrieval
- Timeout protection and iteration limits built into agent
