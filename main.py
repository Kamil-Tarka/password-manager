from database_settings import engine
from models.entities import Base
from view.console_view import start_console_view


def main():
    Base.metadata.create_all(bind=engine)
    start_console_view()


if __name__ == "__main__":
    main()
