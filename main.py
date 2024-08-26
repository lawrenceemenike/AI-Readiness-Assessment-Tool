from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime, timezone
import os
from pdf_generator import generate_pdf_report
import io


app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = '001'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

if os.path.exists('users.db'):
    os.remove('users.db')

with app.app_context():
    db.create_all()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
    
class AssessmentQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    options = db.Column(db.JSON, nullable=False)
    scores = db.Column(db.JSON, nullable=False)
    max_score = db.Column(db.Float, nullable=False)
    
class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completion_date = db.Column(db.DateTime)
    current_question = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='In Progress')
    strategy_score = db.Column(db.Float, default=0)
    governance_score = db.Column(db.Float, default=0)
    data_infrastructure_score = db.Column(db.Float, default=0)
    organization_score = db.Column(db.Float, default=0)
    total_score = db.Column(db.Float, default=0)
    readiness_level = db.Column(db.String(50))
    
class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('assessment_question.id'), nullable=False)
    answer = db.Column(db.String(500))
    score = db.Column(db.Float)

    def __init__(self, assessment_id, question_id, answer):
        self.assessment_id = assessment_id
        self.question_id = question_id
        self.answer = answer
        question = AssessmentQuestion.query.get(question_id)
        if question and question.options:
            option_index = question.options.index(answer)
            self.score = question.scores[option_index]
    
