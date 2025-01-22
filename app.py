from flask import Flask, render_template, request, abort
from flask_apscheduler import APScheduler
from app.services.court_listener import CourtListenerService
from config import Config
import functools

app = Flask(__name__, 
           template_folder='app/templates',  # Set the template folder
           static_folder='app/static')       # Set the static folder
app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

with app.app_context():
    court_listener_service = CourtListenerService()

def validate_webhook_request(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Validate IP
        if request.remote_addr not in app.config['ALLOWED_IPS']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    cases = court_listener_service.get_cases()
    return render_template('index.html', cases=cases)  # Just use the template name

@app.route('/webhook', methods=['POST'])
@validate_webhook_request
def webhook():
    event_data = request.get_json()
    
    # Check idempotency key to avoid duplicate processing
    idempotency_key = request.headers.get('Idempotency-Key')
    if not idempotency_key:
        abort(400)
    
    court_listener_service.handle_webhook_event(event_data)
    return '', 200

# Run update at 6 AM and 6 PM every day
@scheduler.task('cron', id='update_cases', hour='12', minute='42', second='10')
def scheduled_update():
    with app.app_context():
        print("Running scheduled update...")
        court_listener_service.refresh_cases()

if __name__ == '__main__':
    app.run(debug=True) 