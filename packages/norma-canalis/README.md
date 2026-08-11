# norma-canalis

*Canalis* — канал / водовод. Контракт доступа к внешним системам для продуктов артели.

Нормативный ADR: [ADR-0002](../../docs/adr/ADR-0002-connector-contract.md). Version **0.2.0**.

## Что внутри

| Слой | Содержимое |
|------|------------|
| Ядро (stdlib) | `Connector` Protocol, capability-слаги, paging, retry, secrets, audit, registry |
| Extras | `http.rest` / `git.repo` (httpx), `sql.catalog` (SQLAlchemy) |
| Testing | `FakeRowSource` / `FakeDocumentSource` для продуктов без корп-эндпоинтов |

**Implemented drivers:** `http.rest`, `sql.catalog`, `git.repo` (`api_style=gitlab`).

**Non-goals:** async-контракт; корпоративные модели (`v_dg_*`, EAM); MCP/RBAC (у продуктов); драйверы `tracker.jira` / `graph.sparql` (follow-up).

## Установка

```bash
pip install -e ./packages/norma-canalis
pip install -e "./packages/norma-canalis[http,git,sql]"   # драйверы
```

## Быстрый старт

```python
from norma.canalis import ConnectorSpec, EnvSecretResolver, open_connector
from norma.canalis.capability import HTTP_REST

spec = ConnectorSpec(
    id="example-api",
    capability=HTTP_REST,
    endpoint="https://example.invalid/api",
)
with open_connector(spec, resolver=EnvSecretResolver()) as conn:
    assert HTTP_REST in conn.capabilities()
```

Продукты импортируют `norma-canalis` in-process. Библиотека, не сервис.
