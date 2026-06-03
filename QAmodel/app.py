"""
DocQAnswer - Веб-интерфейс для сотрудника
"""
from src.auth import add_user, update_user_role, delete_user as auth_delete_user, add_event
from src.auth import authenticate, set_user_status, get_user_status
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import Response, HTMLResponse, JSONResponse
import json
from fastapi import UploadFile, File, Form
import sqlite3
from pathlib import Path
import sys
import datetime
import hashlib

sys.path.insert(0, str(Path(__file__).parent))
from src.pipeline.qa_pipeline import DocQAPipeline
from src.auth import authenticate, create_session, get_session, logout as auth_logout

app = FastAPI(title="DocQAnswer")

print("🚀 Загрузка DocQAnswer...")
qa_pipeline = DocQAPipeline()
print("✅ Система готова!")


def get_query_id(user_id="employee_1"):
    try:
        conn = sqlite3.connect(Path("data/docqanswer.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM query_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except:
        return None


# HTML шаблон
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>DocQAnswer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f0f2f5; height: 100vh; display: flex; }
        .sidebar { width: 260px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; display: flex; flex-direction: column; }
        .sidebar-header { padding: 30px 20px; border-bottom: 1px solid rgba(255,255,255,0.2); }
        .nav-btn { background: transparent; border: none; color: white; padding: 15px 20px; text-align: left; cursor: pointer; width: 100%; font-size: 16px; }
        .nav-btn:hover { background: rgba(255,255,255,0.1); }
        .nav-btn.active { background: rgba(255,255,255,0.2); border-left: 4px solid white; }
        .main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .header { background: white; padding: 20px 30px; display: flex; justify-content: space-between; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .content { flex: 1; overflow-y: auto; padding: 30px; }
        .card { background: white; border-radius: 16px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        textarea { width: 100%; padding: 15px; border: 2px solid #e0e0e0; border-radius: 12px; font-size: 16px; font-family: inherit; resize: vertical; }
        button { margin-top: 15px; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; }
        .answer-box { background: #f8f9fa; padding: 20px; border-radius: 12px; border-left: 4px solid #28a745; margin-top: 20px; }
        .source-info { background: #fff3cd; padding: 10px 15px; border-radius: 8px; margin-top: 15px; font-size: 14px; }
        .confidence { background: #e9ecef; padding: 5px 10px; border-radius: 20px; display: inline-block; margin-top: 10px; font-size: 12px; }
        .history-item { background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; border: 1px solid #e0e0e0; }
        .history-question { font-weight: bold; margin-bottom: 8px; }
        .history-meta { font-size: 12px; color: #999; display: flex; gap: 15px; margin-top: 8px; flex-wrap: wrap; }
        .filter-bar { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
        .filter-bar input { flex: 1; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px; }
        .filter-bar select { padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px; }
        .empty-state { text-align: center; padding: 60px; color: #999; }
        .feedback-buttons { display: flex; gap: 10px; margin-top: 15px; }
        .btn-like { background: #28a745; color: white; border: none; border-radius: 6px; padding: 6px 12px; cursor: pointer; }
        .btn-dislike { background: #dc3545; color: white; border: none; border-radius: 6px; padding: 6px 12px; cursor: pointer; }
        .login-btn-sidebar { background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.5); color: white; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-top: 10px; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
        .modal-content { background-color: white; margin: 15% auto; padding: 30px; border-radius: 16px; width: 350px; max-width: 90%; }
        .modal-content input { width: 100%; padding: 10px; margin: 10px 0; border: 2px solid #e0e0e0; border-radius: 8px; }
        .history-item { background: white; border-radius: 12px; margin-bottom: 15px; border: 1px solid #e0e0e0; overflow: hidden; cursor: pointer; transition: box-shadow 0.2s; }
        .history-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .history-header { padding: 15px; display: flex; justify-content: space-between; align-items: center; background: #fafafa; }
        .history-question { font-weight: bold; flex: 1; }
        .history-status { font-size: 20px; margin-right: 10px; }
        .history-expand-icon { font-size: 18px; color: #999; }
        .history-details { display: none; padding: 15px; border-top: 1px solid #e0e0e0; background: white; }
        .history-details.show { display: block; }
        .history-answer { background: #f8f9fa; padding: 12px; border-radius: 8px; margin-top: 10px; white-space: pre-wrap; word-break: break-word; }
        .dropdown button { transition: all 0.2s; }
        .dropdown button:hover { background: #5a67d8; transform: translateY(-1px); }
        .dropdown-menu { border-radius: 8px; overflow: hidden; }
        .dropdown-menu button { background: white !important; color: #333 !important; margin: 0 !important; padding: 10px 15px !important; border: none !important; border-bottom: 1px solid #eee !important; cursor: pointer !important; font-size: 14px !important; width: 100% !important; text-align: left !important; }
        .dropdown-menu button:hover { background: #f0f0f0 !important; }
        .dropdown-menu button:last-child { border-bottom: none !important; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>📄 DocQAnswer</h2>
            <p>Помощник по документации</p>
        </div>
        <button class="nav-btn" onclick="showChat()" id="chatBtn" style="display: none;">💬 Чат</button>
        <button class="nav-btn" onclick="showHistory()" id="historyBtn" style="display: none;">📜 История запросов</button>
        <button class="nav-btn" onclick="showAnalytics()" id="analyticsBtn" style="display: none;">📊 Аналитика</button>
        <button class="nav-btn" onclick="showDocuments()" id="documentsBtn" style="display: none;">📁 Управление документами</button>
        <button class="nav-btn" onclick="showUsers()" id="usersBtn" style="display: none;">👥 Управление пользователями</button>
        <button class="nav-btn" onclick="showEventLog()" id="eventLogBtn" style="display: none;">📋 Журнал событий</button>
        <div style="flex: 1;"></div>
        <div style="padding: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
            <div id="userStatus"></div>
        </div>
    </div>

    <div class="main-content">
        <div class="header">
            <h1 id="pageTitle">Чат</h1>
            <div>👤 <span id="userRoleDisplay">Сотрудник</span></div>
        </div>
        <div class="content" id="content">
            <div id="chatView">
                <div class="card">
                    <textarea id="question" rows="4" placeholder="Задайте вопрос по документации..."></textarea>
                    <button onclick="askQuestion()">🔍 Задать вопрос</button>
                </div>
                <div id="answerArea"></div>
            </div>
            <div id="historyView" style="display: none;">
                <div class="card">
                    <div class="filter-bar">
                        <input type="text" id="searchInput" placeholder="🔍 Поиск по истории...">
                        <select id="filterSelect">
                            <option value="all">📅 Все</option>
                            <option value="today">📆 Сегодня</option>
                            <option value="yesterday">🕐 Вчера</option>
                            <option value="week">📊 За неделю</option>
                            <option value="month">🗓 За месяц</option>
                        </select>
                    </div>
                </div>
                <div id="historyList" class="card">Загрузка истории...</div>
                <div id="loadMoreBtn" style="display: none; text-align: center;"><button onclick="loadMore()">Показать еще</button></div>
            </div>
            <div id="analyticsView" style="display: none;">
                <!-- Фильтр периода -->
                <div class="card">
                    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <label><strong>📅 Период:</strong></label>
                        <select id="periodSelect" style="padding: 8px 12px; border-radius: 8px; border: 1px solid #ddd;">
                            <option value="today">Сегодня</option>
                            <option value="week" selected>Последние 7 дней</option>
                            <option value="month">Этот месяц</option>
                            <option value="all">За всё время</option>
                        </select>
                        <button onclick="loadAnalytics()" style="margin-top: 0; padding: 8px 20px;">Обновить</button>
                    </div>
                </div>
    
                <!-- Карточки с метриками -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                    <div class="card" style="text-align: center;">
                        <h3>📊 Всего запросов</h3>
                        <p id="statTotalQueries" style="font-size: 32px; font-weight: bold; color: #667eea;">0</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h3>👍 Доля успешных</h3>
                        <p id="statSuccessRate" style="font-size: 32px; font-weight: bold; color: #28a745;">0%</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h3>⏱ Среднее время ответа</h3>
                        <p id="statAvgTime" style="font-size: 32px; font-weight: bold; color: #764ba2;">0 с</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h3>👍👎 Оценок получено</h3>
                        <p id="statTotalFeedback" style="font-size: 32px; font-weight: bold; color: #ffc107;">0</p>
                    </div>
                </div>
    
                <!-- Графики -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    <div class="card">
                        <h3>📈 Запросы по дням</h3>
                        <canvas id="dailyChart" width="400" height="200" style="width: 100%; height: auto; min-height: 200px;"></canvas>
                    </div>
                    <div class="card">
                        <h3>📊 Оценки пользователей</h3>
                        <canvas id="ratingsChart" width="400" height="200" style="width: 100%; height: auto; min-height: 200px;"></canvas>
                    </div>
                </div>
    
                <!-- Прогресс-бар метрик -->
                <div class="card">
                    <h3>🎯 Метрики качества модели</h3>
                    <div style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span>F1-Score</span>
                            <span id="f1Value">0%</span>
                        </div>
                        <div style="background: #e0e0e0; border-radius: 10px; overflow: hidden;">
                            <div id="f1Bar" style="width: 0%; height: 20px; background: linear-gradient(90deg, #667eea, #764ba2); transition: width 0.5s;"></div>
                        </div>
                    </div>
                    <div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span>Exact Match (EM)</span>
                            <span id="emValue">0%</span>
                        </div>
                        <div style="background: #e0e0e0; border-radius: 10px; overflow: hidden;">
                            <div id="emBar" style="width: 0%; height: 20px; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.5s;"></div>
                        </div>
                    </div>
                </div>
    
                <!-- Таблица неудачных запросов -->
                <div class="card">
                    <h3>❌ Неудачные запросы (дизлайки)</h3>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr><th style="text-align: left; padding: 10px; border-bottom: 1px solid #ddd;">Вопрос</th>
                                    <th style="text-align: left; padding: 10px; border-bottom: 1px solid #ddd;">Ответ</th>
                                    <th style="text-align: left; padding: 10px; border-bottom: 1px solid #ddd;">Источник</th>
                                    <th style="text-align: left; padding: 10px; border-bottom: 1px solid #ddd;">Дата</th>
                                </tr>
                            </thead>
                            <tbody id="failedTableBody">
                                <tr><td colspan="4" style="text-align: center; padding: 40px;">Загрузка...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
    
                <!-- Кнопка экспорта -->
                <div style="text-align: right;">
                    <button onclick="exportReport()" style="background: #28a745;">📥 Экспорт отчёта (CSV)</button>
                </div>
            </div>    
            <div id="documentsView" style="display: none;">
                <!-- Кнопка загрузки -->
                <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>📁 Управление документами</h3>
                    <button onclick="showUploadModal()" style="background: #28a745;">+ Загрузить документ</button>
                </div>
    
                <!-- Статистика -->
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px;">
                    <div class="card" style="text-align: center;">
                        <h3>📄 Всего документов</h3>
                        <p id="statTotalDocs" style="font-size: 32px; font-weight: bold; color: #667eea;">0</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h3>✅ Активных документов</h3>
                        <p id="statActiveDocs" style="font-size: 32px; font-weight: bold; color: #28a745;">0</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h3>📊 Всего чанков</h3>
                        <p id="statTotalChunks" style="font-size: 32px; font-weight: bold; color: #764ba2;">0</p>
                    </div>
                </div>
    
                <!-- Таблица документов -->
                <div class="card">
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #f8f9fa;">
                                    <th style="text-align: left; padding: 12px;">Название документа</th>
                                    <th style="text-align: left; padding: 12px;">Версия</th>
                                    <th style="text-align: left; padding: 12px;">Дата загрузки</th>
                                    <th style="text-align: left; padding: 12px;">Категория</th>
                                    <th style="text-align: left; padding: 12px;">Статус</th>
                                    <th style="text-align: left; padding: 12px;">Действия</th>
                                </tr>
                            </thead>
                            <tbody id="documentsTableBody">
                                <tr><td colspan="6" style="text-align: center; padding: 40px;">Загрузка...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div id="usersView" style="display: none;">
                <!-- Кнопка добавления -->
                <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>👥 Управление пользователями</h3>
                    <button onclick="showAddUserModal()" style="background: #28a745;">+ Добавить пользователя</button>
                </div>
                
                <!-- Статистика -->
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px;">
                    <div class="card" style="text-align: center;">
                        <h3>👥 Всего пользователей</h3>
                        <p id="statTotalUsers" style="font-size: 32px; font-weight: bold; color: #667eea;">0</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h3>✅ Активных</h3>
                        <p id="statActiveUsers" style="font-size: 32px; font-weight: bold; color: #28a745;">0</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h3>🔒 Заблокированных</h3>
                        <p id="statBlockedUsers" style="font-size: 32px; font-weight: bold; color: #dc3545;">0</p>
                    </div>
                </div>
                
                <!-- Таблица пользователей -->
                <div class="card">
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #f8f9fa;">
                                    <th style="text-align: left; padding: 12px;">Логин</th>
                                    <th style="text-align: left; padding: 12px;">Имя</th>
                                    <th style="text-align: left; padding: 12px;">Email</th>
                                    <th style="text-align: left; padding: 12px;">Роль</th>
                                    <th style="text-align: left; padding: 12px;">Статус</th>
                                    <th style="text-align: left; padding: 12px;">Последний вход</th>
                                    <th style="text-align: left; padding: 12px;">Дата регистрации</th>
                                    <th style="text-align: left; padding: 12px;">Действия</th>
                                </tr>
                            </thead>
                            <tbody id="usersTableBody">
                                <tr><td colspan="7" style="text-align: center; padding: 40px;">Загрузка...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <div id="eventLogView" style="display: none;">
                <div class="card">
                    <div style="display: flex; gap: 15px; align-items: center; flex-wrap: wrap; margin-bottom: 20px;">
                        <input type="text" id="eventSearch" placeholder="🔍 Поиск по событиям, пользователю..." style="flex: 2; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px;">
                        <select id="eventPeriod" style="padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px;">
                            <option value="all">📅 Все</option>
                            <option value="today" selected>📆 Сегодня</option>
                            <option value="yesterday">🕐 Вчера</option>
                            <option value="week">📊 За неделю</option>
                            <option value="month">🗓 За месяц</option>
                        </select>
                        <button onclick="loadEventLog()" style="margin-top: 0; padding: 10px 20px;">🔄 Обновить</button>
                        <button onclick="exportEventLog()" style="margin-top: 0; padding: 10px 20px; background: #28a745;">📥 Экспорт CSV</button>
                    </div>
                </div>

                <!-- Статистика -->
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 20px;">
                    <div class="card" style="text-align: center;">
                        <h3>📊 Всего событий</h3>
                        <p id="eventTotalCount" style="font-size: 32px; font-weight: bold; color: #667eea;">0</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h3>📅 За период</h3>
                        <p id="eventPeriodCount" style="font-size: 32px; font-weight: bold; color: #28a745;">0</p>
                    </div>
                </div>

                <!-- Таблица событий -->
                <div class="card">
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #f8f9fa;">
                                    <th style="text-align: left; padding: 12px;">Пользователь</th>
                                    <th style="text-align: left; padding: 12px;">Время</th>
                                    <th style="text-align: left; padding: 12px;">Тип события</th>
                                    <th style="text-align: left; padding: 12px;">Действие</th>
                                    <th style="text-align: left; padding: 12px;">Источник</th>
                                </tr>
                            </thead>
                            <tbody id="eventLogTableBody">
                                <tr><td colspan="5" style="text-align: center; padding: 40px;">Загрузка...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div id="eventLogLoadMoreBtn" style="display: none; text-align: center; margin-top: 20px;">
                    <button onclick="loadMoreEvents()" style="background: #667eea; margin-top: 0;">Показать еще</button>
                </div>
            </div>
        </div>
    </div>

    <div id="loginModal" class="modal">
        <div class="modal-content">
            <span onclick="closeLoginModal()" style="float: right; cursor: pointer;">&times;</span>
            <h3>Вход в систему</h3>
            <input type="text" id="loginUsername" placeholder="Логин">
            <input type="password" id="loginPassword" placeholder="Пароль">
            <button onclick="login()">Войти</button>
            <div id="loginError" style="color: red; margin-top: 10px;"></div>
        </div>
    </div>
    <!-- Модальное окно загрузки документа -->
    <div id="uploadModal" class="modal">
        <div class="modal-content" style="width: 500px;">
            <span onclick="closeUploadModal()" style="float: right; cursor: pointer;">&times;</span>
            <h3>📤 Загрузка документа</h3>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" id="uploadFile" accept=".txt,.pdf,.docx" style="margin: 15px 0;">
                <input type="text" id="docVersion" placeholder="Версия (например: 1.0)" style="width: 100%; margin: 10px 0; padding: 10px;">
                <select id="docCategory" style="width: 100%; margin: 10px 0; padding: 10px;">
                    <option value="Общая">Общая</option>
                    <option value="Техническая">Техническая</option>
                    <option value="Инструкция">Инструкция</option>
                    <option value="Руководство">Руководство</option>
                    <option value="Нормативная">Нормативная</option>
                </select>
                <button type="button" onclick="uploadDocument()" style="width: 100%;">Загрузить</button>
            </form>
            <div id="uploadError" style="color: red; margin-top: 10px;"></div>
        </div>
    </div>
    
    <!-- Модальное окно добавления пользователя -->
    <div id="addUserModal" class="modal">
        <div class="modal-content" style="width: 400px;">
            <span onclick="closeAddUserModal()" style="float: right; cursor: pointer;">&times;</span>
            <h3>➕ Добавление пользователя</h3>
            <input type="text" id="newUsername" placeholder="Логин" style="width: 100%; margin: 10px 0; padding: 10px;">
            <input type="email" id="newEmail" placeholder="Email" style="width: 100%; margin: 10px 0; padding: 10px;">
            <input type="password" id="newPassword" placeholder="Пароль" style="width: 100%; margin: 10px 0; padding: 10px;">
            <select id="newRole" style="width: 100%; margin: 10px 0; padding: 10px;">
                <option value="employee">Сотрудник</option>
                <option value="expert">Эксперт</option>
                <option value="admin">Администратор</option>
            </select>
            <button onclick="addUser()" style="width: 100%;">Добавить</button>
            <div id="addUserError" style="color: red; margin-top: 10px;"></div>
        </div>
    </div>
    
    <!-- Модальное окно редактирования пользователя -->
    <div id="editUserModal" class="modal">
        <div class="modal-content" style="width: 400px;">
            <span onclick="closeEditUserModal()" style="float: right; cursor: pointer;">&times;</span>
            <h3>✏️ Редактирование пользователя</h3>
            <input type="hidden" id="editUserId">
            <label>Логин:</label>
            <input type="text" id="editUsername" readonly style="background: #f0f0f0; width: 100%; margin: 10px 0; padding: 10px;">
            <label>Имя пользователя:</label>
            <input type="text" id="editName" placeholder="Имя" style="width: 100%; margin: 10px 0; padding: 10px;">
            <label>Email:</label>
            <input type="email" id="editEmail" placeholder="Email" style="width: 100%; margin: 10px 0; padding: 10px;">
            <label>Новый пароль (оставьте пустым, чтобы не менять):</label>
            <input type="password" id="editPassword" placeholder="Новый пароль" style="width: 100%; margin: 10px 0; padding: 10px;">
            <button onclick="saveUserEdit()" style="width: 100%;">Сохранить изменения</button>
            <div id="editUserError" style="color: red; margin-top: 10px;"></div>
        </div>
    </div>
    
    <script>
        let currentPage = 0, currentFilter = 'all', currentSearch = '';
        let currentUser = null;
        let currentView = 'chat';
        
        let eventLogPage = 0;
        let isLoadingEvents = false;
        let hasMoreEvents = true;

        function showChat() {
            if (!currentUser) {
                alert('Необходимо войти в систему');
                return;
            }
            document.getElementById('chatView').style.display = 'block';
            document.getElementById('historyView').style.display = 'none';
            document.getElementById('analyticsView').style.display = 'none';
            document.getElementById('documentsView').style.display = 'none';
            document.getElementById('usersView').style.display = 'none';
            document.getElementById('eventLogView').style.display = 'none';
            document.getElementById('pageTitle').innerText = 'Чат';
            document.getElementById('chatBtn').classList.add('active');
            document.getElementById('historyBtn').classList.remove('active');
            document.getElementById('analyticsBtn').classList.remove('active');
            document.getElementById('documentsBtn').classList.remove('active');
            document.getElementById('usersBtn').classList.remove('active');
            document.getElementById('eventLogBtn').classList.remove('active');
        }

        function showHistory() {
            if (!currentUser) {
                alert('Необходимо войти в систему');
                return;
            }
            currentPage = 0;
            document.getElementById('chatView').style.display = 'none';
            document.getElementById('historyView').style.display = 'block';
            document.getElementById('analyticsView').style.display = 'none';
            document.getElementById('documentsView').style.display = 'none';
            document.getElementById('usersView').style.display = 'none';
            document.getElementById('eventLogView').style.display = 'none';
            document.getElementById('pageTitle').innerText = 'История запросов';
            document.getElementById('historyBtn').classList.add('active');
            document.getElementById('chatBtn').classList.remove('active');
            document.getElementById('analyticsBtn').classList.remove('active');
            document.getElementById('documentsBtn').classList.remove('active');
            document.getElementById('usersBtn').classList.remove('active');
            document.getElementById('eventLogBtn').classList.remove('active');
            loadHistory();
        }

        function showAnalytics() {
            if (!currentUser) {
                alert('Необходимо войти в систему');
                return;
            }
            if (currentUser.role !== 'expert' && currentUser.role !== 'admin') {
                alert('Доступ запрещён. Требуются права эксперта.');
                return;
            }
            document.getElementById('chatView').style.display = 'none';
            document.getElementById('historyView').style.display = 'none';
            document.getElementById('analyticsView').style.display = 'block';
            document.getElementById('documentsView').style.display = 'none';
            document.getElementById('usersView').style.display = 'none';
            document.getElementById('eventLogView').style.display = 'none';
            document.getElementById('pageTitle').innerText = 'Аналитика';
            document.getElementById('analyticsBtn').classList.add('active');
            document.getElementById('chatBtn').classList.remove('active');
            document.getElementById('historyBtn').classList.remove('active');
            document.getElementById('documentsBtn').classList.remove('active');
            document.getElementById('usersBtn').classList.remove('active');
            document.getElementById('eventLogBtn').classList.remove('active');
            loadAnalytics();
        }

        function loadHistory() {
            const search = document.getElementById('searchInput')?.value || '';
            const filter = document.getElementById('filterSelect')?.value || 'all';
            fetch(`/history?page=${currentPage}&filter=${filter}&search=${encodeURIComponent(search)}`)
                .then(res => res.json())
                .then(data => {
                    const container = document.getElementById('historyList');
                    if (currentPage === 0) container.innerHTML = '';
                    if (data.length === 0 && currentPage === 0) {
                        container.innerHTML = '<div class="empty-state">История пуста</div>';
                        return;
                    }
                    data.forEach(item => {
                        // Определяем статус (лайк/дизлайк/не оценено)
                        let statusIcon = '';
                        let statusText = '';
                        if (item.feedback === 1) {
                            statusIcon = '👍';
                            statusText = 'Лайк';
                        } else if (item.feedback === 0) {
                            statusIcon = '👎';
                            statusText = 'Дизлайк';
                        } else {
                            statusIcon = '🟡';
                            statusText = 'Не оценено';
                        }
                
                        container.innerHTML += `
                            <div class="history-item" onclick="toggleHistoryDetails(this)">
                                <div class="history-header">
                                    <div class="history-status" title="${statusText}">${statusIcon}</div>
                                    <div class="history-question">❓ ${escapeHtml(item.question)}</div>
                                    <div class="history-expand-icon">▼</div>
                                </div>
                                <div class="history-details">
                                    <div class="history-meta">
                                        ${item.user_id ? `<span>👤 ${escapeHtml(item.user_id)}</span>` : ''}
                                        <span>📄 ${escapeHtml(item.source_doc || 'Неизвестно')}</span>
                                        <span>🎯 ${(item.confidence * 100).toFixed(1)}%</span>
                                        <span>📅 ${item.timestamp}</span>
                                    </div>
                                    <div class="history-answer">
                                        <strong>📝 Ответ системы:</strong><br>
                                        ${escapeHtml(item.answer || 'Нет ответа')}
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    document.getElementById('loadMoreBtn').style.display = data.length === 10 ? 'block' : 'none';
                });
        }

        // Функция раскрытия/скрытия деталей карточки
        function toggleHistoryDetails(element) {
            const details = element.querySelector('.history-details');
            const icon = element.querySelector('.history-expand-icon');
            if (details.classList.contains('show')) {
                details.classList.remove('show');
                icon.innerHTML = '▼';
            } else {
                details.classList.add('show');
                icon.innerHTML = '▲';
            }
        }

        function loadMore() { currentPage++; loadHistory(); }

        

        function askQuestion() {
            const question = document.getElementById('question').value;
            if (!question.trim()) return;
            fetch('/ask', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: 'question=' + encodeURIComponent(question) })
                .then(res => res.json())
                .then(data => { document.getElementById('answerArea').innerHTML = data.html; document.getElementById('question').value = ''; });
        }

        function sendFeedback(rating, queryId) {
            if (!queryId) return alert('ID не найден');
            fetch(`/feedback/${queryId}/${rating}`, { method: 'POST' }).then(() => alert('Спасибо!'));
        }

        function escapeHtml(text) { return text?.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m])) || ''; }

        function showLoginModal() { document.getElementById('loginModal').style.display = 'block'; }
        function closeLoginModal() { document.getElementById('loginModal').style.display = 'none'; }

        function login() {
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;
            fetch('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        closeLoginModal();
                        location.reload();  // Перезагружаем страницу, checkAuth сработает при загрузке
                    } else {
                        document.getElementById('loginError').innerText = data.error;
                    }
                });
        }

        function logout() {
            fetch('/logout', { method: 'POST' }).then(() => location.reload());
        }

        function checkAuth() {
            fetch('/check-auth')
                .then(res => res.json())
                .then(data => {
                    if (data.authenticated) {
                        currentUser = data.user;
                        // Показываем информацию о пользователе и кнопку "Выйти"
                        document.getElementById('userStatus').innerHTML = `👤 ${data.user.name} (${data.user.role})<br><button class="login-btn-sidebar" onclick="logout()">Выйти</button>`;
                        document.getElementById('userRoleDisplay').innerText = data.user.name || data.user.username;
                
                        // Показываем Чат и Историю для всех авторизованных пользователей
                        document.getElementById('chatBtn').style.display = 'block';
                        document.getElementById('historyBtn').style.display = 'block';
                
                        // Показываем Аналитику только для эксперта и админа
                        if (data.user.role === 'expert' || data.user.role === 'admin') {
                            document.getElementById('analyticsBtn').style.display = 'block';
                        } else {
                            document.getElementById('analyticsBtn').style.display = 'none';
                        }
                
                        // Показываем Управление документами только для админа
                        if (data.user.role === 'admin') {
                            document.getElementById('documentsBtn').style.display = 'block';
                        } else {
                            document.getElementById('documentsBtn').style.display = 'none';
                        }
                        
                        // Показываем Управление пользователями только для админа
                        if (data.user.role === 'admin') {
                            document.getElementById('usersBtn').style.display = 'block';
                        } else {
                            document.getElementById('usersBtn').style.display = 'none';
                        }
                        
                        // Показываем Журнал событий только для админа
                        if (data.user.role === 'admin') {
                            document.getElementById('eventLogBtn').style.display = 'block';
                        } else {
                            document.getElementById('eventLogBtn').style.display = 'none';
                        }
                
                        // Если текущая вкладка была скрыта и недоступна, переключаем на Чат
                        if (currentView === 'history' && !document.getElementById('historyBtn').style.display === 'block') {
                            showChat();
                        } else if (currentView === 'analytics' && !document.getElementById('analyticsBtn').style.display === 'block') {
                            showChat();
                        } else if (currentView === 'documents' && !document.getElementById('documentsBtn').style.display === 'block') {
                            showChat();
                        }
                    } else {
                        currentUser = null;
                        document.getElementById('userStatus').innerHTML = '';
                        document.getElementById('userRoleDisplay').innerText = 'Не авторизован';
                
                        // Скрываем все кнопки для неавторизованных
                        document.getElementById('chatBtn').style.display = 'none';
                        document.getElementById('historyBtn').style.display = 'none';
                        document.getElementById('analyticsBtn').style.display = 'none';
                        document.getElementById('documentsBtn').style.display = 'none';
                        document.getElementById('usersBtn').style.display = 'none';
                
                        // Показываем только сообщение о необходимости входа
                        document.getElementById('chatView').style.display = 'none';
                        document.getElementById('historyView').style.display = 'none';
                        document.getElementById('analyticsView').style.display = 'none';
                        document.getElementById('documentsView').style.display = 'none';
                        document.getElementById('usersView').style.display = 'none';
                
                        // Показываем приветственный экран
                        document.getElementById('pageTitle').innerText = 'Добро пожаловать';
                        const content = document.getElementById('content');
                        if (!document.getElementById('welcomeMessage')) {
                            const welcomeDiv = document.createElement('div');
                            welcomeDiv.id = 'welcomeMessage';
                            welcomeDiv.className = 'card';
                            welcomeDiv.style.textAlign = 'center';
                            welcomeDiv.style.padding = '60px';
                            welcomeDiv.innerHTML = `
                                <h2>🔐 Добро пожаловать в DocQAnswer</h2>
                                <p style="margin-top: 20px;">Для использования системы необходимо войти под своей учетной записью.</p>
                                <button onclick="showLoginModal()" style="margin-top: 20px;">Войти в систему</button>
                            `;
                            content.innerHTML = '';
                            content.appendChild(welcomeDiv);
                        }
                    }
                });
        }

        checkAuth();
        setTimeout(() => {
            document.getElementById('searchInput')?.addEventListener('input', () => { currentPage = 0; loadHistory(); });
            document.getElementById('filterSelect')?.addEventListener('change', () => { currentPage = 0; loadHistory(); });
        }, 100);
        // Загрузка аналитики
        function loadAnalytics() {
            const period = document.getElementById('periodSelect')?.value || 'week';
            fetch(`/analytics?period=${period}`)
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('analyticsContent').innerHTML = `<p style="color: red;">${data.error}</p>`;
                        return;
                    }
            
                    // Обновляем карточки
                    document.getElementById('statTotalQueries').innerText = data.total_queries;
                    document.getElementById('statSuccessRate').innerHTML = `${data.success_rate}%`;
                    document.getElementById('statAvgTime').innerHTML = `${data.avg_response_time} с`;
                    document.getElementById('statTotalFeedback').innerHTML = data.total_likes + data.total_dislikes;
            
                    // Обновляем метрики
                    const f1Percent = Math.round(data.f1_score * 100);
                    const emPercent = Math.round(data.em_score * 100);
                    document.getElementById('f1Value').innerHTML = `${f1Percent}%`;
                    document.getElementById('f1Bar').style.width = `${f1Percent}%`;
                    document.getElementById('emValue').innerHTML = `${emPercent}%`;
                    document.getElementById('emBar').style.width = `${emPercent}%`;
            
                    // Таблица неудачных запросов
                    const tbody = document.getElementById('failedTableBody');
                    if (data.failed_queries && data.failed_queries.length > 0) {
                        tbody.innerHTML = data.failed_queries.map(q => `
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">${escapeHtml(q.question)}</td>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">${escapeHtml(q.answer || 'Нет ответа')}</td>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">${escapeHtml(q.source || 'Неизвестно')}</td>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">${q.timestamp}</td>
                            </tr>
                        `).join('');
                    } else {
                        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 40px;">✅ Нет неудачных запросов</td></tr>';
                    }
            
                    // Рисуем графики
                    drawDailyChart(data.daily_queries);
                    drawRatingsChart(data.ratings.likes, data.ratings.dislikes);
                })
                .catch(err => {
                    document.getElementById('analyticsContent').innerHTML = `<p style="color: red;">Ошибка загрузки: ${err}</p>`;
                });
        }

        // График запросов по дням
        function drawDailyChart(dailyData) {
            console.log('📊 drawDailyChart вызван, данные:', dailyData);
    
            const canvas = document.getElementById('dailyChart');
            if (!canvas) {
                console.error('❌ Canvas #dailyChart не найден');
                return;
            }
    
            const ctx = canvas.getContext('2d');
            if (!ctx) {
                console.error('❌ Не удалось получить контекст canvas');
                return;
            }
    
            // Проверяем наличие Chart.js
            if (typeof Chart === 'undefined') {
                console.error('❌ Chart.js не загружен! Проверьте подключение библиотеки.');
                document.getElementById('dailyChart').parentElement.innerHTML += '<p style="color: red;">Ошибка: Chart.js не загружен</p>';
                return;
            }
    
            // Удаляем старый график если есть
            if (window.dailyChart) {
                window.dailyChart.destroy();
                window.dailyChart = null;
            }
    
            if (!dailyData || dailyData.length === 0) {
                console.warn('⚠️ Нет данных для графика');
                return;
            }
    
            try {
                window.dailyChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: dailyData.map(d => d.date),
                        datasets: [{
                            label: 'Количество запросов',
                            data: dailyData.map(d => d.count),
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: { legend: { position: 'top' } }
                    }
                });
                console.log('✅ График создан успешно');
            } catch (err) {
                console.error('❌ Ошибка создания графика:', err);
            }
        }

        // Круговая диаграмма оценок
        function drawRatingsChart(likes, dislikes) {
            console.log('📊 drawRatingsChart вызван, likes:', likes, 'dislikes:', dislikes);
    
            const canvas = document.getElementById('ratingsChart');
            if (!canvas) {
                console.error('❌ Canvas #ratingsChart не найден');
                return;
            }
    
            const ctx = canvas.getContext('2d');
            if (!ctx) {
                console.error('❌ Не удалось получить контекст canvas');
                return;
            }
    
            if (typeof Chart === 'undefined') {
                console.error('❌ Chart.js не загружен!');
                document.getElementById('ratingsChart').parentElement.innerHTML += '<p style="color: red;">Ошибка: Chart.js не загружен</p>';
                return;
            }
    
            if (window.ratingsChart) {
                window.ratingsChart.destroy();
                window.ratingsChart = null;
            }
    
            if (likes === 0 && dislikes === 0) {
                console.warn('⚠️ Нет данных для круговой диаграммы');
                return;
            }
    
            try {
                window.ratingsChart = new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: ['👍 Лайки', '👎 Дизлайки'],
                        datasets: [{
                            data: [likes, dislikes],
                            backgroundColor: ['#28a745', '#dc3545'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: { legend: { position: 'bottom' } }
                    }
                });
                console.log('✅ Круговая диаграмма создана успешно');
            } catch (err) {
                console.error('❌ Ошибка создания диаграммы:', err);
            }
        }

        // Экспорт отчёта
        function exportReport() {
            const period = document.getElementById('periodSelect')?.value || 'week';
            window.open(`/export-report?period=${period}`, '_blank');
        }

        // Панель документов
        function showDocuments() {
            if (!currentUser) {
                alert('Необходимо войти в систему');
                return;
            }
            document.getElementById('chatView').style.display = 'none';
            document.getElementById('historyView').style.display = 'none';
            document.getElementById('analyticsView').style.display = 'none';
            document.getElementById('usersView').style.display = 'none';
            document.getElementById('eventLogView').style.display = 'none';
            document.getElementById('documentsView').style.display = 'block';
            document.getElementById('pageTitle').innerText = 'Управление документами';
            document.getElementById('chatBtn').classList.remove('active');
            document.getElementById('historyBtn').classList.remove('active');
            document.getElementById('analyticsBtn').classList.remove('active');
            document.getElementById('usersBtn').classList.remove('active');
            document.getElementById('eventLogBtn').classList.remove('active');
            document.getElementById('documentsBtn').classList.add('active');
            loadDocuments();
        }

        function loadDocuments() {
            fetch('/admin/documents')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('statTotalDocs').innerText = data.total_documents;
                    document.getElementById('statActiveDocs').innerText = data.active_documents;
                    document.getElementById('statTotalChunks').innerText = data.total_chunks;
            
                    const tbody = document.getElementById('documentsTableBody');
                    if (data.documents.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px;">Нет загруженных документов</td></tr>';
                        return;
                    }
            
                    tbody.innerHTML = data.documents.map(doc => `
                        <tr>
                            <td style="padding: 12px; border-bottom: 1px solid #eee;">${escapeHtml(doc.name)}</td>
                            <td style="padding: 12px; border-bottom: 1px solid #eee;">${escapeHtml(doc.version || '1.0')}</td>
                            <td style="padding: 12px; border-bottom: 1px solid #eee;">${doc.upload_date}</td>
                            <td style="padding: 12px; border-bottom: 1px solid #eee;">${escapeHtml(doc.category || 'Общая')}</td>
                            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                                <span style="background: ${doc.status === 'active' ? '#28a745' : '#dc3545'}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px;">
                                    ${doc.status === 'active' ? 'Активен' : 'Архивирован'}
                                </span>
                            </td>
                            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                                <div class="dropdown" style="position: relative; display: inline-block;">
                                    <button onclick="toggleDocMenu(${doc.id})" style="background: #667eea; border: none; border-radius: 6px; padding: 8px 12px; cursor: pointer; color: white; margin-top: 0; display: flex; align-items: center; gap: 5px;">
                                        ⋮ Действия
                                    </button>
                                    <div id="docMenu${doc.id}" class="dropdown-menu" style="display: none; position: absolute; right: 0; background: white; border: 1px solid #ddd; border-radius: 8px; z-index: 100; min-width: 180px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                                        <button onclick="viewDocument('${escapeHtml(doc.name)}')">
                                            👁 Просмотреть
                                        </button>
                                        <button onclick="updateDocumentVersion(${doc.id}, '${escapeHtml(doc.name)}')">
                                            🔄 Обновить версию
                                        </button>
                                        <button onclick="archiveDocument(${doc.id}, '${escapeHtml(doc.name)}')">
                                            📦 Архивировать
                                        </button>
                                        <button onclick="deleteDocument(${doc.id}, '${escapeHtml(doc.name)}')" style="color: #dc3545 !important;">
                                            🗑 Удалить
                                        </button>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                });
        }

        function toggleDocMenu(docId) {
            const menu = document.getElementById(`docMenu${docId}`);
            menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
        }

        // Закрыть меню при клике вне
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.dropdown')) {
                document.querySelectorAll('[id^="docMenu"]').forEach(menu => menu.style.display = 'none');
            }
        });

        function showUploadModal() {
            document.getElementById('uploadModal').style.display = 'block';
            document.getElementById('uploadError').innerText = '';
        }

        function closeUploadModal() {
            document.getElementById('uploadModal').style.display = 'none';
        }

        function uploadDocument() {
            const file = document.getElementById('uploadFile').files[0];
            if (!file) {
                document.getElementById('uploadError').innerText = 'Выберите файл';
                return;
            }
    
            const version = document.getElementById('docVersion').value || '1.0';
            const category = document.getElementById('docCategory').value;
    
            const formData = new FormData();
            formData.append('file', file);
            formData.append('version', version);
            formData.append('category', category);
    
            fetch('/admin/upload', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        closeUploadModal();
                        loadDocuments();
                        alert('Документ успешно загружен!');
                    } else {
                        document.getElementById('uploadError').innerText = data.error;
                    }
                });
        }

        function viewDocument(docName) {
            window.open(`/admin/view/${encodeURIComponent(docName)}`, '_blank');
        }

        function updateDocumentVersion(docId, docName) {
            const newVersion = prompt('Введите новую версию документа:', '1.1');
            if (newVersion) {
                fetch('/admin/update-version', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ doc_id: docId, version: newVersion })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        loadDocuments();
                        alert('Версия обновлена!');
                    } else {
                        alert(data.error);
                    }
                });
            }
        }

        function archiveDocument(docId, docName) {
            if (confirm(`Архивировать документ "${docName}"?`)) {
                fetch('/admin/archive', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ doc_id: docId })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        loadDocuments();
                        alert('Документ архивирован');
                    } else {
                        alert(data.error);
                    }
                });
            }
        }

        function deleteDocument(docId, docName) {
            if (confirm(`Удалить документ "${docName}"? Это действие нельзя отменить.`)) {
                fetch('/admin/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ doc_id: docId })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        loadDocuments();
                        alert('Документ удалён');
                    } else {
                        alert(data.error);
                    }
                });
            }
        }
        // Панель пользователей
        function showUsers() {
            if (!currentUser || currentUser.role !== 'admin') {
                alert('Доступ запрещён. Требуются права администратора.');
                return;
            }
            document.getElementById('chatView').style.display = 'none';
            document.getElementById('historyView').style.display = 'none';
            document.getElementById('analyticsView').style.display = 'none';
            document.getElementById('documentsView').style.display = 'none';
            document.getElementById('eventLogView').style.display = 'none';
            document.getElementById('usersView').style.display = 'block';
            document.getElementById('pageTitle').innerText = 'Управление пользователями';
            document.getElementById('usersBtn').classList.add('active');
            document.getElementById('chatBtn').classList.remove('active');
            document.getElementById('historyBtn').classList.remove('active');
            document.getElementById('analyticsBtn').classList.remove('active');
            document.getElementById('documentsBtn').classList.remove('active');
            document.getElementById('eventLogBtn').classList.remove('active');
            loadUsers();
        }

        function loadUsers() {
            fetch('/admin/users')
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        console.error(data.error);
                        return;
                    }
                    document.getElementById('statTotalUsers').innerText = data.total_users;
                    document.getElementById('statActiveUsers').innerText = data.active_users;
                    document.getElementById('statBlockedUsers').innerText = data.blocked_users;
                    
                    const tbody = document.getElementById('usersTableBody');
                    if (!data.users || data.users.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 40px;">Нет пользователей</td></tr>';
                        return;
                    }
                    
                    tbody.innerHTML = data.users.map(user => {
                        // Проверяем, является ли пользователь текущим (самим администратором)
                        const isCurrentUser = (currentUser && currentUser.username === user.username);
                        
                        const actionsHtml = isCurrentUser ? `
                            <div class="dropdown" style="position: relative; display: inline-block;">
                                <button onclick="toggleUserMenu(${user.id})" style="background: #667eea; border: none; border-radius: 6px; padding: 8px 12px; cursor: pointer; color: white; margin-top: 0;">
                                    ⋮ Действия
                                </button>
                                <div id="userMenu${user.id}" class="dropdown-menu" style="display: none;">
                                    <button onclick="editUser(${user.id})">✏️ Редактировать</button>
                                </div>
                            </div>
                        ` : `
                            <div class="dropdown" style="position: relative; display: inline-block;">
                                <button onclick="toggleUserMenu(${user.id})" style="background: #667eea; border: none; border-radius: 6px; padding: 8px 12px; cursor: pointer; color: white; margin-top: 0;">
                                    ⋮ Действия
                                </button>
                                <div id="userMenu${user.id}" class="dropdown-menu" style="display: none;">
                                    <button onclick="editUser(${user.id})">✏️ Редактировать</button>
                                    <button onclick="toggleUserBlock(${user.id}, '${user.status}')">
                                        ${user.status === 'active' ? '🔒 Заблокировать' : '🔓 Разблокировать'}
                                    </button>
                                    <button onclick="changeUserRole(${user.id}, '${user.role}')">👑 Сменить роль</button>
                                    <button onclick="deleteUser(${user.id}, '${escapeHtml(user.username)}')" style="color: #dc3545 !important;">🗑 Удалить</button>
                                </div>
                            </div>
                        `;
                        
                        return `
                            <tr>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">${escapeHtml(user.username)}</td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">${escapeHtml(user.name || user.username)}</td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">${escapeHtml(user.email || '-')}</td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">
                                    <span style="background: ${user.role === 'admin' ? '#dc3545' : (user.role === 'expert' ? '#ffc107' : '#28a745')}; color: ${user.role === 'expert' ? '#333' : 'white'}; padding: 4px 8px; border-radius: 12px; font-size: 12px;">
                                        ${user.role === 'admin' ? 'Администратор' : (user.role === 'expert' ? 'Эксперт' : 'Сотрудник')}
                                    </span>
                                </td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">
                                    <span style="background: ${user.status === 'active' ? '#28a745' : '#dc3545'}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px;">
                                        ${user.status === 'active' ? 'Активен' : 'Заблокирован'}
                                    </span>
                                </td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">${user.last_login || '-'}</td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">${user.created_at}</td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">
                                    ${actionsHtml}
                                </td>
                            </tr>
                        `;
                    }).join('');
                });
        }

        function toggleUserMenu(userId) {
            const menu = document.getElementById(`userMenu${userId}`);
            if (menu) {
                menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
            }
        }

        function showAddUserModal() {
            document.getElementById('addUserModal').style.display = 'block';
            document.getElementById('addUserError').innerText = '';
            document.getElementById('newUsername').value = '';
            document.getElementById('newEmail').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('newRole').value = 'employee';
        }

        function closeAddUserModal() {
            document.getElementById('addUserModal').style.display = 'none';
        }

        function addUser() {
            const username = document.getElementById('newUsername').value;
            const email = document.getElementById('newEmail').value;
            const password = document.getElementById('newPassword').value;
            const role = document.getElementById('newRole').value;
            
            if (!username || !password) {
                document.getElementById('addUserError').innerText = 'Заполните логин и пароль';
                return;
            }
            
            // Запрещаем создание администратора
            if (role === 'admin') {
                document.getElementById('addUserError').innerText = 'Нельзя создать пользователя с ролью администратора';
                return;
            }
            
            fetch('/admin/users/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password, role })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    closeAddUserModal();
                    loadUsers();
                    alert('Пользователь добавлен');
                } else {
                    document.getElementById('addUserError').innerText = data.error;
                }
            });
        }

        function editUser(userId) {
            // Получаем данные пользователя
            fetch('/admin/users')
                .then(res => res.json())
                .then(data => {
                    const user = data.users.find(u => u.id === userId);
                    if (user) {
                        document.getElementById('editUserId').value = user.id;
                        document.getElementById('editUsername').value = user.username;
                        document.getElementById('editName').value = user.name || user.username;
                        document.getElementById('editEmail').value = user.email || '';
                        document.getElementById('editPassword').value = '';
                        document.getElementById('editUserError').innerText = '';
                        document.getElementById('editUserModal').style.display = 'block';
                    }
                });
        }
        
        function closeEditUserModal() {
            document.getElementById('editUserModal').style.display = 'none';
        }
        
        function saveUserEdit() {
            const userId = document.getElementById('editUserId').value;
            const name = document.getElementById('editName').value;
            const email = document.getElementById('editEmail').value;
            const newPassword = document.getElementById('editPassword').value;
            
            if (!name) {
                document.getElementById('editUserError').innerText = 'Имя обязательно';
                return;
            }
            
            const data = { user_id: parseInt(userId), name, email };
            if (newPassword) {
                data.password = newPassword;
            }
            
            fetch('/admin/users/edit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    closeEditUserModal();
                    loadUsers();
                    alert('Пользователь обновлён');
                } else {
                    document.getElementById('editUserError').innerText = data.error;
                }
            });
        }

        function toggleUserBlock(userId, currentStatus) {
            // Проверяем, не пытается ли администратор заблокировать себя
            fetch('/admin/users')
                .then(res => res.json())
                .then(data => {
                    const user = data.users.find(u => u.id === userId);
                    if (user && currentUser && user.username === currentUser.username) {
                        alert('Вы не можете заблокировать самого себя');
                        return;
                    }
                    
                    const newStatus = currentStatus === 'active' ? 'blocked' : 'active';
                    fetch('/admin/users/block', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, status: newStatus })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            loadUsers();
                            alert(data.message);
                        } else {
                            alert(data.error);
                        }
                    });
                });
        }

        function changeUserRole(userId, currentRole) {
            // Проверяем, не пытается ли администратор изменить роль себе
            fetch('/admin/users')
                .then(res => res.json())
                .then(data => {
                    const user = data.users.find(u => u.id === userId);
                    if (user && currentUser && user.username === currentUser.username) {
                        alert('Вы не можете изменить роль самого себя');
                        return;
                    }
                    
                    const roles = ['employee', 'expert', 'admin'];
                    const roleNames = { employee: 'Сотрудник', expert: 'Эксперт', admin: 'Администратор' };
                    const newRole = prompt(`Выберите новую роль:\n1 - Сотрудник\n2 - Эксперт\n3 - Администратор`, 
                        currentRole === 'employee' ? '1' : (currentRole === 'expert' ? '2' : '3'));
                    
                    if (newRole && ['1', '2', '3'].includes(newRole)) {
                        const roleMap = { '1': 'employee', '2': 'expert', '3': 'admin' };
                        fetch('/admin/users/role', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ user_id: userId, role: roleMap[newRole] })
                        })
                        .then(res => res.json())
                        .then(data => {
                            if (data.success) {
                                loadUsers();
                                alert('Роль изменена');
                            } else {
                                alert(data.error);
                            }
                        });
                    }
                });
        }
        
        function deleteUser(userId, username) {
            // Проверяем, не пытается ли администратор удалить себя
            if (currentUser && username === currentUser.username) {
                alert('Вы не можете удалить самого себя');
                return;
            }
            
            if (confirm(`Удалить пользователя "${username}"? Это действие нельзя отменить.`)) {
                fetch('/admin/users/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        loadUsers();
                        alert('Пользователь удалён');
                    } else {
                        alert(data.error);
                    }
                });
            }
        }
        
        // Журнал событий
        function showEventLog() {
            if (!currentUser || currentUser.role !== 'admin') {
                alert('Доступ запрещён. Требуются права администратора.');
                return;
            }
            document.getElementById('chatView').style.display = 'none';
            document.getElementById('historyView').style.display = 'none';
            document.getElementById('analyticsView').style.display = 'none';
            document.getElementById('documentsView').style.display = 'none';
            document.getElementById('usersView').style.display = 'none';
            document.getElementById('eventLogView').style.display = 'block';
            document.getElementById('pageTitle').innerText = 'Журнал событий';
            document.getElementById('eventLogBtn').classList.add('active');
            document.getElementById('chatBtn').classList.remove('active');
            document.getElementById('historyBtn').classList.remove('active');
            document.getElementById('analyticsBtn').classList.remove('active');
            document.getElementById('documentsBtn').classList.remove('active');
            document.getElementById('usersBtn').classList.remove('active');
            loadEventLog();
            
            // Сбрасываем пагинацию
            eventLogPage = 0;
            hasMoreEvents = true;
            loadEventLog(true);
        }

        function loadEventLog(reset = true) {
            if (isLoadingEvents) return;
            isLoadingEvents = true;
    
            if (reset) {
                eventLogPage = 0;
                hasMoreEvents = true;
                const tbody = document.getElementById('eventLogTableBody');
                if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px;">\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430...</td></tr>';
                const loadMoreBtn = document.getElementById('eventLogLoadMoreBtn');
                if (loadMoreBtn) loadMoreBtn.style.display = 'none';
            }
    
            var search = '';
            var period = 'today';
            var searchInput = document.getElementById('eventSearch');
            var periodSelect = document.getElementById('eventPeriod');
            if (searchInput) search = searchInput.value;
            if (periodSelect) period = periodSelect.value;
    
            fetch('/admin/event-log?page=' + eventLogPage + '&period=' + encodeURIComponent(period) + '&search=' + encodeURIComponent(search))
                .then(function(res) { return res.json(); })
                .then(function(data) {
                    if (data.error) {
                        console.error(data.error);
                        isLoadingEvents = false;
                        return;
                    }
            
                    var totalCountEl = document.getElementById('eventTotalCount');
                    var periodCountEl = document.getElementById('eventPeriodCount');
                    if (totalCountEl) totalCountEl.innerText = data.total_count;
                    if (periodCountEl) periodCountEl.innerText = data.period_count;
                    
                    var tbody = document.getElementById('eventLogTableBody');
                    if (!tbody) {
                        isLoadingEvents = false;
                        return;
                    }
            
                    if (reset) {
                        tbody.innerHTML = '';
                    }
                    
                    if (!data.events || data.events.length === 0) {
                        if (reset) {
                            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px;">\u041d\u0435\u0442 \u0441\u043e\u0431\u044b\u0442\u0438\u0439</td></tr>';
                        }
                        hasMoreEvents = false;
                        var loadMoreBtn = document.getElementById('eventLogLoadMoreBtn');
                        if (loadMoreBtn) loadMoreBtn.style.display = 'none';
                        isLoadingEvents = false;
                        return;
                    }
            
                    var html = '';
                    for (var i = 0; i < data.events.length; i++) {
                        var event = data.events[i];
                        var bgColor = '#28a745';
                        var typeText = '\u0414\u0435\u0439\u0441\u0442\u0432\u0438\u0435';
                        if (event.event_type === 'login') {
                            bgColor = '#28a745';
                            typeText = '\u0412\u0445\u043e\u0434';
                        } else if (event.event_type === 'query') {
                            bgColor = '#667eea';
                            typeText = '\u0417\u0430\u043f\u0440\u043e\u0441';
                        } else if (event.event_type === 'feedback') {
                            bgColor = '#ffc107';
                            typeText = '\u041e\u0446\u0435\u043d\u043a\u0430';
                        }
                        
                        var actionDisplay = escapeHtml(event.action);
                        actionDisplay = actionDisplay.replace(/\\n/g, '<br>');
                        
                        html += '<tr>';
                        html += '<td style="padding: 12px; border-bottom: 1px solid #eee; vertical-align: top;">' + escapeHtml(event.user_id) + '</td>';
                        html += '<td style="padding: 12px; border-bottom: 1px solid #eee; white-space: nowrap;">' + event.timestamp + '</td>';
                        html += '<td style="padding: 12px; border-bottom: 1px solid #eee;">';
                        html += '<span style="background: ' + bgColor + '; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px;">' + typeText + '</span>';
                        html += '</td>';
                        html += '<td style="padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; max-width: 400px;">';
                        html += '<div style="white-space: pre-wrap; word-break: break-word;">' + actionDisplay + '</div>';
                        html += '</td>';
                        html += '<td style="padding: 12px; border-bottom: 1px solid #eee;">' + escapeHtml(event.source || '-') + '</td>';
                        html += '</tr>';
                    }
            
                    if (reset) {
                        tbody.innerHTML = html;
                    } else {
                        tbody.insertAdjacentHTML('beforeend', html);
                    }
                    
                    // Проверяем, есть ли ещё события
                    hasMoreEvents = data.events.length === 20;
                    var loadMoreBtn = document.getElementById('eventLogLoadMoreBtn');
                    if (loadMoreBtn) {
                        if (hasMoreEvents) {
                            loadMoreBtn.style.display = 'block';
                        } else {
                            loadMoreBtn.style.display = 'none';
                        }
                    }
                    
                    isLoadingEvents = false;
                })
                .catch(function(err) {
                    console.error('Error:', err);
                    var tbody = document.getElementById('eventLogTableBody');
                    if (tbody && reset) {
                        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px;">\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438</td></tr>';
                    }
                    isLoadingEvents = false;
                });
        }
        
        function loadMoreEvents() {
            if (!hasMoreEvents || isLoadingEvents) return;
            eventLogPage++;
            loadEventLog(false);
        }
        
        function exportEventLog() {
            const search = document.getElementById('eventSearch').value;
            const period = document.getElementById('eventPeriod').value;
            window.open(`/admin/event-log/export?period=${period}&search=${encodeURIComponent(search)}`, '_blank');
        }
    </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_TEMPLATE


