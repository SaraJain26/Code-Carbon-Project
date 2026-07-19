def save_data():
    with open("output.txt", "w") as f:
        f.write("Hello")

def load_data():
    with open("output.txt", "r") as f:
        return f.read()

save_data()
load_data()