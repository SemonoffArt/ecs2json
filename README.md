# 🏭 ecs2json

> Конвертер тегов FLS ECS7 в JSON/YAML/CSV для систем промышленной автоматизации

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/badge/Package%20Manager-uv-green.svg)](https://github.com/astral-sh/uv)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 О проекте

**ecs2json** — утилита командной строки для извлечения тегов из mdb баз SCADA **FLS ECS** и экспорта их в различные форматы.

### ✨ Возможности

- 🗄️ **Прямое подключение к MS Access** — чтение `.mdb` файлов ECS через ODBC
- ⚡ **Кэширование справочников** — ускорение обработки за счёт загрузки в память
- 🔍 **Поиск тегов по маске** — фильтрация тегов по шаблону
- 🎨 **Цветной вывод** — наглядное отображение прогресса и результатов
- 📊 **Множество форматов** — экспорт в JSON, YAML, CSV, Telegraf config
- 🔗 **Поиск на мнемосхемах** — обнаружение тегов в файлах `.g`

---

## 🚀 Быстрый старт

### Требования

- ✅ Python **3.13+**
- ✅ **[uv](https://github.com/astral-sh/uv)** — менеджер пакетов
- ✅ **Microsoft Access ODBC Driver** — драйвер для подключения к `.mdb`

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/SemonoffArt/ecs2json.git
cd ecs2json

# Установить зависимости
uv sync
```

### Запуск

```bash
# Запустить скрипт
uv run python ecs2json.py

# Или через entry point
uv run ecs2json
```

---

## 📦 Выводимые файлы

После выполнения создаются файлы:

| Файл | Описание |
|------|----------|
| 📄 `tags.json` | Теги в формате JSON |
| 📄 `tags.yaml` | Теги в формате YAML |
| 📄 `tags.csv` | Теги в формате CSV |
| 📄 `tags.telegraf.conf` | Конфигурация для Telegraf |
| 📄 `equips1.json` | Оборудование в формате equips |

---

## 🏗️ Структура проекта

```
ecs2json/
├── 📄 ecs2json.py           # Основной модуль
├── 📦 pyproject.toml        # Конфигурация проекта
├── 🔒 uv.lock               # Заблокированные зависимости
├── 🐍 .python-version       # Версия Python
├── 📁 data/
│   └── 🗄️ FlsaProDb/        # Базы данных ECS
└── 📝 README.md             # Документация
```

---

## ⚙️ Конфигурация

### Зависимости

```toml
[dependencies]
alive-progress = ">=3.3.0"   # Прогресс-бары
colorama       = ">=0.4.6"   # Цветной вывод
pyodbc         = ">=5.3.0"   # Подключение к MS Access
pyyaml         = ">=6.0.3"   # Работа с YAML
```

### Структура данных

Проект ожидает следующие файлы в `data/FlsaProDb/`:

- `SdrPoint30.mdb` — основная база тегов
- `SdrApAlg30.mdb` — алгоритмы A точек
- `SdrBlkAlg30.mdb` — блочные алгоритмы
- `SdrBpAlg30.mdb` — алгоритмы BP
- `SdrPntTextDyn30.mdb` — текстовые описания
- `SdrSimS5Config30.mdb` — конфигурация подключения к ПЛК Siemens

---

## 🛠️ Разработка

### Добавить зависимость

```bash
uv add <package-name>
```

### Добавить dev-зависимость

```bash
uv add --dev <package-name>
```

### Запустить тесты

```bash
uv run pytest
```

---

## 📝 Пример использования

```python
from ecs2json import TagsHelper

# Инициализация с поиском по маске
tags = TagsHelper(tags_pattern="MAINT%", with_mimic=False)

# Сохранение в различные форматы
tags.save_json()
tags.save_yaml()
tags.save_csv()
tags.save_telegraf()
tags.save_oh_equip_json()
```

---

## 🔧 Troubleshooting

### Ошибка подключения к MS Access

```
Error: Microsoft Access Driver not found
```

**Решение:** Установите [Microsoft Access Database Engine](https://www.microsoft.com/en-us/download/details.aspx?id=54920)

### Ошибка отсутствия файлов баз данных

```
Exception: Can't open db file data/FlsaProDb/SdrPoint30.mdb
```

**Решение:** Убедитесь, что файлы баз данных ECS находятся в директории `data/FlsaProDb/`

---

## 📄 Лицензия

MIT License — см. файл [LICENSE](LICENSE)

---

## 👨‍💻 Автор

**Artjom Semonoff**  
[GitHub](https://github.com/SemonoffArt)

---

<div align="center">

**⭐ Если проект полезен, поставьте звезду на GitHub!**

Made with ❤️ for Industrial Automation

</div>