@app.post("/ask")
async def ask(question: str = Form(...), request: Request = None):
    # Определяем user_id по сессии
    user_id = "employee_1"
    if request:
        session_token = request.cookies.get("session_token")
        if session_token:
            session = get_session(session_token)
            if session:
                user_id = session["user"]["username"]

    result = qa_pipeline.ask(question, user_id=user_id)
    query_id = get_query_id(user_id)

    # Сохраняем событие с ответом и уверенностью
    answer_preview = result.get('answer', '')[:100]
    confidence = result.get('confidence', 0)
    add_event(user_id, "query",
              f"Вопрос: {question[:80]}...\nОтвет: {answer_preview}...\nУверенность: {confidence:.0%}",
              result.get('source'))

    answer_html = f"""
    <div class="answer-box">
        <strong>📝 Ответ:</strong>
        <p style="margin-top: 10px;">{result.get('answer', 'Ответ не найден')}</p>
        <div class="source-info">📄 Источник: {result.get('source', 'Неизвестно')}</div>
        <div class="confidence">🎯 Уверенность: {(result.get('confidence', 0) * 100):.1f}%</div>
        <div class="feedback-buttons">
            <button class="btn-like" onclick="sendFeedback('like', {query_id})">👍 Да</button>
            <button class="btn-dislike" onclick="sendFeedback('dislike', {query_id})">👎 Нет</button>
        </div>
    </div>
    """
    return {"html": answer_html}


