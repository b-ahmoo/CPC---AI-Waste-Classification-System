"""
Streamlit Frontend for Subsystem 1: User Management & Authentication
"""

import streamlit as st
from app.models.usermanagement_models import Country, User
from app.subsystems.usermanagement import AccountService, WasteIntegration

st.title("♻️ AI Waste Classification System")
st.subheader("Subsystem 1: User Management & Authentication")

# Initialize service
if "account_service" not in st.session_state:
    st.session_state.account_service = AccountService()

service = st.session_state.account_service

tab_login, tab_signup, tab_profile = st.tabs(["Login", "Sign Up", "Profile & Waste Rules"])

with tab_signup:
    st.markdown("### Create a New Account")
    with st.form("signup_form"):
        new_user_id = st.text_input("User ID (e.g., u2)")
        new_username = st.text_input("Username")
        new_email = st.text_input("Email Address")
        country_name = st.text_input("Country Name (e.g., Germany)")
        country_code = st.text_input("Country Code (e.g., DE)")
        
        submit_signup = st.form_submit_button("Sign Up")
        
        if submit_signup:
            if new_user_id and new_username and new_email and country_name and country_code:
                country = Country(country_id=f"c_{new_user_id}", name=country_name, code=country_code.upper())
                user = service.create_account(new_user_id, new_username, new_email, country)
                st.success(f"Account successfully created for {user.username}!")
                st.session_state.logged_in_user = user.user_id
            else:
                st.warning("Please fill in all fields.")

with tab_login:
    st.markdown("### Log In to Your Account")
    with st.form("login_form"):
        login_email = st.text_input("Email Address")
        submit_login = st.form_submit_button("Log In")
        
        if submit_login:
            user = service.login(login_email)
            if user:
                st.session_state.logged_in_user = user.user_id
                st.success(f"Welcome back, {user.username}!")
            else:
                st.error("Invalid email or inactive account.")

with tab_profile:
    st.markdown("### User Profile & Regional Waste Rules")
    current_user_id = st.session_state.get("logged_in_user")
    
    if current_user_id:
        active_user = service.find_user_by_id(current_user_id)
        if active_user:
            st.write(f"**Username:** {active_user.username}")
            st.write(f"**Email:** {active_user.email}")
            if active_user.country:
                st.write(f"**Country:** {active_user.country.name} ({active_user.country.code})")
            
            st.divider()
            regulations = WasteIntegration.get_user_waste_regulations(active_user)
            st.markdown("#### 🌍 Applicable Regional Guidelines")
            st.info(regulations["local_disposal_guidelines"])
            
            if st.button("Deactivate Account"):
                service.deactivate_user_account(active_user.user_id)
                st.warning("Account deactivated.")
    else:
        st.warning("Please log in or sign up to view your profile.")
