import Application as app
import tkinter as tk



if __name__ == "__main__":
    version = '2.20.0'
    root = tk.Tk()
    root.title('RATTATA | Reusable Attack Trees Tool Accessible To All.')
    myapp = app.Application(version=version, master=root, testmode=False)
    myapp.mainloop()

# pyinstaller src/main.py --name RATTATA --onefile
