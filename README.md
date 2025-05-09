![AINI](images/aini.png)

# aini

Make **AI** class **ini**tialization easy with auto-imports.

## Installation

```bash
pip install aini
```

## Usage

### aini

```python
from aini import aini

# Load an agent with tools from configuration files
agent = aini('agno/agent', tools=[aini('agno/tools', 'google')])

# Run the agent
response = agent.run('Compare MCP and A2A')
```

### aview

View AI component properties:

```python
from aini import aview

# Display component structure with filtering
ans = agent.run('Compare MCP and A2A')
aview(ans, exclude_keys=['metric'])

[Output]
<agno.run.response.RunResponse>
{
  'content': "Here's a comparison between **MCP** and **A2A**: ...",
  'content_type': 'str',
  'event': 'RunResponse',
  'messages': [
    {
      'role': 'user',
      'content': 'Compare MCP and A2A',
      'add_to_agent_memory': True,
      'created_at': 1746758165
    },
    {
      'role': 'assistant',
      'tool_calls': [
        {
          'id': 'call_0_21871e19-3de7-4a8a-9275-9b4128fb743c',
          'function': {
            'arguments': '{"query":"MCP vs A2A comparison","max_results":5}',
            'name': 'google_search'
          },
          'type': 'function'
        }
      ]
    }
  ]
  ...
}

# Export to YAML for debugging
aview(ans, to_file='debug/output.yaml')
```
