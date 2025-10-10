# Web Search Tool - Enhanced Edition

## Description
Advanced web search with Brave Search API featuring content extraction, filtering, custom ranking, and deep search capabilities.

## Features
- **Cluster Content Extraction**: Extracts related content from Brave's cluster field (up to 5 additional descriptions per result from related pages on the same domain)
- **Freshness Filtering**: Filter results by time (last day, week, month, year)
- **Result Type Filtering**: Target specific content types (news, videos, discussions, FAQ)
- **Custom Ranking (Goggles)**: Pre-defined ranking profiles for academic, technical, or news sources
- **Deep Search**: Multi-strategy search with query expansion for comprehensive results
- **Multi-format Results**: Automatically includes web pages, news articles, videos, and infoboxes

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query text |
| `count` | integer | 10 | Number of results (max: 20) |
| `freshness` | string | null | Time filter: `day`, `week`, `month`, `year` |
| `result_filter` | string | null | Result type: `news`, `videos`, `discussions`, `faq` |
| `goggle_type` | string | null | Ranking profile: `academic`, `technical`, `news` |
| `extra_snippets` | boolean | true | Request cluster data (related pages) from Brave API for richer content |
| `deep_search` | boolean | false | Enable deep search with query expansion |

## Output Format

### Standard Search Response
```json
{
  "status": "success",
  "action": "web_search",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "success": true,
    "query": "search query",
    "total": 10,
    "results": [
      {
        "title": "Result title",
        "url": "https://example.com",
        "snippet": "Brief description",
        "score": 0.95,
        "type": "web|news|video|infobox",
        "all_content": "Combined: title + snippet + cluster descriptions + meta_description (up to 500 chars)"
      }
    ],
    "urls": ["list", "of", "urls"],
    "search_params": {
      "freshness": "SearchFreshness.DAY",
      "filter": "ResultFilter.NEWS",
      "goggle": "technical",
      "extra_snippets": true,
      "count": 10
    }
  }
}
```

### Deep Search Response
```json
{
  "status": "success",
  "action": "web_search",
  "data": {
    "success": true,
    "query": "original query",
    "total": 25,
    "results": [...],
    "search_type": "deep",
    "urls": [...]
  }
}
```

## Error Response
```json
{
  "status": "error",
  "action": "web_search",
  "timestamp": "2024-01-01T12:00:00Z",
  "error_message": "Error description"
}
```

## Usage Examples (With Real Data)

### 1. Basic Search
```python
result = await client.call_tool("web_search", {
    "query": "Python programming"
})
```

**Actual Response:**
```json
{
  "status": "success",
  "action": "web_search",
  "data": {
    "success": true,
    "query": "Python programming",
    "total": 10,
    "results": [
      {
        "title": "Welcome to Python.org",
        "url": "https://www.python.org/",
        "snippet": "The official home of the <strong>Python</strong> <strong>Programming</strong> Language",
        "score": 1.0
      },
      {
        "title": "Python (programming language) - Wikipedia",
        "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "snippet": "<strong>Python</strong> is a high-level, general-purpose <strong>programming</strong> language...",
        "score": 0.6
      }
    ]
  }
}
```

### 2. Fresh News Search (Last 24 Hours)
```python
result = await client.call_tool("web_search", {
    "query": "artificial intelligence",
    "freshness": "day",
    "result_filter": "news",
    "count": 5
})
```

**Actual Response:**
```json
{
  "status": "success",
  "data": {
    "query": "artificial intelligence",
    "total": 5,
    "results": [
      {
        "title": "What Is Artificial Intelligence (AI)? | IBM",
        "url": "https://www.ibm.com/think/topics/artificial-intelligence",
        "snippet": "<strong>Artificial</strong> <strong>intelligence</strong> (AI) is technology that enables computers...",
        "score": 0.9
      },
      {
        "title": "AI for feedback: what to keep in mind when developing your own tool",
        "url": "https://www.timeshighereducation.com/campus/ai-feedback-what-keep-mind-when-developing-your-own-tool",
        "snippet": "A lack of communication skills often leaves UK graduates feeling 'naked in the workplace'...",
        "score": 0.6
      }
    ]
  }
}
```

### 3. Academic Research
```python
result = await client.call_tool("web_search", {
    "query": "machine learning algorithms",
    "goggle_type": "academic",
    "extra_snippets": true
})
```

**Actual Response:**
```json
{
  "status": "success",
  "data": {
    "query": "machine learning algorithms",
    "total": 5,
    "results": [
      {
        "title": "What Is a Machine Learning Algorithm? | IBM",
        "url": "https://www.ibm.com/think/topics/machine-learning-algorithms",
        "snippet": "A machine learning algorithm is <strong>a set of rules or processes used by an AI system to conduct tasks</strong>...",
        "score": 0.9
      },
      {
        "title": "10 Machine Learning Algorithms to Know in 2025 | Coursera",
        "url": "https://www.coursera.org/articles/machine-learning-algorithms",
        "snippet": "<strong>Machine</strong> <strong>learning</strong> <strong>algorithms</strong> power many services in the...",
        "score": 0.7
      }
    ]
  }
}
```

