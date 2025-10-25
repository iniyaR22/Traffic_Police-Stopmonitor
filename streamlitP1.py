import streamlit as st
import pandas as pd
import plotly.express as px
import mysql.connector


def create_connection():
    try:
        connection = mysql.connector.connect(
        host = "gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
        port = 4000,
        user = "3k51nZsQpw5fDsi.root",
        password = "wPp6beRvkSzwGtZQ",
        database='project'
        )
        return connection

    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None


#fetch data from database 

def fetch_data(query):
    connection = create_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                df = pd.DataFrame(result, columns=columns)
                return df
        finally:
            connection.close()
    else:
        return pd.DataFrame()

#streamlit UI

st.set_page_config(page_title="securecheck logs", layout="wide")

st.title("**🚓🚨SECURE_CHECK: Police Stop Logs**")

st.markdown("Law Enforcement & Public Safety Real-time Monitoring Systems")

st.image("D:/iniya/pic/police-officer.jpg")

# table_overview
st.header("POLICE LOGS OVERVIEW")
query = query = """
SELECT 
    v.vehicle_number,
    v.driver_gender,
    v.driver_age,
    v.driver_race,
    v.timestamp,
    vv.violation_type,
    vv.drugs_related_stop,
    c.stop_outcome,
    c.stop_duration
FROM vehicles v
JOIN violation vv ON v.vehicle_number = vv.vehicle_number
JOIN check_post_logs c ON v.vehicle_number = c.vehicle_number
"""

data = fetch_data(query)

st.dataframe(data,use_container_width=True)


#quick metrics 
st.header("Top Actions")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_stop = data.shape[0]
    st.metric("Total Police Stops", total_stop)

with col2:
    arrests = data[data['stop_outcome'].str.contains("Arrest", case=False, na=False)].shape[0]
    st.metric("Total Arrests", arrests)

with col3:
    warnings = data[data['stop_outcome'].str.contains("Warning", case=False, na=False)].shape[0]
    st.metric("Total Warnings", warnings)

with col4:
        drugs_related = data[data['drugs_related_stop'].astype(str).str.contains("1", case=False, na=False)].shape[0]
        st.metric("Drug-Related Stops", drugs_related)

#advanced queries 

st.header("Explore Insights")

