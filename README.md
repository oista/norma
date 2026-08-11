# Norma

Наугольник артели: общий слой триады **ENTAN · PRODATA · Clavis**.

Не продукт — мера. Продукты зависят от Norma; Norma не знает о продуктах.

| Пакет | Роль | Метафора |
|-------|------|----------|
| [`norma-forma`](packages/norma-forma) | SSOT дизайн-токенов + генераторы | *forma* — лекало |
| [`norma-libella`](packages/norma-libella) | Агентский рантайм (ReAct + TurnRecord) | *libella* — отвес |
| [`norma-canalis`](packages/norma-canalis) | Контракт коннекторов к внешним системам | *canalis* — канал / водовод |

Палитра по умолчанию: [`tokens/stone.toml`](tokens/stone.toml) (камень и бумага).

## Локальная установка

```bash
pip install -e ./packages/norma-forma
pip install -e ./packages/norma-libella
pip install -e ./packages/norma-canalis
pip install -e "./packages/norma-canalis[http,git,sql]"   # optional drivers
```

По тегу:

```
norma-forma @ git+https://github.com/oista/norma@v0.1.0#subdirectory=packages/norma-forma
norma-libella @ git+https://github.com/oista/norma@v0.1.0#subdirectory=packages/norma-libella
norma-canalis @ git+https://github.com/oista/norma@v0.1.0#subdirectory=packages/norma-canalis
```

## Документация

- [naming.md](docs/naming.md) — арка, роли, регистр имён
- [glossary.md](docs/glossary.md) — публичные термины
- [design-system.md](docs/design-system.md) — принципы UI триады
- [config-contract.md](docs/config-contract.md) — env-префиксы экосистемы
- [seam-registry.md](docs/seam-registry.md) — реестр межпродуктовых швов
- [docs-conventions.md](docs/docs-conventions.md) — общие правила документации артели
- [ADR-INDEX](docs/adr/ADR-INDEX.md) — решения Norma (начиная с ADR-0001 seam contract)
