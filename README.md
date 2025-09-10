## GitHub Portfolio Visualizer

A Django 4 project that connects to GitHub via OAuth and renders a beautiful, interactive portfolio from your repositories and activity.

### Features
- GitHub OAuth (Login with GitHub)
- Cache of profile, repos, languages, and commit activity
- Dashboard with Chart.js and stylish repo cards
- Drag-and-drop featured highlights ordering
- Public portfolio pages

### Requirements
- Python 3.10+
- GitHub OAuth App (Client ID/Secret)

### Quickstart
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit values inside
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
