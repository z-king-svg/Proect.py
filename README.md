# MatchDesk Studio v4.2

Автономное десктопное приложение для генерации, администрирования и визуализации турнирных сеток. Написано на Python с графическим интерфейсом на Tkinter без обязательных сторонних зависимостей для работы основного функционала.

## Технические особенности

* **Архитектура и интерфейс:**
  * Пользовательский интерфейс на базе стандартных библиотек `tkinter` и `ttk` с поддержкой масштабирования под экраны высокой четкости (HiDPI через `ctypes`).
  * Интерактивный процедурный холст (`tk.Canvas`) с поддержкой свободного панорамирования, плавного зума и полноэкранного режима.
  * Стек отмены и повтора действий (Undo/Redo до 50 полных снимков состояния) и атомарная синхронизация сессии в JSON (`%APPDATA%` / `.config`).

* **Турнирные алгоритмы:**
  Поддержка форматов **Single Elimination**, **Double Elimination** (с автоматическим переходом в нижнюю сетку и логикой Bracket Reset в гранд-финале) и **Round Robin** (генератор кругового расписания и расчет очков в таблице).
    Приведение количества слотов к ближайшей степени двойки и балансировка технических пропусков (BYE) для ростеров от 2 до 64 участников.
    Строгий синтаксический анализ и валидация результатов серий для форматов BO1, BO3 и BO5.

  **Мультимедиа и звуковой движок:**
   Процедурный синтезатор звука: генерация 16-битного аудиоэффекта столкновения (sub-drop impact, 44.1 кГц) без внешних файлов через стандартные модули `math`, `struct` и `wave`.
   Воспроизведение звука под Windows через связку `winsound` и MCI API (`winmm.dll`) для потоков MP3/WAV.
   Система частиц (искры, ударные волны) с покадровой отрисовкой на холсте (~66 FPS).

 **Экспорт и сборка:**
   Модульный рендеринг: экспорт сетки в высоком разрешении в PNG (`Pillow`) и создание наградного сертификата победителя в формате A4 PDF (`ReportLab`).
   Встроенный асинхронный инструмент сборки: компиляция проекта в автономный `.exe` через `PyInstaller` в изолированном фоновом потоке.

## Стек технологий и зависимости

**Базовый рантайм:** Python 3.10+ (Стандартная библиотека: `tkinter`, `threading`, `json`, `wave`, `struct`, `ctypes`, `subprocess`)
 **Опциональные пакеты:** `Pillow` (экспорт в PNG и логотипы), `reportlab` (генерация дипломов в PDF), `pyinstaller` (компиляция в EXE из интерфейса)


# MatchDesk Studio v4.2

Standalone desktop application for generating, managing, and rendering esports tournament brackets. Built entirely on Python and Tkinter with zero mandatory third-party runtime dependencies for core functionality.

## Technical Highlights

 **Architecture & UI:** 
   Custom GUI implemented via native `tkinter` and `ttk` with DPI awareness configuration (`ctypes`).
   Procedurally rendered interactive vector canvas (`tk.Canvas`) supporting dynamic pan, fractional zoom, and full-screen modes.
   Undo/Redo history stack (up to 50 deep-copied application snapshots) and atomic JSON session persistence in OS-specific app storage (`%APPDATA%` / `.config`).

**Tournament Engine & Algorithms:**
   Support for **Single Elimination**, **Double Elimination** (with automatic lower bracket feeding and grand final bracket reset logic), and **Round Robin** (round schedule generator + dynamic point table).
   Power-of-two slot calculations with balanced BYE allocation for non-standard roster sizes (2 to 64 participants).
   Strict match score parsing and verification for BO1, BO3, and BO5 series formats.

**Audio & Multimedia Engine:**
   Procedural waveform audio synthesizer: generates a 16-bit 44.1 kHz PCM sub-drop impact sound on the fly using standard `math`, `struct`, and `wave` modules without external assets.
   Native Windows audio playback via `winsound` and Windows MCI API (`winmm.dll`) for MP3/WAV streams.
   Particle physics engine (sparks, shockwaves) rendered frame-by-frame on Tkinter canvas (~66 FPS).

 **Export & Deployment Pipeline:**
   Modular image and vector rendering: high-resolution bracket export to PNG (via `Pillow`) and winner certificate generation to A4 PDF (via `ReportLab`).
   Integrated asynchronous build system: executes `PyInstaller` in a isolated background worker thread to compile standalone executable packages.

## Tech Stack & Dependencies

 **Core Runtime:** Python 3.10+ (Standard Library: `tkinter`, `threading`, `json`, `wave`, `struct`, `ctypes`, `subprocess`)
 **Optional Dependencies:** `Pillow` (PNG export & team logos), `reportlab` (PDF diplomas), `pyinstaller` (in-app EXE compilation)
