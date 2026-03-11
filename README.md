# Django REST API

- Django REST API for serving front-end applications.

🌐 **Live demo: Front-end 1**  
https://maisappreis.github.io/dental-clinic/

🌐 **Live demo: Front-end 2**  
https://maisappreis.github.io/upfit-gym/


---

## 🧠 Overview

This project was built as part of a fullstack architecture, where the frontend communicates with a REST API developed in Django.  
It focuses on **state management, authentication flows and modular structure**, following modern Django best practices.

---

## 🛠️ Tech Stack

- Django
- Python

---

## 🧩 Architecture

- **Authentication** is implemented using JWT tokens, managed on the frontend and validated by the backend.
- The **backend API** is responsible for business logic, data persistence, and permissions, exposing secure REST endpoints.
- The project is structured to support scalability, maintainability, and clear separation of concerns.

---

## 🔐 Authentication Flow

Authentication is implemented using **JWT (JSON Web Tokens)**, enabling stateless and secure communication between the frontend and backend.

1. The user submits credentials through the frontend login form.
2. The frontend sends the credentials to the Django REST API.
3. Upon successful authentication, the backend issues an **access token** (and refresh token).
4. The frontend stores the token and attaches it to subsequent API requests via the `Authorization` header.
5. Protected routes and resources are validated on the backend using JWT authentication.

---

## 🌱 Project Status

🚧 This project is under active development.  
New features, refactors, and improvements are added incrementally.

---

## 📦 Getting Started

### Installation

Create a virtual environment
Activate the virtual environment:

On Windows
```sh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
or

On macOS/Linux
```sh
source venv/bin/activate
```

```sh
pip install -r requirements.txt
```

### Development

Active your virtual enviroment

On Windows:
```sh
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:
```sh
source venv/bin/activate (On macOS/Linux)
```

Run server:
```sh
python manage.py runserver
```

To run migrations:
```sh
python manage.py makemigrations
python manage.py migrate
```

---

## 🧪 Testing

Run **Tests**
```sh
python manage.py test dental_clinic.tests
python manage.py test upgit_gym.tests
```

---

### Database
Acessa: mysql -u [username] -p
Conecta: mysql -h [endpoint] -u [username] -p
Cria db: CREATE DATABASE `mysql-db`;
Exibe: SHOW DATABASES;

### Commands
To reset database migrations:
python manage.py migrate [app] zero

To update requirements.txt
pip freeze > requirements.txt

---

## 👩‍💻 Author

Maisa Pierini Preis

Frontend‑focused Full Stack Developer

- GitHub: https://github.com/maisappreis
- LinkedIn: https://www.linkedin.com/in/maisa-pp-2303/
- Portfolio: https://maisappreis.github.io/

---

## 📄 License

This project is licensed under the MIT License.

