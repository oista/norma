# norma-forma

Лекало: читает `tokens/stone.toml`, эмитит CSS / themes.toml / Tailwind JS.

```bash
pip install -e .
norma-forma emit --target entan-css --tokens ../../tokens/stone.toml
norma-forma emit --target pw-theme --tokens ../../tokens/stone.toml
norma-forma emit --target tailwind --tokens ../../tokens/stone.toml
```
