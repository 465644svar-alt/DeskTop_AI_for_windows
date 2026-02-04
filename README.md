# AI Manager v11.0

Десктопное приложение для работы с нейросетями на Windows: чат, мультизапросы,
журналирование, сохранение результатов и расширенные настройки провайдеров.

## Поддерживаемые нейросети

- **OpenAI GPT**
- **Anthropic Claude**
- **Google Gemini**
- **DeepSeek**
- **Groq**
- **Mistral AI**

## Возможности

- Чат с любой из поддерживаемых нейросетей
- Пакетная обработка запросов ко всем нейросетям одновременно
- Ветвление диалогов (сохранение/загрузка/удаление веток)
- Сохранение ответов и логов в файлы
- Журнал запросов/ошибок и статистика
- Админ‑лог взаимодействий (отправка/обработка/ответ)
- Настройка ролей и системных промптов по провайдерам
- Арбитр: выбор главной нейросети
- Списки запретов и задачи
- Проверка статуса подключений

## Установка

### Требования
- Python 3.8+
- Windows 10/11

### Быстрый старт

1. Клонируйте репозиторий:
```bash
git clone https://github.com/465644svar-alt/DeskTop_AI_for_windows.git
cd DeskTop_AI_for_windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Запустите приложение:
```bash
python main_app.py
```

## Сборка EXE для Windows

### Вариант 1: BAT-скрипт (рекомендуется)
```
build_windows.bat
```

### Вариант 2: Python-скрипт
```bash
python build_windows.py
```

После сборки исполняемый файл будет в папке `dist/AI_Manager.exe`

## Получение API ключей

| Провайдер | Ссылка для получения ключа |
|-----------|---------------------------|
| OpenAI | https://platform.openai.com/api-keys |
| Anthropic | https://console.anthropic.com/ |
| Gemini | https://aistudio.google.com/apikey |
| DeepSeek | https://platform.deepseek.com/ |
| Groq | https://console.groq.com/keys |
| Mistral | https://console.mistral.ai/api-keys/ |

## Структура проекта

```
DeskTop_AI_for_windows/
├── main_app.py          # Основное приложение
├── requirements.txt     # Зависимости Python
├── build_windows.bat    # Скрипт сборки (Windows)
├── build_windows.py     # Скрипт сборки (кроссплатформенный)
├── config.json          # Конфигурация (создается автоматически)
└── README.md           # Документация
```

## Основные вкладки

- **Chat** — диалог с выбранной нейросетью
- **Admin_Chat** — админ‑лог взаимодействий
- **API Settings** — ввод API ключей и модели (вручную)
- **Arbitrator** — выбор главной нейросети
- **Role** — системные промпты по провайдерам
- **Prohibitions** — список запретов
- **Tasks** — список задач
- **Logs** — журнал ответов/ошибок

## Лицензия

MIT License
