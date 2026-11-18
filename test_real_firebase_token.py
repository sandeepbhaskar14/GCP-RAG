
import getpass
import requests

from app.core.security import verify_firebase_id_token


def main():
    api_key = getpass.getpass("Firebase Web API Key: ")
    email = input("Test user email: ").strip()
    password = getpass.getpass("Test user password: ")

    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signInWithPassword?key={api_key}"
    )

    response = requests.post(
        url,
        json={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        },
        timeout=20,
    )

    if response.status_code != 200:
        print("Firebase login failed.")
        print("HTTP status:", response.status_code)
        print("Response:", response.json())
        return

    id_token = response.json()["idToken"]

    print("\nFirebase login successful.")

    decoded = verify_firebase_id_token(id_token)

    print("ID token verification successful!")
    print("Firebase UID:", decoded["uid"])
    print("Email:", decoded.get("email"))
    print("Email verified:", decoded.get("email_verified"))


if __name__ == "__main__":
    main()
