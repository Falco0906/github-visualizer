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

Open http://localhost:8000 and click "Sign in with GitHub".

### Environment Variables (.env)
- `DEBUG` True/False
- `SECRET_KEY` random string
- `ALLOWED_HOSTS` comma-separated
- `GITHUB_KEY` your OAuth client ID
- `GITHUB_SECRET` your OAuth client secret
- `GITHUB_SCOPE` read:user,user:email,repo
- `SITE_URL` public site URL (http://localhost:8000 during dev)

### GitHub OAuth App Setup
1. Create a new OAuth App at https://github.com/settings/developers
2. Homepage URL: your SITE_URL
3. Authorization callback URL: `SITE_URL/auth/complete/github/`
4. Put client ID/secret into `.env`

### Apps
- `accounts`: dashboard, profile editing, preferences
- `portfolio`: models for snapshots, repos, activities, highlights, public pages
- `githubapi`: API client and ingestion service

### Production Notes
- Use `whitenoise` for static files
- Set `DEBUG=False`, a strong `SECRET_KEY`, and `ALLOWED_HOSTS`
- Prefer Postgres (install `psycopg2-binary` and configure `DATABASES`)
