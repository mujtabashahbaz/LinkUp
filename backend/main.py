from datetime import datetime, timedelta, timezone
from typing import Optional
import os

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, or_, and_
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./linkup.db")
# Some providers may still expose the old postgres:// prefix.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 24 * 7

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    headline = Column(String(180), default="")
    location = Column(String(120), default="")
    about = Column(Text, default="")
    avatar = Column(String(500), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "post_id"),)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Connection(Base):
    __tablename__ = "connections"
    id = Column(Integer, primary_key=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("requester_id", "receiver_id"),)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LinkUp API")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
allowed_origins = [FRONTEND_URL, "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class ProfileIn(BaseModel):
    name: str
    headline: str = ""
    location: str = ""
    about: str = ""
    avatar: str = ""

class PostIn(BaseModel):
    body: str

class CommentIn(BaseModel):
    body: str

def public_user(u: User):
    return {
        "id": u.id, "name": u.name, "email": u.email, "headline": u.headline or "",
        "location": u.location or "", "about": u.about or "", "avatar": u.avatar or "",
    }

def create_token(user_id: int):
    exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

def current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid authentication")
    user = session.get(User, uid)
    if not user:
        raise HTTPException(401, "User not found")
    return user

@app.get("/")
def root():
    return {"name": "LinkUp API", "status": "ok"}

@app.post("/auth/register")
def register(data: RegisterIn, session: Session = Depends(db)):
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if session.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    user = User(
        name=data.name.strip(),
        email=data.email.lower(),
        password_hash=pwd_context.hash(data.password),
        headline="Open to new opportunities",
    )
    session.add(user); session.commit(); session.refresh(user)
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": public_user(user)}

@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(db)):
    user = session.query(User).filter(User.email == form.username.lower()).first()
    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": public_user(user)}

@app.get("/me")
def me(user: User = Depends(current_user)):
    return public_user(user)

@app.put("/me")
def update_me(data: ProfileIn, user: User = Depends(current_user), session: Session = Depends(db)):
    for key, value in data.model_dump().items():
        setattr(user, key, value.strip() if isinstance(value, str) else value)
    session.commit(); session.refresh(user)
    return public_user(user)

@app.get("/users")
def users(user: User = Depends(current_user), session: Session = Depends(db)):
    rows = session.query(User).filter(User.id != user.id).order_by(User.name).all()
    result = []
    for u in rows:
        c = session.query(Connection).filter(
            or_(
                and_(Connection.requester_id == user.id, Connection.receiver_id == u.id),
                and_(Connection.requester_id == u.id, Connection.receiver_id == user.id)
            )
        ).first()
        item = public_user(u)
        item["connection"] = None if not c else {
            "id": c.id, "status": c.status,
            "incoming": c.receiver_id == user.id and c.status == "pending"
        }
        result.append(item)
    return result

@app.get("/users/{user_id}")
def user_profile(user_id: int, _: User = Depends(current_user), session: Session = Depends(db)):
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    return public_user(u)

@app.post("/connections/{user_id}")
def connect(user_id: int, user: User = Depends(current_user), session: Session = Depends(db)):
    if user_id == user.id:
        raise HTTPException(400, "Cannot connect with yourself")
    if not session.get(User, user_id):
        raise HTTPException(404, "User not found")
    existing = session.query(Connection).filter(
        or_(
            and_(Connection.requester_id == user.id, Connection.receiver_id == user_id),
            and_(Connection.requester_id == user_id, Connection.receiver_id == user.id)
        )
    ).first()
    if existing:
        raise HTTPException(409, "Connection already exists")
    c = Connection(requester_id=user.id, receiver_id=user_id)
    session.add(c); session.commit()
    return {"ok": True}

@app.post("/connections/{connection_id}/accept")
def accept(connection_id: int, user: User = Depends(current_user), session: Session = Depends(db)):
    c = session.get(Connection, connection_id)
    if not c or c.receiver_id != user.id:
        raise HTTPException(404, "Request not found")
    c.status = "accepted"; session.commit()
    return {"ok": True}

@app.get("/feed")
def feed(user: User = Depends(current_user), session: Session = Depends(db)):
    posts = session.query(Post).order_by(Post.created_at.desc()).limit(100).all()
    output = []
    for p in posts:
        author = session.get(User, p.author_id)
        comments = session.query(Comment).filter(Comment.post_id == p.id).order_by(Comment.created_at).all()
        output.append({
            "id": p.id, "body": p.body, "created_at": p.created_at,
            "author": public_user(author),
            "likes": session.query(Like).filter(Like.post_id == p.id).count(),
            "liked": session.query(Like).filter(Like.post_id == p.id, Like.user_id == user.id).first() is not None,
            "comments": [
                {
                    "id": c.id, "body": c.body, "created_at": c.created_at,
                    "author": public_user(session.get(User, c.user_id))
                } for c in comments
            ]
        })
    return output

@app.post("/posts")
def create_post(data: PostIn, user: User = Depends(current_user), session: Session = Depends(db)):
    body = data.body.strip()
    if not body:
        raise HTTPException(400, "Post cannot be empty")
    post = Post(author_id=user.id, body=body)
    session.add(post); session.commit(); session.refresh(post)
    return {"id": post.id}

@app.post("/posts/{post_id}/like")
def toggle_like(post_id: int, user: User = Depends(current_user), session: Session = Depends(db)):
    if not session.get(Post, post_id):
        raise HTTPException(404, "Post not found")
    like = session.query(Like).filter(Like.post_id == post_id, Like.user_id == user.id).first()
    if like:
        session.delete(like); liked = False
    else:
        session.add(Like(post_id=post_id, user_id=user.id)); liked = True
    session.commit()
    return {"liked": liked}

@app.post("/posts/{post_id}/comments")
def add_comment(post_id: int, data: CommentIn, user: User = Depends(current_user), session: Session = Depends(db)):
    if not session.get(Post, post_id):
        raise HTTPException(404, "Post not found")
    body = data.body.strip()
    if not body:
        raise HTTPException(400, "Comment cannot be empty")
    c = Comment(post_id=post_id, user_id=user.id, body=body)
    session.add(c); session.commit()
    return {"ok": True}
