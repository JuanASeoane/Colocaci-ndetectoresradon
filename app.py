import streamlit as st

# Título de tu página web
st.title("📱 Mi Primera App en Móvil")

# Un texto explicativo
st.write("Esta app procesa datos directamente usando Python.")

# Una caja donde el usuario introduce un dato
nombre = st.text_input("Ingresa tu nombre:")

# Un botón que realiza una acción cuando se presiona
if st.button("Saludar"):
    if nombre:
        st.success(f"¡Hola {nombre}! Bienvenido a tu app web.")
    else:
        st.warning("Por favor, escribe tu nombre primero.")