### 4. Technical Documentation
```python
result = await client.call_tool("web_search", {
    "query": "React hooks tutorial",
    "goggle_type": "technical",
    "freshness": "month"
})
```

**Actual Response:**
```json
{
  "status": "success",
  "data": {
    "query": "React hooks tutorial",
    "total": 5,
    "results": [
      {
        "title": "React Hooks",
        "url": "https://www.w3schools.com/react/react_hooks.asp",
        "snippet": "Note: <strong>Hooks</strong> will not work in <strong>React</strong> class components...",
        "score": 1.0
      },
      {
        "title": "Built-in React Hooks – React",
        "url": "https://react.dev/reference/react/hooks",
        "snippet": "<strong>Hooks</strong> let you use different <strong>React</strong> features from your components...",
        "score": 0.9
      },
      {
        "title": "How to Use React Hooks – Full Tutorial for Beginners",
        "url": "https://www.freecodecamp.org/news/full-guide-to-react-hooks/",
        "snippet": "Hi everyone! <strong>Hooks</strong> are one of the main features of modern <strong>React</strong> code...",
        "score": 0.8
      }
    ]
  }
}
```

### 5. Video Search
```python
result = await client.call_tool("web_search", {
    "query": "Python tutorial",
    "result_filter": "videos",
    "count": 5
})
```

**Actual Response:**
```json
{
  "status": "success",
  "data": {
    "query": "Python tutorial",
    "total": 5,
    "results": [
      {
        "title": "The Python Tutorial — Python 3.13.7 documentation",
        "url": "https://docs.python.org/3/tutorial/index.html",
        "snippet": "<strong>Python</strong> is an easy to learn, powerful programming language...",
        "score": 1.0
      },
      {
        "title": "Python Tutorial",
        "url": "https://www.w3schools.com/python/",
        "snippet": "W3Schools offers free online <strong>tutorials</strong>, references and exercises...",
        "score": 0.9
      },
      {
        "title": "Learn Python - Free Interactive Python Tutorial",
        "url": "https://www.learnpython.org/",
        "snippet": "learnpython.org is a free interactive <strong>Python</strong> <strong>tutorial</strong> for people who want to learn <strong>Python</strong>, fast.",
        "score": 0.6
      }
    ]
  }
}
```

### 6. Recent Discussions
```python
result = await client.call_tool("web_search", {
    "query": "ChatGPT alternatives",
    "result_filter": "discussions",
    "freshness": "week"
})
```

**Actual Response:**
```json
{
  "status": "success",
  "data": {
    "query": "ChatGPT alternatives",
    "total": 10,
    "results": [
      {
        "title": "The 9 best ChatGPT alternatives in 2025 | Zapier",
        "url": "https://zapier.com/blog/chatgpt-alternatives/",
        "snippet": "ChatGPT still takes the win on a few aspects: its data analysis and reasoning features are a lot more advanced...",
        "score": 1.0
      },
      {
        "title": "r/OpenAI on Reddit: ChatGPT alternatives",
        "url": "https://www.reddit.com/r/OpenAI/comments/1hcpklu/chatgpt_alternatives/",
        "snippet": "Try <strong>agentsea.com</strong>. it's a private alternative to chatgpt.",
        "score": 0.8
      },
      {
        "title": "What are great and simple ChatGPT alternatives to recommend people? - Techlore Forum",
        "url": "https://discuss.techlore.tech/t/what-are-great-and-simple-chatgpt-alternatives-to-recommend-people/13476",
        "snippet": "OpenAI just announced they have 800 million users and (they say) users doubled in the last two months...",
        "score": 0.1
      }
    ]
  }
}
```

### 7. Deep Search with Query Expansion
```python
result = await client.call_tool("web_search", {
    "query": "quantum computing",
    "deep_search": true,
    "count": 5
})
```

**Actual Response:**
```json
{
  "status": "success",
  "data": {
    "query": "quantum computing",
    "total": 5,
    "search_type": "deep",
    "results": [
      {
        "title": "Quantum computing - Wikipedia",
        "url": "https://en.wikipedia.org/wiki/Quantum_computing",
        "snippet": "A <strong>quantum</strong> <strong>computer</strong> is a (real or theoretical) <strong>computer</strong> that uses...",
        "score": 1.0
      },
      {
        "title": "What Is Quantum Computing? | IBM",
        "url": "https://www.ibm.com/think/topics/quantum-computing",
        "snippet": "<strong>Quantum</strong> <strong>computing</strong> is a rapidly-emerging technology...",
        "score": 0.8
      },
      {
        "title": "DOE Explains...Quantum Computing | Department of Energy",
        "url": "https://www.energy.gov/science/doe-explainsquantum-computing",
        "snippet": "DOE's Lawrence Berkeley National Laboratory is using a sophisticated cooling system...",
        "score": 0.6
      }
    ],
    "urls": [
      "https://en.wikipedia.org/wiki/Quantum_computing",
      "https://quantumcomputinginc.com/",
      "https://www.ibm.com/think/topics/quantum-computing",
      "https://finance.yahoo.com/news/billionaires-piling-quantum-computing-stock-101100012.html",
      "https://www.energy.gov/science/doe-explainsquantum-computing"
    ]
  }
}
```

