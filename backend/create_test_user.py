import sys
sys.path.insert(0, "src")

import bcrypt
from sqlmodel import Session, select
from database import engine
from models import User

EMAIL = "test@test.com"
PASSWORD = "test1234"

def main():
    hashed = bcrypt.hashpw(PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == EMAIL)).first()
        if existing:
            existing.hashed_password = hashed
            session.add(existing)
            session.commit()
            print(f"Utilisateur {EMAIL} mis à jour (nouveau mot de passe).")
        else:
            user = User(email=EMAIL, hashed_password=hashed)
            session.add(user)
            session.commit()
            print(f"Utilisateur {EMAIL} créé.")

if __name__ == "__main__":
    main()