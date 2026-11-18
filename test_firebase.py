
from app.core.firebase import initialize_firebase

if __name__ == "__main__":
    app = initialize_firebase()

    print("Firebase app name:", app.name)
    print("Firebase project ID:", app.project_id)