Note: Deep search performs query expansion internally, searching for variations to get comprehensive results.

### 8. Combined Parameters
```python
result = await client.call_tool("web_search", {
    "query": "AI startups",
    "freshness": "week",
    "result_filter": "news",
    "goggle_type": "news",
    "extra_snippets": true,
    "count": 5
})
```

**Actual Response:**
```json
{
  "status": "success",
  "data": {
    "query": "AI startups",
    "total": 5,
    "results": [
      {
        "title": "Forbes 2025 AI 50 List - Top Artificial Intelligence Companies Ranked",
        "url": "https://www.forbes.com/lists/ai50/",
        "snippet": "Newcomers to the list include $2.5 billion-valued <strong>Anysphere (better known as Cursor),</strong> a three year-old AI startup...",
        "score": 1.0
      },
      {
        "title": "Top 156 AI Startups 2025 | Funded by Sequoia, YC, A16Z",
        "url": "https://gregschwartz.medium.com/the-top-156-ai-startups-of-2025-funded-by-sequoia-yc-a16z-1bb79a41e0d6",
        "snippet": "The top <strong>AI</strong> <strong>startups</strong> of 2025 funded by Sequoia, YC, A16Z, and more...",
        "score": 0.9
      }
    ],
    "search_params": {
      "freshness": null,
      "filter": null,
      "goggle": "news",
      "extra_snippets": true,
      "count": 5
    }
  }
}
```

## Goggle Profiles

### Academic (`goggle_type: "academic"`)
Boosts:
- `.edu` domains (3x)
- `scholar.google.com` (3x)
- `arxiv.org` (3x)
- `.org` domains (2x)
- `pubmed.ncbi.nlm.nih.gov` (2x)
- `sciencedirect.com` (2x)

Downranks:
- Social media sites (Pinterest, Facebook, Twitter)

### Technical (`goggle_type: "technical"`)
Boosts:
- `github.com` (3x)
- `stackoverflow.com` (3x)
- Documentation sites (`docs.*`) (2x)
- `dev.to` (2x)
- `medium.com` (2x)

Downranks:
- `w3schools.com` (2x)

### News (`goggle_type: "news"`)
Boosts:
- `reuters.com` (3x)
- `apnews.com` (3x)
- `bbc.com` (2x)
- `cnn.com` (2x)
- `nytimes.com` (2x)

## Result Types

The `type` field in results indicates the source type:
- `web`: Standard web pages
- `news`: News articles
- `video`: Video content
- `infobox`: Knowledge panel/infobox
- `summary`: AI-generated summary
- `discussions`: Forum/discussion threads
- `faq`: Frequently asked questions

## Performance Notes

1. **Rate Limiting**: The API enforces 1-second delays between requests and auto-retries on 429 errors
2. **Content Length**: `all_content` field is limited to 500 characters to manage response size
3. **Deep Search**: Takes longer (~10-15 seconds) as it performs multiple searches
4. **Max Results**: Standard searches max at 20 results, deep searches can return more unique URLs

## Best Practices

1. **Use Freshness for Time-Sensitive Queries**: Add `freshness: "day"` for breaking news or recent events
2. **Combine Filters**: Use both `result_filter` and `goggle_type` for precise results
3. **Enable Cluster Extraction**: Keep `extra_snippets: true` to extract related content from cluster field (provides descriptions from related pages on the same domain)
4. **Deep Search for Research**: Use `deep_search: true` for comprehensive research tasks
5. **Specific Goggles for Domains**: Use `academic` for research papers, `technical` for code/docs

## How Brave API Extra Content Works

The `extra_snippets` parameter requests cluster data from Brave Search API. When enabled, Brave returns a `cluster` field containing 3-5 related pages from the same domain. Our implementation extracts descriptions from these cluster items to enrich the `all_content` field, providing more context beyond the main snippet.

## Changelog

### v2.1 (Current)
- **Fixed**: Now correctly extracts extra content from Brave API's `cluster` field (related pages from same domain)
- **Fixed**: Updated documentation to reflect actual Brave API behavior
- Added cluster descriptions to `extra_snippets` array (up to 5 items)
- Enhanced `all_content` to include: title + snippet + cluster descriptions + meta_description

### v2.0
- Added `extra_snippets` parameter for requesting cluster data
- Added `freshness` filter (day, week, month, year)
- Added `result_filter` for content type filtering
- Added `goggle_type` for custom ranking profiles
- Added `deep_search` for query expansion
- Enhanced result parsing (news, videos, infobox, summary)
- Added `all_content` field combining all snippets
- Implemented automatic rate limiting and retry

### v1.0
- Basic search with query and count parameters
- Simple result format with title, url, snippet