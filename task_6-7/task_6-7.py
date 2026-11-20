
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
import jwt


app = FastAPI(title="User Management API")
SECRET_KEY = "GFJHNVIURUSHLJHWBBNKFG"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Модель пользователя
class User(BaseModel):
    id: int
    name: str
    email: EmailStr


# Модель для создания пользователя
class UserCreate(BaseModel):
    name: str
    email: EmailStr


# Хранилище в памяти
users = []
next_id = 1


# Создание пользователя
@app.post("/users/", response_model=User)
def create_user(user: UserCreate):
    global next_id

    new_user = User(
        id=next_id,
        name=user.name,
        email=user.email
    )

    users.append(new_user)
    next_id += 1

    return new_user


# Получение всех пользователей
@app.get("/users/", response_model=list[User])
def get_users():
    return users


# Получение пользователя по ID
@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    for user in users:
        if user.id == user_id:
            return user

    raise HTTPException(status_code=404, detail="User not found")


# Обновление пользователя
@app.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, updated_user: UserCreate):
    for index, user in enumerate(users):
        if user.id == user_id:
            new_user = User(
                id=user_id,
                name=updated_user.name,
                email=updated_user.email
            )

            users[index] = new_user
            return new_user

    raise HTTPException(status_code=404, detail="User not found")


# Удаление пользователя
@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    for user in users:
        if user.id == user_id:
            users.remove(user)
            return {"message": "User deleted"}

    raise HTTPException(status_code=404, detail="User not found")



password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Отдельное хранилище для учётных записей
auth_users = {}


def hash_password(password: str):
    return password_hash.hash(password)


def verify_password(password: str, hashed: str):
    return password_hash.verify(password, hashed)


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# Регистрация
@app.post("/register")
def register(username: str, password: str):
    if username in auth_users:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    auth_users[username] = {
        "username": username,
        "password": hash_password(password)
    }

    return {"message": "User registered"}


# Авторизация
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth_users.get(form_data.username)

    if not user or not verify_password(
        form_data.password,
        user["password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_access_token({
        "sub": form_data.username
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# Проверка JWT
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if username is None or username not in auth_users:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return username

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


# Защищённый маршрут
@app.get("/profile")
def profile(username: str = Depends(get_current_user)):
    return {
        "message": "Authenticated successfully",
        "username": username
    }
