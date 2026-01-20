# AI Manager v8.0

Десктопное приложение для работы с нейросетями на Windows.

## Поддерживаемые нейросети

- **OpenAI GPT** (GPT-4o, GPT-4, GPT-3.5-turbo)
- **Anthropic Claude** (Claude 3.5 Sonnet, Claude 3 Haiku)
- **Google Gemini** (Gemini 1.5 Flash, Gemini 1.5 Pro)
- **DeepSeek** (DeepSeek-Chat, DeepSeek-Coder)
- **Groq** (Llama 3.3, Mixtral - сверхбыстрые!)
- **Mistral AI** (Mistral Small, Mistral Large)

## Возможности

- Чат с любой из 6 нейросетей
- Пакетная обработка запросов ко всем нейросетям одновременно
- Сохранение ответов в файлы
- Отправка результатов в Telegram
- История запросов
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

## Скриншоты

Приложение имеет следующие вкладки:
- **Чат** - диалог с выбранной нейросетью
- **Настройки API** - ввод API ключей
- **Пакетная обработка** - отправка запросов во все сети
- **Статус** - проверка подключений
- **История** - просмотр сохраненных ответов
- **О программе** - информация о приложении

## Лицензия

MIT License
