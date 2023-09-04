import streamlit as st
from pulp import LpMaximize, LpProblem, LpVariable, lpSum
import pandas as pd
from datetime import timedelta, datetime
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def to_csv_link(df):
    csv = df.to_csv(index=True)
    b64 = base64.b64encode(csv.encode()).decode()  
    return f'<a href="data:file/csv;base64,{b64}" download="schedule.csv">Download as CSV</a>'

st.title('Shift Scheduling Optimizer')

st.write("""
This website automatically generates an optimized shift schedule for your company, balancing workloads and preferences. 
The optimized schedule is then available for download as a CSV file. Below are some important notes:
- The optimization process aims to meet the 'Number of Workers Required per Day' as much as possible. 
- However, it prioritizes fulfilling the 'Number of Days Off Desired by Each Worker'.
""")

n_workers = st.number_input('Number of Workers:', min_value=1, max_value=20, value=5)
n_workers_per_day = st.number_input('Number of Workers Required per Day:', min_value=1, max_value=n_workers, value=3)

start_date = st.date_input("Start Date", value=datetime.strptime("2023-08-01", "%Y-%m-%d").date())
end_date = st.date_input("End Date", value=datetime.strptime("2023-08-31", "%Y-%m-%d").date())

if end_date < start_date:
    st.warning('The end date should be after the start date.')
    st.stop()

n_days = (end_date - start_date).days + 1

worker_names = st.text_input('Worker Names (comma separated):', 'A,B,C,D,E')

workers = [name.strip() for name in worker_names.split(',')]

if len(workers) != n_workers:
    st.warning('The number of worker names should match the number of workers.')
    st.stop()

days_off_dict = {}
for worker in workers:
    days_off_dict[worker] = st.number_input(f'Number of Days Off Desired by {worker}:', min_value=0, max_value=n_days, value=5)

model = LpProblem(name="shift-scheduling", sense=LpMaximize)

penalty = LpVariable(name="penalty", lowBound=0)

shift_types = [0, 1, 2, 3]
shift_mapping = {0: 'Off', 1: 'First Half', 2: 'Second Half', 3: 'Full Day'}

x = {
    (worker, (start_date + timedelta(days=day)).strftime('%Y-%m-%d'), shift_type): LpVariable(
        name=f"x_{worker}_{(start_date + timedelta(days=day)).strftime('%Y-%m-%d')}_{shift_type}",
        cat='Binary'
    )
    for worker in workers
    for day in range(n_days)
    for shift_type in shift_types
}

model += -penalty, "Minimize_Penalty"

for day in range(n_days):
    date_str = (start_date + timedelta(days=day)).strftime('%Y-%m-%d')
    for worker in workers:
        model += lpSum(x[worker, date_str, shift_type] for shift_type in shift_types) == 1, f"worker_{worker}_day_{date_str}_constraint"
    
    model += lpSum(x[worker, date_str, 1] * 0.5 + x[worker, date_str, 3] for worker in workers) >= n_workers_per_day - penalty, f"hard_full_and_first_{date_str}"
    model += lpSum(x[worker, date_str, 2] * 0.5 + x[worker, date_str, 3] for worker in workers) >= n_workers_per_day - penalty, f"hard_full_and_second_{date_str}"

for worker in workers:
    model += lpSum(x[worker, (start_date + timedelta(days=day)).strftime('%Y-%m-%d'), 0] for day in range(n_days)) == days_off_dict[worker], f"days_off_{worker}"

status = model.solve()

if status == 1:
    st.success('Optimal solution found.')

    data = {worker: {(start_date + timedelta(days=day)).strftime('%Y-%m-%d'): "" for day in range(n_days)} for worker in workers}

    for day in range(n_days):
        date_str = (start_date + timedelta(days=day)).strftime('%Y-%m-%d')
        for worker in workers:
            for shift_type in shift_types:
                var = x[worker, date_str, shift_type]
                if var.varValue:
                    data[worker][date_str] = shift_mapping[shift_type]

    df = pd.DataFrame.from_dict(data, orient='index')

    st.write(df)
    st.markdown(to_csv_link(df), unsafe_allow_html=True)
else:
    st.error('No solution found.')

# 問い合わせフォーム
st.header('Contact Us')
st.write("If you have any questions or feedback, please feel free to contact us using the form below:")
name = st.text_input("Name:")
email = st.text_input("Email:")
message = st.text_area("Message:")
if st.button("Submit"):
    # メール送信処理
    smtp_server = 'smtp.gmail.com'  # GmailのSMTPサーバーを使用する場合
    smtp_port = 587  # GmailのSMTPポート番号

    sender_email = 'your_email@gmail.com'  # 送信元のメールアドレス
    sender_password = 'your_password'  # 送信元のメールアドレスのパスワード

    recipient_email = '****'  # 送信先のメールアドレス

    subject = 'Contact Us Form Submission'
    message_text = f"Name: {name}\nEmail: {email}\nMessage: {message}"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message_text, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        st.success("Message sent successfully!")
    except Exception as e:
        st.error(f"An error occurred: {e}")

# プライバシーポリシー
st.header('Privacy Policy')
st.write("We respect your privacy and handle your personal information with care. This policy outlines how we collect, use, and protect your data when you use our [Service/Website].")
st.write("Information We Collect：We may collect your name, email address, and other contact details. We also gather technical information such as log data and cookies.")
st.write("How We Use Your Information：We use the collected information for providing and improving our services, as well as for communication, customization, and promotional purposes.")
st.write("Sharing and Disclosure：We may share your information with trusted third parties for the purposes outlined in this policy, except when required by law or with your consent.")
st.write("Data Security：We take appropriate measures to protect your personal information from unauthorized access, disclosure, or misuse.")
st.write("Cookies：We may use cookies to analyze usage patterns and enhance your experience. You can adjust your browser settings to refuse cookies.")
st.write("Contact Us：For any questions regarding this Privacy Policy, please contact us at [Contact Information].")
st.write("Changes and Updates：We reserve the right to update this Privacy Policy as needed. We will notify you of significant changes through appropriate means.")
