def run():
    st.title("Kids Management")

    # Load existing kids
    kids_df = load_kids()

    user = st.session_state.user  # Current logged-in user
    role = user["role"].lower()
    username = user["username"]

    # Filter for leaders
    if role == "leader":
        kids_df = kids_df[kids_df["Leader"] == username]

    # Display kids list
    st.subheader("Current Kids")
    if kids_df.empty:
        st.info("No kids found.")
    else:
        st.dataframe(kids_df)

    # Add new kid form
    st.subheader("Add a New Kid")
    with st.form("add_kid_form"):
        name = st.text_input("Kid's Name")
        age = st.number_input("Age", min_value=1, max_value=18)
        program = st.selectbox("Program", ["Sunday School", "Teens", "Youth"])

        submitted = st.form_submit_button("Add Kid")
        if submitted:
            if name.strip() == "":
                st.error("Name cannot be empty.")
            else:
                new_kid = {"Name": name.strip(), "Age": age, "Program": program, "Leader": username}
                # Convert dict to DataFrame
                new_kid_df = pd.DataFrame([new_kid])
                # Concatenate with existing DataFrame
                kids_df = pd.concat([kids_df, new_kid_df], ignore_index=True)
                save_kids(kids_df)
                st.success(f"Added {name} to {program}.")
                st.experimental_rerun()
