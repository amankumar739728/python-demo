from fastapi import FastAPI, Form, Request, Depends, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pymongo
import smtplib
from email.mime.text import MIMEText
import secrets
import os
from dotenv import load_dotenv
import uvicorn


load_dotenv()


sender_password = os.getenv("sender_password")

smtp_server = "smtp-relay.brevo.com"
smtp_port = 587
sender_email = "amanpain000@gmail.com"





app = FastAPI()

templates = Jinja2Templates(directory="templates")


client = pymongo.MongoClient("mongodb+srv://aman123:Legion%40123@cluster0.yrmlxqc.mongodb.net/Aman?retryWrites=true&w=majority")  # Your MongoDB connection string
db = client["Aman"]
collection = db["Login"]

def generate_reset_token():
    token = secrets.token_urlsafe(16)
    return token

def send_password_reset_email(email, token):
    subject = "Password Reset Request"
    message = f"Click the following link to reset your password: http://localhost:8000/reset_password/{token}"

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)

@app.get("/")
async def read_root(request: Request, username: str = Cookie(default=None)):
    if username:
        return templates.TemplateResponse("index.html", {"request": request, "username": username})
    else:
        return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: str = "", message: str = "",notification: str = ""):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error, "message": message, "notification": notification}
    )

@app.post("/login")
async def login_post(username: str = Form(...), password: str = Form(...)):
    user = collection.find_one({"username": username})
    
    if user and user["password"] == password:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="username", value=username)
        return response
    else:
        return RedirectResponse(url="/login?error=Incorrect%20credentials", status_code=303)

@app.get("/logout")
async def logout(request: Request, username: str = Cookie(default=None)):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("username")
    return response

@app.get("/forgot_password", response_class=HTMLResponse)
async def forgot_password_form(request: Request, error: str = ""):
    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request, "error": error}
    )

@app.post("/forgot_password")
async def forgot_password_post(email: str = Form(...)):
    user = collection.find_one({"email": email})
    
    if user:
        token = generate_reset_token()
        user["reset_token"] = token
        collection.update_one({"email": email}, {"$set": {"reset_token": token}})
        
        send_password_reset_email(email, token)
        return RedirectResponse(url="/forgot_password_success", status_code=303)
    else:
        return RedirectResponse(url="/forgot_password?error=Invalid%20email%20address", status_code=303)

@app.get("/forgot_password_success", response_class=HTMLResponse)
async def forgot_password_success(request: Request):
    return templates.TemplateResponse(
        "forgot_password_success.html",
        {"request": request}
    )

@app.get("/reset_password/{token}", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    user = collection.find_one({"reset_token": token})
    
    if user:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "token": token}
        )
    else:
        return templates.TemplateResponse(
            "reset_password_error.html",
            {"request": request}
        )

@app.post("/reset_password/{token}")
async def reset_password_post(token: str,request: Request,password: str = Form(...)):
    user = collection.find_one({"reset_token": token})
    
    if user:
        collection.update_one({"reset_token": token}, {"$set": {"password": password}})
        return RedirectResponse(url="/reset_password_success", status_code=303)
    else:
        return templates.TemplateResponse(
            "reset_password_error.html",
            {"request": request}
        )

@app.get("/reset_password_success", response_class=HTMLResponse)
async def reset_password_success(request: Request):
    return templates.TemplateResponse(
        "reset_password_success.html",
        {"request": request}
    )
    
@app.get("/registration-form.html", response_class=HTMLResponse)
async def registration_form(request: Request, notification: str = ""):
    return templates.TemplateResponse(
        "registration-form.html",
        {"request": request, "notification": notification}
    )

@app.post("/reg")
async def registration_post(
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    try:
        if username and email and password:
            user = {"email": email, "username": username, "password": password}
            result = collection.insert_one(user)

            if result.inserted_id:
                notification = "User created successfully. Now you can login."
                return RedirectResponse(url=f"/login?notification={notification}", status_code=303)
            else:
                raise HTTPException(status_code=500, detail="Failed to create user")
        else:
            raise HTTPException(status_code=400, detail="Missing required parameters")
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while saving user information")
    
@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, username: str = Cookie(default=None)):
    return templates.TemplateResponse("home.html", {"request": request, "username": username})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, username: str = Cookie(default=None)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": username})

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, username: str = Cookie(default=None)):
    user = collection.find_one({"username": username})
    
    if user:
        user_data = {"email": user["email"], "username": user["username"], "password": user["password"]}
        return templates.TemplateResponse("profile.html", {"request": request, "username": username, "user": user_data})
    else:
        # Handle the case when the user is not found
        return templates.TemplateResponse("profile.html", {"request": request, "username": username, "user": None})



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