selected_query = st.selectbox("Select Your QUERY",[

    "1.Total number of police stops",
    "2.Top 10 vehicle_numbers involved in drug-related stops",
    "3.Which vehicles were most frequently searched?",
    "4.Which driver age group had the highest arrest rate?",
    "5.What is the gender distribution of drivers stopped in each country?",
    "6.Which race and gender combination has the highest search rate?",
    "7.What time of day sees the most traffic stops?",
    "8.What is the average stop duration for different violations?",
    "9.Which violations are most associated with searches or arrests?",
    "10.Which violations are most common among younger drivers (<25)?",
    "11.Is there a violation that rarely results in search or arrest?",
    "12.Which racer report the highest rate of drug-related stops?",
    "13.Which racer has the most stops with search conducted?",
#complex queries
    "14.Yearly breakdown of stops and arrests by country (uses window functions)",
    "15.Driver violation trends based on age and race",
    "16.Time period analysis of stops",
    "17.Violations with high search and arrest rates",
    "18.Top 5 violations with highest arrest rates"
])
query_map = {
    "1.Total number of police stops":"SELECT COUNT(*) AS total_stop FROM check_post_logs",
    "2.Top 10 vehicle_numbers involved in drug-related stops":"SELECT v.vehicle_number, COUNT(*) AS drug_stop_count FROM violation v JOIN check_post_logs c ON v.vehicle_number = c.vehicle_number WHERE v.drugs_related_stop='1' GROUP BY v.vehicle_number ORDER BY drug_stop_count DESC LIMIT 10",
    "3.Which vehicles were most frequently searched?":"SELECT c.vehicle_number, COUNT(*) AS search_count FROM check_post_logs c JOIN violation v ON c.vehicle_number=v.vehicle_number GROUP BY c.vehicle_number ORDER BY search_count DESC LIMIT 10",
    "4.Which driver age group had the highest arrest rate?":"SELECT age_group, ROUND(100.0 * SUM(is_arrest)/SUM(total),2) AS arrest_rate_pct FROM (SELECT v.vehicle_number, CASE WHEN v.driver_age<25 THEN 'Under 25' WHEN v.driver_age BETWEEN 25 AND 40 THEN '25-40' WHEN v.driver_age BETWEEN 41 AND 60 THEN '41-60' ELSE '60+' END AS age_group, CASE WHEN c.stop_outcome='Arrest' THEN 1 ELSE 0 END AS is_arrest, 1 AS total FROM vehicles v JOIN check_post_logs c ON v.vehicle_number=c.vehicle_number) t GROUP BY age_group ORDER BY arrest_rate_pct DESC",
    "5.What is the gender distribution of drivers stopped in each country?":"SELECT driver_race, driver_gender, COUNT(*) AS stops FROM vehicles GROUP BY driver_race, driver_gender ORDER BY driver_race, stops DESC",
    "6.Which race and gender combination has the highest search rate?":"SELECT v.driver_race, v.driver_gender, COUNT(*) AS search_count FROM vehicles v JOIN violation vi ON v.vehicle_number = vi.vehicle_number GROUP BY v.driver_race, v.driver_gender ORDER BY search_count DESC LIMIT 1",
    "7.What time of day sees the most traffic stops?":"#SELECT HOUR(v.timestamp) AS hour_of_day, COUNT(*) AS stops FROM vehicles v JOIN check_post_logs c ON v.vehicle_number=c.vehicle_number GROUP BY hour_of_day ORDER BY stops DESC",
    "8.What is the average stop duration for different violations?":"SELECT vi.violation_type, ROUND(AVG(c.stop_duration),2) AS avg_stop_duration FROM violation vi JOIN check_post_logs c ON vi.vehicle_number=c.vehicle_number GROUP BY vi.violation_type ORDER BY avg_stop_duration DESC",
    "9.Which violations are most associated with searches or arrests?":"SELECT vi.violation_type, COUNT(DISTINCT c.vehicle_number) AS total_linked_stops, SUM(CASE WHEN c.stop_outcome='Arrest' THEN 1 ELSE 0 END) AS arrests FROM violation vi JOIN check_post_logs c ON vi.vehicle_number = c.vehicle_number GROUP BY vi.violation_type ORDER BY arrests DESC, total_linked_stops DESC",
    "10.Which violations are most common among younger drivers (<25)?":"SELECT vi.violation_type, COUNT(*) AS count FROM violation vi JOIN vehicles v ON vi.vehicle_number=v.vehicle_number WHERE v.driver_age < 25 GROUP BY vi.violation_type ORDER BY count DESC",
    "11.Is there a violation that rarely results in search or arrest?":"SELECT vi.violation_type, COUNT(c.vehicle_number) AS linked_stops, SUM(CASE WHEN c.stop_outcome='Arrest' THEN 1 ELSE 0 END) AS arrests FROM violation vi LEFT JOIN check_post_logs c ON vi.vehicle_number=c.vehicle_number GROUP BY vi.violation_type HAVING linked_stops < 5 AND arrests = 0 ORDER BY linked_stops ASC",
    "12.Which racer report the highest rate of drug-related stops?":"SELECT driver_race, ROUND(100.0*SUM(CASE WHEN vi.drugs_related_stop='1' THEN 1 ELSE 0 END)/COUNT(*),2) AS pct_drug_stops FROM vehicles v JOIN violation vi ON v.vehicle_number=vi.vehicle_number GROUP BY driver_race ORDER BY pct_drug_stops DESC",
    "13.Which racer has the most stops with search conducted?":"SELECT driver_race, COUNT(DISTINCT vi.vehicle_number) AS searched_stops FROM vehicles v JOIN violation vi ON v.vehicle_number=vi.vehicle_number GROUP BY driver_race ORDER BY searched_stops DESC LIMIT 1",
#comple queries
    "14.Yearly breakdown of stops and arrests by country (uses window functions)":"SELECT driver_race, year, total_stops, total_arrests, ROUND(100.0*total_arrests/NULLIF(total_stops,0),2) AS arrest_rate_pct FROM (SELECT driver_race, YEAR(v.timestamp) AS year, COUNT(*) AS total_stops, SUM(CASE WHEN c.stop_outcome='Arrest' THEN 1 ELSE 0 END) AS total_arrests FROM vehicles v JOIN check_post_logs c ON v.vehicle_number=c.vehicle_number GROUP BY driver_race, YEAR(v.timestamp)) t ORDER BY driver_race, year",
    "15.Driver violation trends based on age and race":"SELECT t.age_group, t.driver_race, vi.violation_type, COUNT(*) AS count FROM (SELECT vehicle_number, CASE WHEN driver_age<25 THEN 'Under25' WHEN driver_age BETWEEN 25 AND 40 THEN '25-40' WHEN driver_age BETWEEN 41 AND 60 THEN '41-60' ELSE '60+' END AS age_group, driver_race FROM vehicles) t JOIN violation vi ON t.vehicle_number=vi.vehicle_number GROUP BY t.age_group, t.driver_race, vi.violation_type ORDER BY t.age_group, count DESC",
    "16.Time period analysis of stops":"SELECT YEAR(v.timestamp) AS year, DATE_FORMAT(v.timestamp,'%Y-%m') AS month, HOUR(v.timestamp) AS hour, COUNT(*) AS stops FROM vehicles v JOIN check_post_logs c ON v.vehicle_number=c.vehicle_number GROUP BY year, month, hour ORDER BY year, month, hour",
    "17.Violations with high search and arrest rates":"SELECT violation_type, total_searches, total_arrests, ROUND(100.0*total_arrests/NULLIF(total_searches,0),2) AS arrest_rate_pct FROM (SELECT vi.violation_type, COUNT(*) AS total_searches, SUM(CASE WHEN c.stop_outcome='Arrest' THEN 1 ELSE 0 END) AS total_arrests FROM violation vi JOIN check_post_logs c ON vi.vehicle_number=c.vehicle_number GROUP BY vi.violation_type) t ORDER BY arrest_rate_pct DESC LIMIT 5",
    "18.Top 5 violations with highest arrest rates":"SELECT violation_type, total_cases, total_arrests, ROUND(100.0*total_arrests/NULLIF(total_cases,0),2) AS arrest_rate_pct FROM (SELECT vi.violation_type, COUNT(*) AS total_cases, SUM(CASE WHEN c.stop_outcome='Arrest' THEN 1 ELSE 0 END) AS total_arrests FROM violation vi JOIN check_post_logs c ON vi.vehicle_number=c.vehicle_number GROUP BY vi.violation_type) t ORDER BY arrest_rate_pct DESC LIMIT 5"
}    

