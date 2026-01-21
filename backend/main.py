# backend/main.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# === Настройка базы данных (SQLite) ===
BASE_DIR = Path(__file__).parent
DATABASE_URL = f"sqlite:///{BASE_DIR}/ads.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# === Модель объявления ===
class Ad(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    price = Column(String)
    description = Column(Text, nullable=True)
    photo_path = Column(String)

# Создаём таблицу
Base.metadata.create_all(bind=engine)

# === FastAPI приложение ===
app = FastAPI(title="Недвижимость API")

# Разрешаем CORS (для Telegram Web App)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Отдаём загруженные фото как статику
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

@app.post("/ads/")
async def create_ad(
    title: str = Form(...),
    price: str = Form(...),
    description: str = Form(None),
    photo: UploadFile = File(...)
):
    # Проверка: изображение?
    if not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")

    # Генерируем уникальное имя
    ext = photo.filename.split(".")[-1].lower() if "." in photo.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = UPLOAD_DIR / filename

    # Сохраняем файл
    with open(filepath, "wb") as f:
        f.write(await photo.read())

    # Сохраняем в БД
    db = SessionLocal()
    db_ad = Ad(
        title=title,
        price=price,
        description=description,
        photo_path=f"/uploads/{filename}"
    )
    db.add(db_ad)
    db.commit()
    db.refresh(db_ad)
    db.close()

    return {
        "id": db_ad.id,
        "title": db_ad.title,
        "price": db_ad.price,
        "photo_url": f"/uploads/{filename}"
    }

@app.get("/ads/")
def get_ads():
    db = SessionLocal()
    ads = db.query(Ad).all()
    db.close()
    return [
        {
            "id": ad.id,
            "title": ad.title,
            "price": ad.price,
            "description": ad.description,
            "photo_url": ad.photo_path
        }
        for ad in ads
    ]