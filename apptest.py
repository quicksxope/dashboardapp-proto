import streamlit as st
from authenticator import authenticator
import pages.finance as finance
import pages.logistics as logistics
import pages.operations as operations
import pages.hr as hr

# Login
name, auth_status, username = authenticator.login("Login", "main")

if auth_status:
    st.sidebar.write(f"Welcome, {name}!")
    authenticator.logout("Logout", "sidebar")

    # Role-based routing
    role = authenticator.credentials['usernames'][username]['role']

    if role == "finance":
        finance.render()
    elif role == "logistics":
        logistics.render()
    elif role == "operations":
        operations.render()
    elif role == "hr":
        hr.render()
    else:
        st.error("Unauthorized role.")
elif auth_status is False:
    st.error("Incorrect username or password.")
elif auth_status is None:
    st.warning("Please enter your credentials.")