def populate_questions():
    questions = [
        # Strategy (19 points max)
        AssessmentQuestion(
            category='Strategy',
            subcategory='AI Strategy',
            text='Does your organization have a well-defined AI strategy?',
            options=["Yes, we have a detailed AI strategy.", 
                     "No, we are currently developing an AI strategy.",
                     "No, we have not started developing an AI strategy.",
                     "Unsure"],
            scores=[5, 3, 1, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Strategy',
            subcategory='Leadership and Ownership',
            text='Is there clear leadership or a dedicated team responsible for the AI strategy?',
            options=["Yes, there is a dedicated AI team or leader.",
                     "No, it is managed in an organic and decentralized manner.",
                     "Unsure"],
            scores=[5, 2, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Strategy',
            subcategory='Impact Measurement',
            text='Do you have a process to measure the impact of AI deployment?',
            options=["Yes, we have a process and clearly defined metrics.",
                     "Yes, we have a process but are still working on actual metrics.",
                     "No, we don’t have a process or metrics but are likely to develop this within 12 months.",
                     "No, we don’t have a process or metrics and are unlikely to develop this within 12 months.",
                     "Unsure"],
            scores=[5, 4, 2, 1, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Strategy',
            subcategory='Financial Strategy',
            text='Has your organization established a financial strategy for sustainable AI funding?',
            options=["Yes, both short-term and long-term financial strategies are in place.",
                     "Yes, only a short-term financial strategy is in place.",
                     "No, but we are currently developing a financial strategy.",
                     "No, we have no plans to develop a financial strategy.",
                     "Unsure"],
            scores=[5, 3, 2, 1, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Strategy',
            subcategory='Budget Allocation',
            text='How is your organization prioritizing budget allocation for AI deployment compared to other technological initiatives?',
            options=["AI deployment is the highest priority with additional budget allocated.",
                     "AI deployment is given equal priority with some additional funding.",
                     "AI deployment is important but requires cutting spending in other areas.",
                     "AI deployment depends on other technical initiatives being in place first.",
                     "Unsure"],
            scores=[5, 4, 3, 2, 0],
            max_score=5
        ),

        # Governance (17 points max)
        AssessmentQuestion(
            category='Governance',
            subcategory='AI Governance Framework',
            text='Does your organization have a clearly defined AI governance framework?',
            options=["Yes", "No", "Developing"],
            scores=[5, 0, 3],
            max_score=5
        ),
        AssessmentQuestion(
            category='Governance',
            subcategory='Ethical AI Policies',
            text='Are there established policies and procedures for ethical AI development and use?',
            options=["Yes", "No", "Developing"],
            scores=[5, 0, 3],
            max_score=5
        ),
        AssessmentQuestion(
            category='Governance',
            subcategory='C-suite Engagement',
            text='How engaged is your C-suite with AI implementation issues?',
            options=["Excellent", "Very Good", "Good", "Fair", "Poor"],
            scores=[5, 4, 3, 2, 1],
            max_score=5
        ),
        AssessmentQuestion(
            category='Governance',
            subcategory='Resource Allocation',
            text='How would you rate the allocation of resources (financial, human, technological) to support AI projects?',
            options=["Excellent", "Very Good", "Solid", "Fair", "Poor"],
            scores=[5, 4, 3, 2, 1],
            max_score=5
        ),
        AssessmentQuestion(
            category='Governance',
            subcategory='Performance Metrics',
            text='Do you have established metrics and KPIs to measure AI initiatives\' performance and impact?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Governance',
            subcategory='Change Management',
            text='Have you developed a change management plan to address organizational impacts from AI implementations?',
            options=["Yes", "No", "Developing"],
            scores=[5, 0, 3],
            max_score=5
        ),
        AssessmentQuestion(
            category='Governance',
            subcategory='Transparency and Accountability',
            text='Are there mechanisms to ensure transparency and accountability in AI decision-making processes?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Governance',
            subcategory='Risk Management',
            text='How does your organization manage risks associated with AI implementation, such as bias, privacy concerns, and regulatory compliance?',
            options=["Excellent", "Solid", "Good", "Fair", "Poor"],
            scores=[5, 4, 3, 2, 1],
            max_score=5
        ),

        # Data & Infrastructure (20 points max)
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Data Availability',
            text='To what extent is your organization’s data structured and available for AI analysis?',
            options=["Data is not available.",
                     "Data is available but with privacy/compliance concerns.",
                     "Data is mostly prepared with minor access limitations.",
                     "Data is fully prepared and accessible.",
                     "Other"],
            scores=[0, 2, 3, 5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Data Collection',
            text='Do you collect data on your services?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Data Accuracy',
            text='How would you rate the accuracy and reliability of your data?',
            options=["Excellent", "Good", "Moderate", "Fair", "Poor"],
            scores=[5, 4, 3, 2, 1],
            max_score=5
        ),
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Data Up-to-Date',
            text='Do you have a mechanism to ensure your data is up-to-date?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Data Access',
            text='How easy is it for authorized personnel to access the data needed for AI analysis?',
            options=["Easy", "Somewhat difficult", "Difficult"],
            scores=[5, 3, 1],
            max_score=5
        ),
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Data Integration',
            text='Do you have systems to integrate data from different sources (e.g., CRM, ERP)?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Infrastructure Performance',
            text='How would you rate the performance of your data storage and computing infrastructure?',
            options=["Excellent", "Very Good", "Solid", "Fair", "Poor"],
            scores=[5, 4, 3, 2, 1],
            max_score=5
        ),
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Scalability',
            text='How would you rate your infrastructure\'s capacity to scale to accommodate changing AI demands?',
            options=["Excellent", "Very Good", "Solid", "Fair", "Poor"],
            scores=[5, 4, 3, 2, 1],
            max_score=5
        ),
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Cloud Solutions',
            text='Have you considered cloud-based solutions for scalability and flexibility?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Data & Infrastructure',
            subcategory='Security Policies',
            text='Are there policies to ensure data security and privacy?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),

        # Organization (Talent & Culture) (17 points max)
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Talent Availability',
            text='Does your organization have a dedicated team with expertise in AI technologies?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Team Capacity',
            text='How would you rate your team’s capacity to manage and analyze data effectively?',
            options=["Excellent", "Very Good", "Solid", "Fair", "Poor"],
            scores=[5, 4, 3, 2, 1],
            max_score=5
        ),
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Training Programs',
            text='Has your company invested in training programs to upskill employees in AI-related competencies?',
            options=["Yes, through external vendors.",
                     "Yes, with comprehensive internal programs.",
                     "No, but plans to in the future.",
                     "No, with no plans.",
                     "Unsure"],
            scores=[5, 4, 3, 1, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Knowledge Sharing',
            text='Does your organization have mechanisms for knowledge sharing and documentation of best practices in AI development?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Cross-functional Collaboration',
            text='Are there opportunities for collaboration between technical teams and domain experts in AI projects?',
            options=["Yes", "No"],
            scores=[5, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Cultural Readiness',
            text='How urgently is your organization looking to embrace AI?',
            options=["High urgency", "Moderate urgency", "Limited urgency", "No urgency"],
            scores=[5, 4, 3, 1],
            max_score=5
        ),
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Board Receptiveness',
            text='How receptive is your Board to changes brought about by AI?',
            options=["High receptiveness", "Moderate receptiveness", "Limited receptiveness", "Not receptive", "Unsure"],
            scores=[5, 4, 3, 1, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Leadership Receptiveness',
            text='How receptive is your Leadership Team to changes brought about by AI?',
            options=["High receptiveness", "Moderate receptiveness", "Limited receptiveness", "Not receptive", "Unsure"],
            scores=[5, 4, 3, 1, 0],
            max_score=5
        ),
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Change Management Plan',
            text='Do you have a change management plan in place to address changes brought about by AI?',
            options=["Yes", "No", "Developing"],
            scores=[5, 0, 3],
            max_score=5
        ),
        AssessmentQuestion(
            category='Organization (Talent & Culture)',
            subcategory='Employee Receptiveness',
            text='How receptive are your employees to changes brought about by AI?',
            options=["High receptiveness", "Moderate receptiveness", "Limited receptiveness", "Not receptive", "Unsure"],
            scores=[5, 4, 3, 1, 0],
            max_score=5
        ),
    ]
    db.session.bulk_save_objects(questions)
    db.session.commit()


