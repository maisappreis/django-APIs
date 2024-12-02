# Django APIs for Web Applications

## Gym Company
A web application to manage the company's customers, income and expenses. <br>
Front-end code on: https://github.com/maisappreis/upfit-project

You can try it out in this production test version: https://maisappreis.github.io/upfit-gym/

## Dental Clinic
A web application to manage the patient schedule, income and expenses of the dental clinic, as well as to perform the monthly cash closing. <br>
Front-end code on: https://github.com/maisappreis/dental-clinic-web-system

You can try it out in this production test version: https://maisappreis.github.io/dental-clinic/

## Technologies:
- Django
- Python

## 🌱 Backend Development

### 🛠️ Installation

Create a virtual environment
Activate the virtual environment:
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1 (On Windows)
or
source venv/bin/activate (On macOS/Linux)
```

```
pip install -r requirements.txt
```

### 🛠️ Running
Active your virtual enviroment

On Windows:
```
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:
```
source venv/bin/activate (On macOS/Linux)
```

Run server:
```
python manage.py runserver
```

To run migrations:
```
python manage.py makemigrations
python manage.py migrate
```

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
