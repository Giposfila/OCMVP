from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import bcrypt
from app.database import get_db
from app.models import UserProfile
from app.services.user_service import (
    create_user,
    get_user_by_email,
    verify_password as check_pass,
)

router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    from app.main import templates

    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register")
async def register_page(request: Request):
    from app.main import templates

    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, email)
    if user and check_pass(password, user.password_hash):
        request.session["user_id"] = str(user.id)
        request.session["user_email"] = user.email
        request.session["user_role"] = user.role
        return RedirectResponse("/", status_code=302)

    from app.main import templates

    return templates.TemplateResponse(
        "auth/login.html", {"request": request, "error": "Неверный email или пароль"}
    )


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, email)
    if user:
        from app.main import templates

        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Пользователь с таким email уже существует"},
        )

    new_user = create_user(db, email=email, password=password, role="StandardUser")
    request.session["user_id"] = str(new_user.id)
    request.session["user_email"] = new_user.email
    request.session["user_role"] = new_user.role
    return RedirectResponse("/", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)