def calculate_score(assessment):
    responses = Response.query.filter_by(assessment_id=assessment.id).all()
    category_scores = {
        'Strategy': 0,
        'Governance': 0,
        'Data & Infrastructure': 0,
        'Organization (Talent & Culture)': 0
    }
    category_max_scores = {
        'Strategy': 19,
        'Governance': 17,
        'Data & Infrastructure': 20,
        'Organization (Talent & Culture)': 17
    }

    for response in responses:
        question = AssessmentQuestion.query.get(response.question_id)
        if question and question.options:
            option_index = question.options.index(response.answer)
            score = question.scores[option_index]
            category_scores[question.category] += score
            
    # Normalize scores to respect maximum categories scores
    for category in category_scores:
        category_scores[category] = min(category_scores[category],
                                        category_max_scores[category])

    assessment.strategy_score = category_scores['Strategy']
    assessment.governance_score = category_scores['Governance']
    assessment.data_infrastructure_score = category_scores['Data & Infrastructure']
    assessment.organization_score = category_scores['Organization (Talent & Culture)']

    total_score = sum(category_scores.values())
    assessment.total_score = total_score

    if total_score <= 21:
        assessment.readiness_level = 'AI Novice'
    elif total_score <= 43:
        assessment.readiness_level = 'AI Ready'
    elif total_score <= 65:
        assessment.readiness_level = 'AI Proficient'
    else:
        assessment.readiness_level = 'AI Advanced'

    db.session.commit()
    
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)
    
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('register'))
        new_user = User(email=form.email.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/start_assessment')
@login_required
def start_assessment():
    assessment = Assessment(user_id=current_user.id)
    db.session.add(assessment)
    db.session.commit()
    return redirect(url_for('assessment_question', assessment_id=assessment.id))

@app.route('/assessment/<int:assessment_id>', methods=['GET', 'POST'])
@login_required
def assessment_question(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        flash('Unauthorized access to assessment', 'danger')
        return redirect(url_for('dashboard'))
    
    questions = AssessmentQuestion.query.all()
    current_question_index = assessment.current_question - 1
    
    if current_question_index >= len(questions):
        return redirect(url_for('assessment_complete', assessment_id=assessment_id))
    
    current_questions = questions[current_question_index:current_question_index+4]
    
    if request.method == 'POST':
        for question in current_questions:
            answer = request.form.get(f'question_{question.id}')
            if answer:
                response = Response(assessment_id=assessment_id, question_id=question.id, answer=answer)
                db.session.add(response)
        assessment.current_question += len(current_questions)
        
        db.session.commit()
        return redirect(url_for('assessment_question', assessment_id=assessment_id))
    return render_template('assessment_questions.html', questions=current_questions, assessment=assessment)

@app.route('/assessment/<int:assessment_id>/complete')
@login_required
def assessment_complete(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        flash('Unauthorized access to assessment', 'danger')
        return redirect(url_for('dashboard'))
    
    calculate_score(assessment)
    assessment.status = 'Complete'
    assessment.completion_date = datetime.now(timezone.utc)
    db.session.commit()
    
    return render_template('assessment_complete.html', assessment=assessment, strategy_score=assessment.strategy_score,
                           governance_score=assessment.governance_score,
                           data_infrastructure_score=assessment.data_infrastructure_score,
                           organization_score=assessment.organization_score,
                           total_score=assessment.total_score,
                           readiness_level=assessment.readiness_level)
    
@app.route('/assessment/<int:assessment_id>/pdf')
@login_required
def generate_pdf(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        flash('Unauthorized access to assessment', 'danger')
        return redirect(url_for('dashboard'))

    pdf_buffer = generate_pdf_report(assessment)
    pdf_buffer.seek(0)
    return send_file(
        io.BytesIO(pdf_buffer.getvalue()),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'AI_Readiness_Report_{assessment_id}.pdf'  # Changed from attachment_filename
    )

with app.app_context():
    db.drop_all()
    db.create_all()
    populate_questions()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not AssessmentQuestion.query.first():
            populate_questions()
    app.run(debug=True)