# Django REST API

- Django REST API for serving front-end applications.

🌐 **Live demo: Front-end 1**  
https://maisappreis.github.io/dental-clinic/

🌐 **Live demo: Front-end 2**  
https://maisappreis.github.io/upfit-gym/

**Docs**
https://django-apis-two.vercel.app/api/swagger/

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

To test the interaction with Stripe, run the following commands in the terminal in administrator mode:
```sh
stripe login
stripe listen --forward-to localhost:8000/api/accounts/stripe/webhook/
```

I copied the generated webhook to the .env file.
Test card number: 42424242424242
Other data can be any number.

---

## 🧪 Testing

Run **Tests**
```sh
python manage.py test dental_clinic.tests
python manage.py test upgit_gym.tests

coverage run manage.py test ai_content_agent

coverage run manage.py test
coverage report
coverage html
```

Open to see coverage:
htmlcov/index.html

---

### Database
Acessa: mysql -u [username] -p
Conecta: mysql -h [endpoint] -u [username] -p
Cria db: CREATE DATABASE `mysql-db`;
Exibe: SHOW DATABASES;

### Commands
To reset database migrations:
python manage.py migrate [app] zero

To update requirements.txt:
```sh
pip freeze > requirements.txt
```

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

## Deploy e migrations

The environment is defined by `ENVIRONMENT` and, when absent, by `VERCEL_ENV`.
In production, use:

```env
ENVIRONMENT=production
```

Before publishing a version, apply the migrations to the production database only once, using the Neon variables:

```powershell
python manage.py migrate --noinput
python manage.py check --deploy
```

These commands should run in a release job or pipeline with serialized concurrency.

## Content Agent worker on Cloud Run

The public API can stay on Vercel while QStash delivers long-running content
generation jobs to Cloud Run.

Set these variables on Vercel:

```env
CONTENT_AGENT_QUEUE_BACKEND=qstash
CONTENT_AGENT_PUBLIC_URL=https://your-vercel-app.vercel.app
CONTENT_AGENT_WORKER_URL=https://your-cloud-run-service.run.app
QSTASH_TOKEN=...
CONTENT_AGENT_JOB_TOKEN=...
```

Set the same production secrets on Cloud Run that the job needs to run:

```env
ENVIRONMENT=production
DJANGO_SECRET_KEY=...
OPENAI_API_KEY=...
QSTASH_TOKEN=...
CONTENT_AGENT_JOB_TOKEN=...
CONTENT_AGENT_STORAGE_BACKEND=firebase
FIREBASE_STORAGE_BUCKET=...
FIREBASE_CREDENTIALS_JSON=...
NEON_DB_NAME=...
NEON_DB_USER=...
NEON_DB_PASSWORD=...
NEON_DB_HOST=...
NEON_DB_PORT=5432
```

Cloud Run exposes the same Django routes as Vercel, but QStash should call only
the authenticated worker endpoints:

```text
/api/content-agent/jobs/post-generation/
/api/content-agent/jobs/post-images/
```
