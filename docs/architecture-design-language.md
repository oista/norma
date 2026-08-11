# Architecture Design Language

**SSOT для Claude, дизайнера и Cursor.**\
Living board (экраны + kit): [`adl/index.html`](adl/index.html) — открыть в браузере.\
Токены: [`../tokens/stone.toml`](../tokens/stone.toml).\
Знаки 512×512: [`../brand/marks/`](../brand/marks/).

Канон продукта-онтологии: **Clavis** (ранний черновик — Cavis). См. [`naming.md`](naming.md).

______________________________________________________________________

## 1. Правило высоты

**3D — только гербы сущностей.** Кнопки, таблицы, сайдбар, тогглы, модалки — строгий **2D**.

Иконка замкового камня в шапке Clavis — да.\
Выпуклая 3D-кнопка «Run agent» — нет.

______________________________________________________________________

## 2. Визуальная грамматика

| Уровень | Как выглядит | Зачем |
|---------|--------------|-------|
| Брендовые сущности | Один предметный isometric 3D-символ на бежевой плитке, лёгкий наклон | PRODATA — материал; ENTAN — инструмент познания; Clavis — элемент смысла |
| Навигация и управление | Строгий 2D: графитовый текст, тонкие линии, таблицы, статус-чипы | Рабочий, не «игрушечный» |
| Акцент | Одна оранжево-киноварная метка `#E95B2B`, не заливка всего | Provenance, warning, active trace, invariant violation |
| Контекст | Тёплый камень / песок `#c4b494` / `#d8cbae` | Лор арки |

### Знаки — камера и свет

- Изометрия ~30° (одинаковый угол для PRODATA / ENTAN / Clavis)
- Свет сверху-слева; освещённая грань `stone-soft`, теневая `stone`
- Контур `ink` `#222829`; одна киноварная метка на грани
- Плитка: квадрат, фон `paper`, рамка `hairline`, **без чёрных плашек**
- Без букв внутри пиктограммы

| Знак | Предмет |
|------|---------|
| PRODATA | Блок / тёсаный камень (материал) |
| ENTAN | Отвес (инструмент выверки) |
| Clavis | Замковый клин-камень (запирает смысл) |

______________________________________________________________________

## 3. Запреты (anti-patterns)

Копипаста для ревью:

- [ ] Чёрные плашки / dark-hero
- [ ] Flat-vector вместо объёма у **знаков**
- [ ] Кислотные градиенты, glow, neon
- [ ] Glassmorphism
- [ ] Мозги / нейросети / абстрактные графы / графики как логотип
- [ ] Случайные буквы в пиктограммах
- [ ] 3D-кнопки, выпуклые контролы
- [ ] Игрушечные pill-радиусы без нужды

______________________________________________________________________

## 4. Токены

| Token | Hex / value | Роль |
|-------|-------------|------|
| `paper` / `bg-canvas` | `#F7F7F5` | Фон полотна (холодный нейтральный) |
| `paper-raised` / `bg-surface` | `#FFFFFF` | Карточки, инпуты |
| `bg-subtle` | `#F1F3F5` | Вторичная поверхность |
| `bg-selected` | `#E9EEF2` | Quiet selection |
| `ink-strong` | `#18212B` | Заголовки |
| `ink` | `#344150` | Основной текст |
| `ink-muted` | `#6B7785` | Вторичный текст |
| `border` | `#D9DFE5` | UI hairline (cool neutral) |
| `border-strong` | `#B9C3CC` | Secondary button border |
| `stone` / `stone-soft` | `#C4B494` / `#D8CBAE` | **Только** бренд-плитки / marks |
| `hairline` | `#C9B58E` | Рамка brand tile |
| `accent` | `#E95B2B` | Primary CTA / provenance |
| `accent-deep` | `#C9471E` | Hover primary |
| `navy-900` / `sidebar` | `#202C3D` | Навигация / dense chrome |
| `info` | `#385F7A` | Selection / focus ring |
| `danger` / `success` / `warning` | `#B53B39` / `#28725E` / `#A15C13` | Status |
| `radius-sm/md/lg` | 6 / 8 / 10 px | Скругления |
| `shadow` | **none** | Только линии |

**Правило:** тёплый limestone (`stone`) — только гербы и onboarding. UI-бордеры — cool `--border`, не бежевый hairline.

**Состояния:** hover = `--bg-hover`; focus = `--focus-ring` (`info`); selected chips = `--bg-selected` + `--info`; disabled opacity 0.4.

**Типографика:** UI sans (Segoe UI / system); display caps для wordmark; mono для ID, SQL, `loop_plan`; tabular nums в таблицах.

______________________________________________________________________

## 5. Controls kit

| Элемент | Правило |
|---------|---------|
| Primary button | `accent` fill, белый текст, radius-sm |
| Secondary | paper-raised + hairline border |
| Ghost | без бордера, ink-muted |
| Danger | `danger` fill |
| Input / select | hairline, paper-raised, focus = accent ring |
| Toggle | track stone / on=accent; thumb white |
| Chip | hairline pill; active = accent border |
| Tabs | bottom accent 2px на active |
| Sidebar active | inset accent bar 3px |

______________________________________________________________________

## 6. Экраны-канон (см. board)

1. Shell — header + content  
2. Sidebar — active accent bar  
3. Agent chat — thought / action / answer + left rule  
4. Trace turn — timeline + chips + mono  
5. Lineage table — dense tabular  
6. Clavis ontology — 2D node-link hairline  
7. Runtime presets — radio cards  
8. Empty — короткий copy + secondary CTA  
9. Error — left-border alert, не full-bleed red  
10. Confirm — paper modal  
11. Controls kit  
12. Setup settings — 2-col compact  

______________________________________________________________________

## 7. Чеклист ревью UI

1. Есть ли чёрная плашка или dark-hero? → убрать.  
2. Есть ли 3D на кнопках/таблицах? → убрать.  
3. Акцент заливает весь экран? → оставить одну метку.  
4. Hex вне `stone.toml`? → заменить токеном.  
5. Знак содержит буквы / мозг / граф? → перерисовать.  
6. Тени вместо hairline? → убрать shadow.  
7. Ошибка кричит красным фоном? → alert с left border.  

______________________________________________________________________

## Связанные

- [`design-system.md`](design-system.md) — пять принципов триады  
- [`naming.md`](naming.md) — арка имён  
- ENTAN ADR-0022 — Norma shared layer  
