# LLM Integration Guide

This guide covers configuring and using LLM providers with the SDLC Agent system.

## Supported Providers

| Provider | Models | Best For |
|----------|--------|----------|
| **OpenAI** | GPT-4o, GPT-4-turbo, GPT-3.5-turbo | General use, code generation |
| **Azure OpenAI** | GPT-4o, GPT-4-turbo | Enterprise with compliance needs |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus | Complex reasoning, long context |
| **Google** | Gemini 1.5 Pro | Multi-modal, long context |

---

## Quick Setup

### 1. OpenAI (Recommended for Development)

```bash
# .env
OPENAI_API_KEY=sk-proj-...
OPENAI_ORG_ID=org-...  # Optional
```

### 2. Azure OpenAI (Recommended for Enterprise)

```bash
# .env
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
```

### 3. Anthropic Claude

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Agent Model Configuration

Each agent type can use a different model optimized for its task:

```python
# src/sdlc_agent/agents/config.py

AGENT_MODEL_CONFIG = {
    "orchestrator": {
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.1,  # Low for consistent planning
        "max_tokens": 4096,
    },
    "developer": {
        "provider": "openai", 
        "model": "gpt-4o",
        "temperature": 0.2,  # Slightly creative for code
        "max_tokens": 8192,
    },
    "reviewer": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "temperature": 0.0,  # Strict for reviews
        "max_tokens": 4096,
    },
    "tester": {
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "security": {
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.0,
        "max_tokens": 4096,
    },
}
```

---

## LangChain/LangGraph Integration

The system uses LangChain for LLM interactions:

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# OpenAI
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,
    api_key=settings.llm.openai_api_key,
)

# Anthropic
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    temperature=0.0,
    api_key=settings.llm.anthropic_api_key,
)

# Azure OpenAI
from langchain_openai import AzureChatOpenAI
llm = AzureChatOpenAI(
    azure_deployment=settings.llm.azure_openai_deployment_name,
    azure_endpoint=settings.llm.azure_openai_endpoint,
    api_key=settings.llm.azure_openai_api_key,
    api_version=settings.llm.azure_openai_api_version,
)
```

---

## Rate Limiting

Configure rate limits to avoid hitting API quotas:

```python
# src/sdlc_agent/core/config.py

class LLMSettings(BaseSettings):
    # Rate limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_tokens_per_minute: int = 150000
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    retry_exponential_backoff: bool = True
```

---

## Token Tracking

Track token usage for cost management:

```python
from langchain_community.callbacks import get_openai_callback

async def run_with_tracking(llm, prompt):
    with get_openai_callback() as cb:
        result = await llm.ainvoke(prompt)
        
    # Log usage
    logger.info(
        "LLM call completed",
        prompt_tokens=cb.prompt_tokens,
        completion_tokens=cb.completion_tokens,
        total_cost=cb.total_cost,
    )
    
    # Store in database for analytics
    await store_token_usage(cb)
    
    return result
```

---

## Fallback Configuration

Configure fallback providers for resilience:

```python
from langchain.llms.fallback import FallbackLLM

llm = FallbackLLM(
    llms=[
        ChatOpenAI(model="gpt-4o"),
        ChatAnthropic(model="claude-3-5-sonnet-20241022"),
        ChatOpenAI(model="gpt-3.5-turbo"),  # Fallback to cheaper model
    ]
)
```

---

## Embeddings

For vector memory (Qdrant):

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",  # 1536 dimensions
    api_key=settings.llm.openai_api_key,
)

# Or for Azure
from langchain_openai import AzureOpenAIEmbeddings
embeddings = AzureOpenAIEmbeddings(
    azure_deployment="text-embedding-3-small",
    azure_endpoint=settings.llm.azure_openai_endpoint,
)
```

---

## Testing LLM Configuration

```bash
# Test OpenAI connection
curl http://localhost:8000/api/v1/health/ready

# Test via Python
docker exec -it sdlc-api python -c "
from sdlc_agent.core.config import get_settings
from langchain_openai import ChatOpenAI

settings = get_settings()
llm = ChatOpenAI(model='gpt-4o', api_key=settings.llm.openai_api_key)
print(llm.invoke('Hello, respond with OK if working').content)
"
```

---

## Cost Optimization Tips

1. **Use GPT-4o-mini for simple tasks**: Classification, formatting
2. **Cache common responses**: Redis caching for repeated queries
3. **Batch requests**: Combine multiple small requests
4. **Stream responses**: For long-running generations
5. **Set max_tokens appropriately**: Avoid wasting tokens

---

## Troubleshooting

### "Rate limit exceeded"
- Increase `rate_limit_requests_per_minute` gradually
- Add exponential backoff
- Consider upgrading API tier

### "Context length exceeded"
- Truncate or summarize long inputs
- Use models with larger context (GPT-4-turbo: 128k, Claude: 200k)

### "Invalid API key"
- Verify key in `.env`
- Restart containers: `docker compose restart api worker`
- Check for trailing whitespace in keys
