
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

    
    # Check the user's current verification status
    decoded = verify_firebase_id_token(id_token)

    if decoded.get("email_verified", False):
        print("\nEmail is already verified.")
        print("Verification email will not be sent.")

    else:
        # Send Firebase email verification
        verification_url = (
            "https://identitytoolkit.googleapis.com/v1/"
            f"accounts:sendOobCode?key={api_key}"
        )

        verification_response = requests.post(
            verification_url,
            json={
                "requestType": "VERIFY_EMAIL",
                "idToken": id_token,
            },
            timeout=20,
        )

        if verification_response.status_code == 200:
            print("\nVerification email sent successfully!")
            print("Email:", verification_response.json().get("email"))
        else:
            print("\nFailed to send verification email.")
            print("Status:", verification_response.status_code)
            print("Response:", verification_response.json())



    print("\nFirebase login successful.")

    decoded = verify_firebase_id_token(id_token)

    print("ID token verification successful!")

    print("Firebase UID:", decoded["uid"])
    print("Email:", decoded.get("email"))

    # Call the protected FastAPI endpoint.
    api_response = requests.get(
        "http://127.0.0.1:8000/auth/me",
        headers={
            "Authorization": f"Bearer {id_token}"
        },
        timeout=20,
    )

    print("\nFastAPI /auth/me response:")
    print("HTTP Status:", api_response.status_code)
    print("Response:", api_response.json())
    print("Email verified:", decoded.get("email_verified"))


if __name__ == "__main__":
    main()