if st.button("RUN QUERY"):
    result = fetch_data(query_map[selected_query])
    if not result.empty:
        st.write(result)
    else:
        st.warning("no result found")



st.markdown("---")
st.markdown("SecureCheck: Enabling Smarter FIR Law Enforcement")

st.header("Police Check Post Entry Form")

#st.markdown(" Fill the form")

#input form 

with st.form("new_log_form"):
    stop_date = st.date_input("Stop Date")
    stop_time = st.time_input("Stop Time")
    county_name = st.text_input("County Name")
    driver_gender = st.selectbox("Driver Gender", ["male", "female"])
    driver_age = st.number_input("Driver Age", min_value=16, max_value=100, value=27)
    driver_race = st.text_input("Driver Race")
    search_conducted = st.selectbox("Was a Search Conducted?", ["0", "1"])
    search_type = st.text_input("Search Type")
    drugs_related_stop = st.selectbox("Was it Drug Related?", ["0", "1"])
    stop_duration = st.selectbox("Stop Duration", data['stop_duration'].dropna().unique())
    vehicle_numberst = st.text_input("Vehicle Number")
    timestamp = pd.Timestamp.now()

    submitted = st.form_submit_button("predict stop outcome nd voilation")
 
import platform

if submitted:
    # filter data for prediction
    filtered_data = data[
        (data['driver_gender'] == driver_gender) &
        (data['driver_age'] == driver_age) &
        (data['stop_duration'] == stop_duration) &
        (data['drugs_related_stop'] == int(drugs_related_stop))
    ]

    # Predict stop_outcome
    if not filtered_data.empty:
        predicted_outcome = filtered_data['stop_outcome'].mode()[0]
        predicted_violation = filtered_data['violation_type'].mode()[0]
    else:
        predicted_outcome = "warning"
        predicted_violation = "speeding"

    # natural lang summary
    search_text = "a search was conducted" if search_conducted == "1" else "no search"
    drug_text = "was drug related" if drugs_related_stop == "1" else "was not drug related"

    # Display result
    st.markdown("### 🚩PREDICTION SUMMARY")
    st.markdown(f"""
        **Predicted Violation:** {predicted_violation}  
        **Predicted Outcome:** {predicted_outcome}  

        🧾 A {driver_age}-year-old {driver_gender} driver in **{county_name}** was stopped at 
        **{stop_time.strftime('%I:%M %p')}** on **{stop_date}**.  
        {search_text}, and {drug_text}.  
        **Stop duration:** {stop_duration}. **Vehicle Number:** {vehicle_numberst or "****"}.
    """)