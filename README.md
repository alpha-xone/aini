![AINI](images/aini.gif)

# aini

Declarative AI components - make **AI** component **ini**tialization easy with auto-imports and prebuilt YAML configs.

---

## 🚀 Quick Start: Discover, Inspect, Use

### 0. Install (with LangChain support)

```bash
pip install aini[lang]
```

---

### 1. Discover Available LangChain Configurations

List all available YAML config files for LangChain components:

```python
In [1]: from aini import alist

In [2]: alist(key='lang')
╭──────────────────────────────────────────────────────────────────────────────────╮
│ Found 9 YAML file(s)                                                             │
│ └── aini / Site-Packages: C:/Python3/Lib/site-packages/aini/                     │
│     ├── lang/                                                                    │
│     │   ├── config.yml: config                                                   │
│     │   ├── graph.yml: state_graph                                               │
│     │   ├── llm.yml: ds, r1, sf-qwen, sf-qwen-14b, sf-qwen-30b, sf-qwen-32b      │
│     │   ├── memory.yml: instore, saver                                           │
│     │   ├── msg.yml: msg_state, sys, human, user, ai, invoke, prompt             │
│     │   ├── react.yml: agent                                                     │
│     │   ├── supervisor.yml: supervisor                                           │
│     │   └── tools.yml: tavily                                                    │
│     └── lang_book/                                                               │
│         └── idea_validator.yml: clarifier, researcher, competitor, report        │
╰──────────────────────────────────────────────────────────────────────────────────╯
```

### 2. Inspect a Component’s Component

See the exact configuration for a component by passing `akey`:

```python
In [3]: from aini import aini

In [4]: aini('lang/llm:ds', araw=True)
Out [4]:
{
  'class': 'langchain.llms.DeepSeek',
  'params': {'model': 'deepseek-chat'}
}
```

### 3. Instantiate and Use the Component

Initialize and use the component directly:

```python
# Instantiate the DeepSeek LLM (make sure DEEPSEEK_API_KEY is set)
In [5]: ds = aini('lang/llm:ds')

# Use the model (example: send a message)
In [6]: ds.invoke('hi').pretty_print()
======================== Ai Message ========================
Hello! 😊 How can I assist you today?
```

---

## 🧑‍💻 Extended Usage

### Visualize and Debug

```python
In [7]: from aini import aview

In [8]: aview(ds.invoke('hi'))
<langchain_core.messages.ai.AIMessage>
{
  'content': 'Hello! 😊 How can I assist you today?',
  'response_metadata': {
    'token_usage': {'completion_tokens': 11, 'prompt_tokens': 4, 'total_tokens': 15, 'prompt_cache_miss_tokens': 4},
    'model_name': 'deepseek-chat',
    'system_fingerprint': 'fp_8802369eaa_prod0425fp8',
    'id': '2be77461-5d07-4f95-8976-c3a782e1799b',
    'finish_reason': 'stop'
  },
  'type': 'ai',
  'id': 'run--5cdbede5-9545-441e-a137-ebe25699bf36-0',
  'usage_metadata': {'input_tokens': 4, 'output_tokens': 11, 'total_tokens': 15}
}
```

### List Methods

```python
In [9]: from aini import ameth

In [10]: ameth(ds)
Out [10]:
['invoke', 'predict', 'stream', ...]
```

---

## 🛠️ Advanced Features

### Variable Substitution

Use environment variables, input variables, or defaults in your YAML:

```yaml
llm:
  class: "langchain_deepseek.ChatDeepSeek"
  params:
    api_key: ${DEEPSEEK_API_KEY}
    model: ${model|'deepseek-chat'}
    temperature: ${temp|0.7}
```

**Resolution priority:**
1. Input variables (kwargs to `aini()`)
2. Environment variables
3. Defaults section in YAML
4. Fallback after `|`

### Additioal Parameters

You can pass additional parameters when initializing components (only for single component):

```python
In [11]: ds = aini('lang/llm:ds', max_tokens=100)
```

### Custom Initialization

Specify custom init methods:

```yaml
model_client:
  class: autogen_core.models.ChatCompletionClient
  init: load_component
  params:
    model: ${model}
    expected: ${expected}
```

---

## 📚 More Examples

### [LangChain / LangGraph](https://langchain-ai.github.io/langgraph/)

```python
In [13]: import operator
In [14]: from functools import reduce
# Get a list of agents from LangGraph
In [15]: agents = aini('lang_book/idea_validator)
# Chain them together
In [16]: workflow = reduce(operator.or_, agents.value())
# Get report from the workflow
In [17]: ans = workflow.invoke({'messages': 'Consistency check for AI agents'})
In [18]: ans['messages'][-1].pretty_print()
```

### [Autogen](https://github.com/microsoft/autogen)

```bash
pip install aini[autogen]
```

```python
In [17]: client = aini('autogen/client', model=aini('autogen/llm:ds'))
In [18]: agent = aini('autogen/assistant', name='deepseek', model_client=client)
In [19]: ans = await agent.run(task='What is your name')
In [20]: aview(ans)
```

### [Agno](https://github.com/agno-agi/agno)

```bash
pip install aini[agno]
```

```python
In [21]: agent = aini('agno/agent', tools=[aini('agno/tools:google')])
In [22]: ans = agent.run('Compare MCP and A2A')
In [23]: aview(ans, exc_keys=['metrics'])

<<<<<<< HEAD
### [Mem0](https://mem0.ai/)

```bash
pip install aini[mem0]
```

```python
In [24]: memory = aini('mem0/memory:mem0')
```

---

## 📝 Configuration File Format

YAML or JSON, with support for defaults, variable substitution, and nested components.

```yaml
defaults:
  api_key: "default-key-value"
  temperature: 0.7

assistant:
  class: autogen_agentchat.agents.AssistantAgent
  params:
    name: ${name}
    model_client: ${model_client|client}
    tools: ${tools}
```

---

## 🔗 Links

- [LangChain](https://python.langchain.com/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Autogen](https://github.com/microsoft/autogen)
- [Agno](https://github.com/agno-agi/agno)
- [Mem0](https://mem0.ai/)

---

## 📦 Installation

```bash
pip install aini
```
