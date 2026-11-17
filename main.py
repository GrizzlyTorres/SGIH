from database.db_manager import init_db
from ui.app_window import SGIHApp


def main():
    init_db()
    app = SGIHApp()
    app.mainloop()


if __name__ == "__main__":
    main()