# auth.py
import streamlit as st
import hashlib
import jwt
from datetime import datetime, timedelta
import json
import os
from functools import wraps

# Секретный ключ для JWT (в продакшене должен быть в переменных окружения)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Моковые данные пользователей (в реальном приложении - база данных)
USERS_DB = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@company.com",
        "hashed_password": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "disabled": False
    },
    "user": {
        "username": "user",
        "full_name": "Regular User",
        "email": "user@company.com",
        "hashed_password": hashlib.sha256("user123".encode()).hexdigest(),
        "role": "user",
        "disabled": False
    },
    "viewer": {
        "username": "viewer",
        "full_name": "Viewer Only",
        "email": "viewer@company.com",
        "hashed_password": hashlib.sha256("viewer123".encode()).hexdigest(),
        "role": "viewer",
        "disabled": False
    }
}


def verify_password(plain_password, hashed_password):
    """Проверка пароля"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def authenticate_user(username: str, password: str):
    """Аутентификация пользователя"""
    user = USERS_DB.get(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Создание JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    """Проверка JWT токена"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.PyJWTError:
        return None


def login_page():
    """Страница входа"""
    st.title("🔐 Авторизация")

    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### Вход в систему мониторинга")

            with st.form("login_form"):
                username = st.text_input("Логин", placeholder="Введите имя пользователя")
                password = st.text_input("Пароль", type="password", placeholder="Введите пароль")
                remember_me = st.checkbox("Запомнить меня", value=True)

                submitted = st.form_submit_button("Войти", type="primary", use_container_width=True)

                if submitted:
                    if not username or not password:
                        st.error("Пожалуйста, заполните все поля")
                        return

                    user = authenticate_user(username, password)
                    if not user:
                        st.error("Неверное имя пользователя или пароль")
                    elif user.get("disabled"):
                        st.error("Аккаунт отключен")
                    else:
                        # Создаем токен
                        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES if remember_me else 15)
                        access_token = create_access_token(
                            data={"sub": user["username"], "role": user["role"]},
                            expires_delta=access_token_expires
                        )

                        # Сохраняем в сессии
                        st.session_state["access_token"] = access_token
                        st.session_state["user"] = user
                        st.session_state["authenticated"] = True
                        st.session_state["role"] = user["role"]

                        st.success(f"Добро пожаловать, {user['full_name']}!")
                        st.rerun()

            # Демо аккаунты (только для разработки)
            with st.expander("Демо аккаунты"):
                st.markdown("""
                **Администратор:**
                - Логин: `admin`
                - Пароль: `admin123`

                **Пользователь:**
                - Логин: `user`
                - Пароль: `user123`

                **Наблюдатель:**
                - Логин: `viewer`
                - Пароль: `viewer123`
                """)


def logout():
    """Выход из системы"""
    for key in ["access_token", "user", "authenticated", "role"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def check_auth():
    """Проверка аутентификации"""
    if not st.session_state.get("authenticated", False):
        return False

    # Проверяем токен
    token = st.session_state.get("access_token")
    if not token or not verify_token(token):
        logout()
        return False

    return True


def require_auth(func):
    """Декоратор для проверки аутентификации"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not check_auth():
            login_page()
            st.stop()
        return func(*args, **kwargs)

    return wrapper


def require_role(required_role: str):
    """Декоратор для проверки роли"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not check_auth():
                login_page()
                st.stop()

            user_role = st.session_state.get("role", "")
            if user_role != required_role and user_role != "admin":
                st.error("У вас недостаточно прав для доступа к этой странице")
                st.info(f"Требуемая роль: {required_role}, ваша роль: {user_role}")
                st.stop()

            return func(*args, **kwargs)

        return wrapper

    return decorator


def has_role(required_role: str):
    """Проверка, есть ли у пользователя нужная роль"""
    if not check_auth():
        return False

    user_role = st.session_state.get("role", "")
    return user_role == required_role or user_role == "admin"


def get_current_user():
    """Получение информации о текущем пользователе"""
    if check_auth():
        return st.session_state.get("user", {})
    return None