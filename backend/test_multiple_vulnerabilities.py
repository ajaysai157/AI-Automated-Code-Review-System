import os
import sqlite3

user_input = input("Enter expression: ")
result = eval(user_input)

password = "admin123"
print("Password:", password)

username = input("Username: ")
query = "SELECT * FROM users WHERE username = '" + username + "'"

api_key = "sk-test-123456789"