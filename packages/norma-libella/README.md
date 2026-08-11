# norma-libella

Отвес: домен-агностичный агентский рантайм.

```bash
pip install -e .
```

```python
from norma.libella.tools.protocol import ToolExecutor, ExecutionContext
from norma.libella.tools.classification import ToolTaxonomy
from norma.libella.contract.record import TurnRecord, StopReason
from norma.libella.loop.runtime_options import AgentRuntimeOptions
from norma.libella.loop.simple_tool_loop import stream_tool_loop
```

Продукты регистрируют свой `ToolExecutor` и `ToolTaxonomy`. Полный контракт инвариантов агента (`catalog.yaml` / monitor) пока живёт в продуктовом репозитории ENTAN (`moex-enterprise-analyst/agent/contract/`) и переедет после смены module paths в registry (ADR-0022).
