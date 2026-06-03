"""
Простая система аутентификации с ролями
"""

import hashlib
import secrets
from typing import Optional, Dict
from datetime import datetime, timedelta
import json
from pathlib import Path

# Глобальное хранилище сессий
_sessions: Dict[str, dict] = {}

# Путь к файлу с пользователями
USERS_DB = Path(__file__).parent.parent / "data" / "users.json"


def load_users_from_file() -> Dict:
    """Загружает пользователей из файла"""
    if USERS_DB.exists():
        with open(USERS_DB, 'r', encoding='utf-8') as f:
            users_list = json.load(f)
            # Преобразуем список в словарь для быстрого доступа
            users = {}
            for u in users_list:
                users[u["username"]] = {
                    "password_hash": u["password_hash"],
                    "role": u["role"],
                    "name": u.get("name", u["username"]),
                    "status": u.get("status", "active")
                }
            return users
    return {}


def save_users_to_file(users: Dict):
    """Сохраняет пользователей в файл"""
    users_list = []
    for username, data in users.items():
        users_list.append({
            "username": username,
            "password_hash": data["password_hash"],
            "role": data["role"],
            "name": data.get("name", username),
            "status": data.get("status", "active")
        })
    USERS_DB.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_DB, 'w', encoding='utf-8') as f:
        json.dump(users_list, f, ensure_ascii=False, indent=2)


# Загружаем пользователей
USERS = load_users_from_file()

# Если файл пустой, создаём пользователей по умолчанию
if not USERS:
    USERS = {
        "employee": {
            "password_hash": hashlib.sha256("123".encode()).hexdigest(),
            "role": "employee",
            "name": "Иван Петров",
            "status": "active"
        },
        "expert": {
            "password_hash": hashlib.sha256("expert456".encode()).hexdigest(),
            "role": "expert",
            "name": "Мария Соколова",
            "status": "active"
        },
        "admin": {
            "password_hash": hashlib.sha256("admin789".encode()).hexdigest(),
            "role": "admin",
            "name": "Алексей Иванов",
            "status": "active"
        }
    }
    save_users_to_file(USERS)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username: str, password: str) -> Optional[dict]:
    """
    Возвращает информацию о пользователе при успешной аутентификации.
    Если пользователь заблокирован, возвращает словарь с ключом 'blocked': True
    """
    if username not in USERS:
        return None

    user = USERS[username]

    # Проверка на блокировку
    if user.get("status") == "blocked":
        return {"blocked": True, "username": username, "name": user.get("name", username)}

    if user["password_hash"] == hash_password(password):
        return {
            "username": username,
            "role": user["role"],
            "name": user.get("name", username),
            "status": user.get("status", "active")
        }
    return None


def create_session(user_info: dict) -> str:
    session_token = secrets.token_urlsafe(32)
    _sessions[session_token] = {
        "user": user_info,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=8)
    }
    print(f"✅ Сессия создана: {session_token[:20]}... для {user_info['name']}")
    print(f"   Всего активных сессий: {len(_sessions)}")
    return session_token


def get_session(session_token: str) -> Optional[dict]:
    if session_token not in _sessions:
        print(f"❌ Токен не найден: {session_token[:20]}...")
        return None

    session = _sessions[session_token]
    if datetime.now() > session["expires_at"]:
        print(f"⏰ Сессия истекла: {session_token[:20]}...")
        del _sessions[session_token]
        return None

    return session


def logout(session_token: str) -> None:
    if session_token in _sessions:
        del _sessions[session_token]
        print(f"👋 Сессия удалена: {session_token[:20]}...")


def get_active_sessions_count() -> int:
    return len(_sessions)


# === Управление пользователями ===

def get_user_status(username: str) -> Optional[str]:
    """Возвращает статус пользователя"""
    if username not in USERS:
        return None
    return USERS[username].get("status", "active")


def set_user_status(username: str, status: str) -> bool:
    """Устанавливает статус пользователя (active/blocked)"""
    if username not in USERS:
        return False
    USERS[username]["status"] = status
    save_users_to_file(USERS)  # Сохраняем изменения
    return True


def add_user(username: str, password: str, role: str, name: str = None) -> bool:
    """Добавляет нового пользователя в систему"""
    if username in USERS:
        return False

    if name is None:
        name = username

    USERS[username] = {
        "password_hash": hash_password(password),
        "role": role,
        "name": name,
        "status": "active"
    }
    save_users_to_file(USERS)  # Сохраняем изменения
    return True


def update_user_role(username: str, new_role: str) -> bool:
    """Обновляет роль пользователя"""
    if username not in USERS:
        return False
    USERS[username]["role"] = new_role
    save_users_to_file(USERS)  # Сохраняем изменения
    return True


def update_user_name(username: str, new_name: str) -> bool:
    """Обновляет имя пользователя"""
    if username not in USERS:
        return False
    USERS[username]["name"] = new_name
    save_users_to_file(USERS)  # Сохраняем изменения
    return True


def delete_user(username: str) -> bool:
    """Удаляет пользователя из системы"""
    if username not in USERS:
        return False
    del USERS[username]
    save_users_to_file(USERS)  # Сохраняем изменения
    return True


def sync_users_from_admin(users_list: list):
    """Синхронизирует пользователей из админ-панели"""
    global USERS
    new_users = {}
    for u in users_list:
        new_users[u["username"]] = {
            "password_hash": u["password_hash"],
            "role": u["role"],
            "name": u.get("name", u["username"]),
            "status": u.get("status", "active")
        }
    USERS = new_users
    save_users_to_file(USERS)


def add_event(user_id: str, event_type: str, action: str, source: str = None):
    """Добавляет событие в журнал"""
    import json
    from pathlib import Path

    EVENTS_DB = Path(__file__).parent.parent / "data" / "events.json"

    # Загружаем существующие события
    if EVENTS_DB.exists():
        with open(EVENTS_DB, 'r', encoding='utf-8') as f:
            events = json.load(f)
    else:
        events = []

    # Добавляем новое событие
    events.append({
        "id": len(events) + 1,
        "user_id": user_id,
        "event_type": event_type,
        "action": action,
        "source": source,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    # Ограничиваем количество (храним последние 1000)
    if len(events) > 1000:
        events = events[-1000:]

    # Сохраняем
    EVENTS_DB.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_DB, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)