![AINI](images/aini.png)

# aini

Make class instantiation easy with auto-imports

## Installation

```bash
pip install aini
```

## Usage

### aini

**AI** component **in**itialization with auto-imports:

```python
from aini import aini

agent = aini('agno/agent', tools=[aini('agno/tools', 'google')])
```

### aview

View AI component properties:

```python
from aini import aview

# Example usage
ans = agent.run('Compare MCP and A2A')
aview(ans)
[Output]
<agno.run.response.RunResponse>
{
  'content': 'Here’s a comparison between **MCP (Multi-Component Protocol)** and **A2A (Agent-to-Agent Protocol)** based on the available resources: ...',
  'content_type': 'str',
  'event': 'RunResponse',
  'messages': [
    {'role': 'user', 'content': 'Compare MCP and A2A', 'add_to_agent_memory': True, 'created_at': 1746758165},
    {
      'role': 'assistant',
      'tool_calls': [
        {
          'id': 'call_0_21871e19-3de7-4a8a-9275-9b4128fb743c',
          'function': {'arguments': '{"query":"MCP vs A2A comparison","max_results":5}', 'name': 'google_search'},
          'type': 'function'
        }
      ]
    }
  ]
  ...
}

# Save to file
aview(ans, to_file='debug/output.yaml')
```
