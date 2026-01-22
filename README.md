# Pandora Box

A comprehensive Django-based document management and administrative system for government operations.

## Features

- User authentication and role-based access control
- Document management system
- Administrative dashboard
- Notification system
- PostgreSQL database backend

## Technology Stack

- **Backend**: Django 4.2
- **Database**: PostgreSQL
- **Server**: Gunicorn
- **Static Files**: WhiteNoise
- **Python**: 3.13.7

## Deploy to Render

Click the button below to deploy this application to Render:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/HILTONJACKSO/pandora-site)

The deployment will automatically:
- Create a PostgreSQL database
- Set up the web service
- Install dependencies
- Collect static files
- Run database migrations
- Generate a secure SECRET_KEY

After deployment, you can create a superuser by running:
```bash
python manage.py createsuperuser
```
in the Render Shell (accessible from your service dashboard).

## Local Development

### Prerequisites

- Python 3.13.7
- PostgreSQL

### Setup

1. Clone the repository:
```bash
git clone https://github.com/HILTONJACKSO/pandora-site.git
cd pandora-site
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=pandora_box
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

## License

Proprietary - All rights reserved

## Contact

For questions or support, please contact the development team.