@app.post("/feedback/{query_id}/{rating}")
async def feedback(query_id: int, rating: str, request: Request = None):
    if rating not in ['like', 'dislike']:
        raise HTTPException(status_code=400, detail="Некорректная оценка")
    is_positive = (rating == 'like')

    # Получаем user_id из сессии
    user_id = "employee_1"
    question_text = ""
    if request:
        session_token = request.cookies.get("session_token")
        if session_token:
            session = get_session(session_token)
            if session:
                user_id = session["user"]["username"]

    try:
        conn = sqlite3.connect(Path("data/docqanswer.db"))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO feedback (query_id, is_positive) VALUES (?, ?)", (query_id, is_positive))

        # Получаем текст вопроса для этого query_id
        cursor.execute("SELECT question FROM query_history WHERE id = ?", (query_id,))
        row = cursor.fetchone()
        if row:
            question_text = row[0][:80]

        conn.commit()
        conn.close()

        # Сохраняем событие с информацией о вопросе
        rating_emoji = "👍 Лайк" if is_positive else "👎 Дизлайк"
        add_event(user_id, "feedback",
                  f"Оценка: {rating_emoji}\nВопрос: {question_text}...",
                  None)

        return {"status": "ok", "message": "Спасибо за оценку!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
async def get_history(page: int = 0, filter: str = "all", search: str = "", request: Request = None):
    # Определяем user_id и роль по сессии
    user_id = "employee_1"
    user_role = "employee"
    if request:
        session_token = request.cookies.get("session_token")
        if session_token:
            session = get_session(session_token)
            if session:
                user_id = session["user"]["username"]
                user_role = session["user"]["role"]

    try:
        conn = sqlite3.connect(Path("data/docqanswer.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        limit = 10
        offset = page * limit

        # Для эксперта и админа показываем ВСЕ запросы
        if user_role in ["expert", "admin"]:
            query = """
                SELECT q.id, q.user_id, q.question, q.answer, q.source_doc, q.confidence, q.timestamp, f.is_positive as feedback
                FROM query_history q
                LEFT JOIN feedback f ON q.id = f.query_id
                WHERE 1=1
            """
            params = []
        else:
            # Для сотрудника — только его запросы
            query = """
                SELECT q.id, q.user_id, q.question, q.answer, q.source_doc, q.confidence, q.timestamp, f.is_positive as feedback
                FROM query_history q
                LEFT JOIN feedback f ON q.id = f.query_id
                WHERE q.user_id = ?
            """
            params = [user_id]

        import datetime
        today = datetime.datetime.now().date()
        if filter == "today":
            query += " AND DATE(q.timestamp) = ?"
            params.append(today.isoformat())
        elif filter == "yesterday":
            yesterday = today - datetime.timedelta(days=1)
            query += " AND DATE(q.timestamp) = ?"
            params.append(yesterday.isoformat())
        elif filter == "week":
            week_ago = today - datetime.timedelta(days=7)
            query += " AND DATE(q.timestamp) >= ?"
            params.append(week_ago.isoformat())
        elif filter == "month":
            month_ago = today - datetime.timedelta(days=30)
            query += " AND DATE(q.timestamp) >= ?"
            params.append(month_ago.isoformat())

        if search:
            query += " AND q.question LIKE ?"
            params.append(f"%{search}%")

        query += " ORDER BY q.timestamp DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(offset)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [{
            "id": row["id"],
            "user_id": row["user_id"] if user_role in ["expert", "admin"] else None,
            "question": row["question"],
            "answer": (row["answer"][:500] + "...") if row["answer"] and len(row["answer"]) > 500 else (row["answer"] or ""),
            "source_doc": row["source_doc"],
            "confidence": row["confidence"],
            "timestamp": row["timestamp"],
            "feedback": row["feedback"] if row["feedback"] is not None else None
        } for row in rows]
    except Exception as e:
        print(f"Ошибка: {e}")
        return []


@app.get("/analytics")
async def get_analytics(request: Request, period: str = "week"):
    """
    period: 'today', 'week', 'month', 'all'
    """
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}

    session = get_session(session_token)
    if not session or session["user"]["role"] not in ["expert", "admin"]:
        return {"error": "Доступ запрещён"}

    conn = sqlite3.connect(Path("data/docqanswer.db"))
    cursor = conn.cursor()

    import datetime
    today = datetime.datetime.now().date()

    # Определяем дату начала периода
    start_date = None
    if period == "today":
        start_date = today
    elif period == "week":
        start_date = today - datetime.timedelta(days=7)
    elif period == "month":
        start_date = today - datetime.timedelta(days=30)

    # Общее количество запросов за период
    if start_date:
        cursor.execute("SELECT COUNT(*) FROM query_history WHERE DATE(timestamp) >= ?", (start_date.isoformat(),))
    else:
        cursor.execute("SELECT COUNT(*) FROM query_history")
    total_queries = cursor.fetchone()[0]

    # Лайки и дизлайки за период
    if start_date:
        cursor.execute("""
            SELECT COUNT(*) FROM feedback f
            JOIN query_history q ON f.query_id = q.id
            WHERE f.is_positive = 1 AND DATE(q.timestamp) >= ?
        """, (start_date.isoformat(),))
        total_likes = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM feedback f
            JOIN query_history q ON f.query_id = q.id
            WHERE f.is_positive = 0 AND DATE(q.timestamp) >= ?
        """, (start_date.isoformat(),))
        total_dislikes = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT COUNT(*) FROM feedback WHERE is_positive = 1")
        total_likes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM feedback WHERE is_positive = 0")
        total_dislikes = cursor.fetchone()[0]

    # Среднее время ответа
    if start_date:
        cursor.execute("""
            SELECT AVG(response_time) FROM query_history
            WHERE response_time IS NOT NULL AND DATE(timestamp) >= ?
        """, (start_date.isoformat(),))
    else:
        cursor.execute("SELECT AVG(response_time) FROM query_history WHERE response_time IS NOT NULL")
    avg_response_time_row = cursor.fetchone()
    avg_response_time = round(avg_response_time_row[0], 2) if avg_response_time_row and avg_response_time_row[0] else 0

    # Запросы по дням
    if start_date:
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM query_history
            WHERE DATE(timestamp) >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (start_date.isoformat(),))
    else:
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM query_history
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 30
        """)
    daily_queries = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]

    # Оценки пользователей (для круговой диаграммы)
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN f.is_positive = 1 THEN 1 ELSE 0 END) as likes,
            SUM(CASE WHEN f.is_positive = 0 THEN 1 ELSE 0 END) as dislikes
        FROM feedback f
    """)
    ratings_row = cursor.fetchone()
    likes_total = ratings_row[0] if ratings_row[0] else 0
    dislikes_total = ratings_row[1] if ratings_row[1] else 0

    # Неудачные запросы (дизлайки)
    if start_date:
        cursor.execute("""
            SELECT q.id, q.user_id, q.question, q.answer, q.source_doc, q.confidence, q.timestamp
            FROM query_history q
            JOIN feedback f ON q.id = f.query_id
            WHERE f.is_positive = 0 AND DATE(q.timestamp) >= ?
            ORDER BY q.timestamp DESC
            LIMIT 20
        """, (start_date.isoformat(),))
    else:
        cursor.execute("""
            SELECT q.id, q.user_id, q.question, q.answer, q.source_doc, q.confidence, q.timestamp
            FROM query_history q
            JOIN feedback f ON q.id = f.query_id
            WHERE f.is_positive = 0
            ORDER BY q.timestamp DESC
            LIMIT 20
        """)
    failed_queries = [{
        "id": row[0],
        "user_id": row[1],
        "question": row[2],
        "answer": (row[3][:200] + "...") if row[3] and len(row[3]) > 200 else row[3],
        "source": row[4],
        "confidence": row[5],
        "timestamp": row[6]
    } for row in cursor.fetchall()]

    # === РАСЧЁТ МЕТРИК F1 И EM ===
    # Для расчёта нужны правильные ответы. Будем использовать feedback:
    # Лайк = ответ правильный, Дизлайк = ответ неправильный
    # TP = лайки, FP = дизлайки (упрощённо)
    # F1 = 2 * precision * recall / (precision + recall)
    # где precision = TP / (TP + FP), recall = TP / (TP + FN) но FN у нас нет

    # Метрики F1 и EM
    tp = total_likes # True Positives (правильные ответы)
    fp = total_dislikes # False Positives (неправильные ответы)

    if tp + fp > 0:
        precision = tp / (tp + fp)
        recall = tp / (tp + fp)
        f1_score = round(2 * (precision * recall) / (precision + recall), 3) if (precision + recall) > 0 else 0
    else:
        f1_score = 0

    # EM (Exact Match) — процент ответов с высокой уверенностью (>0.8)
    if start_date:
        cursor.execute("""
            SELECT COUNT(*) FROM query_history
            WHERE confidence > 0.8 AND DATE(timestamp) >= ?
        """, (start_date.isoformat(),))
        high_confidence = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM query_history WHERE DATE(timestamp) >= ?", (start_date.isoformat(),))
        total_in_period = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT COUNT(*) FROM query_history WHERE confidence > 0.8")
        high_confidence = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM query_history")
        total_in_period = cursor.fetchone()[0]

    em_score = round(high_confidence / total_in_period, 3) if total_in_period > 0 else 0

    # Доля успешных ответов
    total_feedback = (total_likes + total_dislikes) if (total_likes + total_dislikes) > 0 else 1
    success_rate = round(total_likes / total_feedback * 100, 1)

    conn.close()

    return {
        "total_queries": total_queries,
        "total_likes": total_likes,
        "total_dislikes": total_dislikes,
        "success_rate": success_rate,
        "avg_response_time": avg_response_time,
        "daily_queries": daily_queries,
        "ratings": {"likes": likes_total, "dislikes": dislikes_total},
        "failed_queries": failed_queries,
        "f1_score": f1_score,
        "em_score": em_score
    }


@app.post("/login")
async def login(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    auth_result = authenticate(username, password)

    # Проверка на блокировку
    if auth_result and auth_result.get("blocked"):
        return {"success": False, "error": "Пользователь заблокирован. Обратитесь к администратору."}

    # Проверка на успешную аутентификацию
    if auth_result:
        session_token = create_session(auth_result)
        response = JSONResponse({"success": True, "user": auth_result})
        response.set_cookie(key="session_token", value=session_token, httponly=True, max_age=28800)

        # Обновляем время последнего входа
        users = get_users()
        for u in users:
            if u["username"] == username:
                u["last_login"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                u["status"] = "active"
                save_users(users)
                break

        add_event(username, "login", f"Вход в систему", None)

        return response

    return {"success": False, "error": "Неверный логин или пароль"}


@app.post("/logout")
async def logout(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token:
        auth_logout(session_token)
    response = JSONResponse({"success": True})
    response.delete_cookie("session_token")
    return response


@app.get("/check-auth")
async def check_auth(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token:
        session = get_session(session_token)
        if session:
            return {"authenticated": True, "user": session["user"]}
    return {"authenticated": False}


@app.get("/export-report")
async def export_report(request: Request, period: str = "week"):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}

    session = get_session(session_token)
    if not session or session["user"]["role"] not in ["expert", "admin"]:
        return {"error": "Доступ запрещён"}

    import datetime
    import csv
    from io import StringIO

    today = datetime.datetime.now().date()
    if period == "today":
        start_date = today
    elif period == "week":
        start_date = today - datetime.timedelta(days=7)
    elif period == "month":
        start_date = today - datetime.timedelta(days=30)
    else:
        start_date = None

    conn = sqlite3.connect(Path("data/docqanswer.db"))
    cursor = conn.cursor()

    if start_date:
        cursor.execute("""
            SELECT q.id, q.user_id, q.question, q.answer, q.source_doc, q.confidence, q.timestamp,
                   f.is_positive as feedback
            FROM query_history q
            LEFT JOIN feedback f ON q.id = f.query_id
            WHERE DATE(q.timestamp) >= ?
            ORDER BY q.timestamp DESC
        """, (start_date.isoformat(),))
    else:
        cursor.execute("""
            SELECT q.id, q.user_id, q.question, q.answer, q.source_doc, q.confidence, q.timestamp,
                   f.is_positive as feedback
            FROM query_history q
            LEFT JOIN feedback f ON q.id = f.query_id
            ORDER BY q.timestamp DESC
        """)

    rows = cursor.fetchall()
    conn.close()

    # Создаём CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Пользователь', 'Вопрос', 'Ответ', 'Источник', 'Уверенность', 'Дата', 'Оценка'])

    for row in rows:
        feedback_str = ""
        if row[7] == 1:
            feedback_str = "Лайк"
        elif row[7] == 0:
            feedback_str = "Дизлайк"

        writer.writerow([
            row[0], row[1], row[2], row[3], row[4], row[5], row[6], feedback_str
        ])

    from fastapi.responses import Response
    return Response(
        content=output.getvalue().encode('utf-8-sig'),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=report_{period}_{datetime.datetime.now().strftime('%Y%m%d')}.csv"}
    )


# === АДМИН: Управление документами ===

# Хранилище метаданных документов (в реальности — отдельная таблица в БД)
DOCUMENTS_DB = Path("data/documents_meta.json")


def init_documents_db():
    if not DOCUMENTS_DB.exists():
        with open(DOCUMENTS_DB, 'w', encoding='utf-8') as f:
            json.dump([], f)


def get_documents():
    with open(DOCUMENTS_DB, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_documents(docs):
    with open(DOCUMENTS_DB, 'w', encoding='utf-8') as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


init_documents_db()


@app.get("/admin/documents")
async def get_documents_list(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    docs = get_documents()

    # Подсчёт чанков
    import json
    chunks_file = Path("data/chunks/all_chunks.json")
    total_chunks = 0
    if chunks_file.exists():
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
            total_chunks = len(chunks)

    return {
        "total_documents": len(docs),
        "active_documents": len([d for d in docs if d.get("status") == "active"]),
        "total_chunks": total_chunks,
        "documents": docs
    }


@app.post("/admin/upload")
async def upload_document(request: Request, file: UploadFile = File(...), version: str = Form("1.0"),
                          category: str = Form("Общая")):

    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    # Сохраняем файл
    file_path = Path("data/raw") / file.filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    with open(file_path, 'wb') as f:
        f.write(content)

    # Добавляем метаданные
    docs = get_documents()
    docs.append({
        "id": len(docs) + 1,
        "name": file.filename,
        "version": version,
        "category": category,
        "upload_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active"
    })
    save_documents(docs)

    # Переиндексируем документы
    import subprocess
    subprocess.run([sys.executable, "src/data/loader.py"], capture_output=True)
    subprocess.run([sys.executable, "src/retriever/faiss_indexer.py"], capture_output=True)

    return {"success": True}


@app.post("/admin/update-version")
async def update_version(request: Request):
    data = await request.json()
    doc_id = data.get("doc_id")
    new_version = data.get("version")

    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    docs = get_documents()
    for doc in docs:
        if doc["id"] == doc_id:
            doc["version"] = new_version
            save_documents(docs)
            return {"success": True}
    return {"error": "Документ не найден"}


@app.post("/admin/archive")
async def archive_document(request: Request):
    data = await request.json()
    doc_id = data.get("doc_id")

    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    docs = get_documents()
    for doc in docs:
        if doc["id"] == doc_id:
            doc["status"] = "archived"
            save_documents(docs)
            return {"success": True}
    return {"error": "Документ не найден"}


@app.post("/admin/delete")
async def delete_document(request: Request):
    data = await request.json()
    doc_id = data.get("doc_id")

    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    # Находим документ
    docs = get_documents()
    doc_to_delete = None
    for doc in docs:
        if doc["id"] == doc_id:
            doc_to_delete = doc
            break

    if doc_to_delete:
        # Удаляем файл
        file_path = Path("data/raw") / doc_to_delete["name"]
        if file_path.exists():
            file_path.unlink()

        # Удаляем из списка
        docs = [d for d in docs if d["id"] != doc_id]
        save_documents(docs)

        # Переиндексируем
        import subprocess
        subprocess.run([sys.executable, "src/data/loader.py"], capture_output=True)
        subprocess.run([sys.executable, "src/retriever/faiss_indexer.py"], capture_output=True)

        return {"success": True}

    return {"error": "Документ не найден"}


@app.get("/admin/view/{doc_name}")
async def view_document(request: Request, doc_name: str):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    file_path = Path("data/raw") / doc_name
    if file_path.exists():
        from fastapi.responses import FileResponse
        return FileResponse(file_path)
    return {"error": "Файл не найден"}


# === АДМИН: Управление пользователями ===

USERS_DB = Path("data/users.json")


def init_users_db():
    if not USERS_DB.exists():
        default_users = [
            {"id": 1, "username": "employee", "email": "", "password_hash": hashlib.sha256("123".encode()).hexdigest(),
             "role": "employee", "status": "active", "last_login": None,
             "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"id": 2, "username": "expert", "email": "",
             "password_hash": hashlib.sha256("expert456".encode()).hexdigest(), "role": "expert", "status": "active",
             "last_login": None, "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"id": 3, "username": "admin", "email": "",
             "password_hash": hashlib.sha256("admin789".encode()).hexdigest(), "role": "admin", "status": "active",
             "last_login": None, "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        ]
        with open(USERS_DB, 'w', encoding='utf-8') as f:
            json.dump(default_users, f, ensure_ascii=False, indent=2)


def get_users():
    with open(USERS_DB, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_users(users):
    with open(USERS_DB, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


init_users_db()


@app.get("/admin/users")
async def get_users_list(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    users = get_users()
    total_users = len(users)
    active_users = len([u for u in users if u.get("status") == "active"])
    blocked_users = len([u for u in users if u.get("status") == "blocked"])

    return {
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users,
        "users": users
    }


@app.post("/admin/users/add")
async def add_user_endpoint(request: Request):
    data = await request.json()
    username = data.get("username")
    email = data.get("email", "")
    password = data.get("password")
    role = data.get("role", "employee")

    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    if not username or not password:
        return {"error": "Логин и пароль обязательны"}

    users = get_users()
    if any(u["username"] == username for u in users):
        return {"error": "Пользователь с таким логином уже существует"}

    # Добавляем в auth.py
    if not add_user(username, password, role):
        return {"error": "Не удалось создать пользователя"}

    new_id = max([u["id"] for u in users]) + 1 if users else 1
    new_user = {
        "id": new_id,
        "username": username,
        "email": email,
        "password_hash": hashlib.sha256(password.encode()).hexdigest(),
        "role": role,
        "status": "active",
        "last_login": None,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    users.append(new_user)
    save_users(users)

    return {"success": True}


@app.post("/admin/users/block")
async def block_user(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    new_status = data.get("status")  # 'active' или 'blocked'

    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    users = get_users()
    for user in users:
        if user["id"] == user_id:
            username = user["username"]
            # Обновляем статус в auth.py
            if set_user_status(username, new_status):
                user["status"] = new_status
                save_users(users)
                message = "Пользователь разблокирован" if new_status == "active" else "Пользователь заблокирован"
                return {"success": True, "message": message}
            return {"error": "Не удалось изменить статус"}
    return {"error": "Пользователь не найден"}


@app.post("/admin/users/role")
async def change_role_endpoint(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    new_role = data.get("role")

    # Запрещаем назначение роли администратора
    if new_role == "admin":
        return {"success": False, "error": "Назначение роли администратора запрещено"}

    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    users = get_users()
    for user in users:
        if user["id"] == user_id:
            # Обновляем роль в auth.py
            update_user_role(user["username"], new_role)
            user["role"] = new_role
            save_users(users)
            return {"success": True}
    return {"error": "Пользователь не найден"}


@app.post("/admin/users/delete")
async def delete_user_endpoint(request: Request):
    data = await request.json()
    user_id = data.get("user_id")

    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    users = get_users()
    user_to_delete = None
    for user in users:
        if user["id"] == user_id:
            user_to_delete = user
            break

    if user_to_delete:
        # Удаляем из auth.py
        auth_delete_user(user_to_delete["username"])
        users = [u for u in users if u["id"] != user_id]
        save_users(users)
        return {"success": True}

    return {"error": "Пользователь не найден"}


@app.post("/admin/users/edit")
async def edit_user(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    name = data.get("name")
    email = data.get("email")
    new_password = data.get("password", "")

    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    users = get_users()
    for user in users:
        if user["id"] == user_id:
            username = user["username"]

            # Обновляем имя в auth.py
            from src.auth import update_user_name
            update_user_name(username, name)

            # Обновляем пароль если указан
            if new_password:
                import hashlib
                from src.auth import hash_password, USERS, save_users_to_file
                if username in USERS:
                    USERS[username]["password_hash"] = hash_password(new_password)
                    save_users_to_file(USERS)

            # Обновляем в users.json (без роли)
            user["name"] = name
            user["email"] = email
            save_users(users)

            return {"success": True}

    return {"error": "Пользователь не найден"}


# === АДМИН: Журнал событий ===

# Хранилище событий
EVENTS_DB = Path("data/events.json")


def init_events_db():
    if not EVENTS_DB.exists():
        with open(EVENTS_DB, 'w', encoding='utf-8') as f:
            json.dump([], f)


def add_event(user_id: str, event_type: str, action: str, source: str = None):
    """Добавляет событие в журнал"""
    events = get_events()
    events.append({
        "id": len(events) + 1,
        "user_id": user_id,
        "event_type": event_type,  # login, query, feedback
        "action": action,
        "source": source,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    # Ограничиваем количество событий (храним последние 1000)
    if len(events) > 1000:
        events = events[-1000:]
    with open(EVENTS_DB, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def get_events():
    with open(EVENTS_DB, 'r', encoding='utf-8') as f:
        return json.load(f)


init_events_db()


@app.get("/admin/event-log")
async def get_event_log(request: Request, period: str = "today", search: str = "", page: int = 0):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    events = get_events()

    # Фильтр по периоду
    today = datetime.datetime.now().date()
    filtered_events = []

    for event in events:
        event_date = datetime.datetime.strptime(event["timestamp"], "%Y-%m-%d %H:%M:%S").date()

        if period == "today" and event_date != today:
            continue
        elif period == "yesterday" and event_date != today - datetime.timedelta(days=1):
            continue
        elif period == "week" and event_date < today - datetime.timedelta(days=7):
            continue
        elif period == "month" and event_date < today - datetime.timedelta(days=30):
            continue

        if search:
            search_lower = search.lower()
            matched = False
            if search_lower in event["action"].lower():
                matched = True
            elif search_lower in event["user_id"].lower():
                matched = True
            elif event.get("source") and search_lower in event["source"].lower():
                matched = True
            if not matched:
                continue

        filtered_events.append(event)

    # Сортируем по времени (сначала новые)
    filtered_events.sort(key=lambda x: x["timestamp"], reverse=True)

    total_count = len(events)
    period_count = len(filtered_events)

    # Пагинация
    limit = 20
    offset = page * limit
    paginated_events = filtered_events[offset:offset + limit]

    return {
        "total_count": total_count,
        "period_count": period_count,
        "events": paginated_events
    }


@app.get("/admin/event-log/export")
async def export_event_log(request: Request, period: str = "today", search: str = ""):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"error": "Не авторизован"}
    session = get_session(session_token)
    if not session or session["user"]["role"] != "admin":
        return {"error": "Доступ запрещён"}

    events = get_events()

    import datetime
    today = datetime.datetime.now().date()
    filtered_events = []

    for event in events:
        event_date = datetime.datetime.strptime(event["timestamp"], "%Y-%m-%d %H:%M:%S").date()

        if period == "today" and event_date != today:
            continue
        elif period == "yesterday" and event_date != today - datetime.timedelta(days=1):
            continue
        elif period == "week" and event_date < today - datetime.timedelta(days=7):
            continue
        elif period == "month" and event_date < today - datetime.timedelta(days=30):
            continue

        if search:
            search_lower = search.lower()
            matched = False
            if search_lower in event["action"].lower():
                matched = True
            elif search_lower in event["user_id"].lower():
                matched = True
            elif event.get("source") and search_lower in event["source"].lower():
                matched = True
            if not matched:
                continue

        filtered_events.append(event)

    # Создаём CSV
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Пользователь', 'Время', 'Тип события', 'Действие', 'Источник'])

    for event in filtered_events:
        event_type_str = ""
        if event["event_type"] == "login":
            event_type_str = "Вход"
        elif event["event_type"] == "query":
            event_type_str = "Запрос"
        elif event["event_type"] == "feedback":
            event_type_str = "Оценка"
        else:
            event_type_str = event["event_type"]

        writer.writerow([
            event["id"], event["user_id"], event["timestamp"],
            event_type_str, event["action"], event.get("source", "")
        ])

    return Response(
        content=output.getvalue().encode('utf-8-sig'),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=event_log_{period}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

if __name__ == "__main__":
    import uvicorn

    print("\n🌐 Запуск DocQAnswer на http://localhost:8000")
    print("👤 Логины: employee/123, expert/expert456, admin/admin789")
    uvicorn.run(app, host="0.0.0.0", port=8000)
