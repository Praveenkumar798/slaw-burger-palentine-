import requests
import json

# ===== PASTE YOUR CREDENTIALS HERE =====
CLIENT_ID = "IVBGGEpqq7fwIzqNuiOa88WBA0bh4Gak"
CLIENT_SECRET = "zoeI6cYIjj7CLpUNxbpbX-OKlti9hhn43AWcBYD3QqhMsJUfdE91Rta6wuE7e-Bp"
# =======================================

def get_access_token():
    """Get Toast API Access Token"""
    
    print("="*70)
    print("STEP 1: Getting Toast API Access Token")
    print("="*70)
    
    url = "https://ws-api.toasttab.com/authentication/v1/authentication/login"
    
    payload = {
        "clientId": CLIENT_ID,
        "clientSecret": CLIENT_SECRET,
        "userAccessType": "TOAST_MACHINE_CLIENT"
    }
    
    headers = {"Content-Type": "application/json"}
    
    print("\nRequesting access token...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('token', {}).get('accessToken')
            expires = data.get('token', {}).get('expiresIn')
            
            print("\nSUCCESS! Access Token Generated")
            print("="*70)
            print(f"\nACCESS_TOKEN:")
            print(f"{token}")
            print(f"\nExpires in: {expires} seconds ({expires/3600:.1f} hours)")
            print("="*70)
            
            # Save to file
            with open("toast_token.txt", "w") as f:
                f.write(f"ACCESS_TOKEN={token}\n")
                f.write(f"EXPIRES_IN={expires}\n")
            
            print("\nToken saved to: toast_token.txt")
            
            return token
        else:
            print(f"\nERROR: {response.status_code}")
            print(f"Response: {response.text}")
            print("\nCHECK:")
            print("   1. Client ID is correct")
            print("   2. Client Secret is correct")
            print("   3. You have API access enabled in Toast Developer Portal")
            return None
            
    except Exception as e:
        print(f"\nException: {str(e)}")
        return None

if __name__ == "__main__":
    token = get_access_token()
    
    if token:
        print("\nSTEP 1 COMPLETE!")
        print("Next: Run Guid_toast.py")
    else:
        print("\nSTEP 1 FAILED - Fix errors above and try again")



        #eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik9FSkZNRUZEUlRkRVEwWkJPVFkwTWprNU9UUkRNVFZHUXpFMlJURkdNalUzUVRjeE16TTFNUSJ9.eyJodHRwczovL3RvYXN0dGFiLmNvbS9jbGllbnRfbmFtZSI6IkNBQWI4ZjU3MzlhNTkxODQiLCJodHRwczovL3RvYXN0dGFiLmNvbS9hY2Nlc3NfdHlwZSI6IlRPQVNUX01BQ0hJTkVfQ0xJRU5UIiwiaHR0cHM6Ly90b2FzdHRhYi5jb20vZXh0ZXJuYWxfaWQiOiJDQUFiOGY1NzM5YTU5MTg0IiwiaHR0cHM6Ly90b2FzdHRhYi5jb20vcGFydG5lcl9ndWlkIjoiMWMwZGQwNGMtYzIzMC00ZWQ1LTlhYmYtNTZmYTQxZDIzYzZkIiwiaHR0cHM6Ly90b2FzdHRhYi5jb20vdHlwZSI6IklOREVQRU5ERU5UX1BBUlRORVIiLCJpc3MiOiJodHRwczovL3RvYXN0LXBvcy50b2FzdHRhYi5hdXRoMC5jb20vIiwic3ViIjoiSVZCR0dFcHFxN2Z3SXpxTnVpT2E4OFdCQTBiaDRHYWtAY2xpZW50cyIsImF1ZCI6Imh0dHBzOi8vdG9hc3Qtc2VydmljZXMtYXBpLyIsImlhdCI6MTc2NzYwMDA4MiwiZXhwIjoxNzY3Njg2NDgyLCJzY29wZSI6ImNhc2htZ210OnJlYWQgY29uZmlnOnJlYWQgZGVsaXZlcnlfaW5mby5hZGRyZXNzOnJlYWQgZGlnaXRhbF9zY2hlZHVsZTpyZWFkIGd1ZXN0LnBpOnJlYWQga2l0Y2hlbjpyZWFkIGxhYm9yOnJlYWQgbGFib3IuZW1wbG95ZWVzOnJlYWQgbWVudXM6cmVhZCBvcmRlcnM6cmVhZCBwYWNrYWdpbmc6cmVhZCByZXN0YXVyYW50czpyZWFkIHN0b2NrOnJlYWQiLCJndHkiOiJjbGllbnQtY3JlZGVudGlhbHMiLCJhenAiOiJJVkJHR0VwcXE3ZndJenFOdWlPYTg4V0JBMGJoNEdhayJ9.syT5jof7CMDys_L8vwGnvdlukGzJdMv1xSIsqjb5qkLafaNwwXYAq4Y-3d8THI7upKBLupGhWUjvm0-iKqk6jD0lNL2VgtErEPTTpYtIwzfz6Frr5z2Z5a6ElisT6bH5omL3WlSSYCFXG-1RP_4JhuOAJOlQghLdC83JHhe7T7v34_ZJA4m1zAqlGeXRfObh5QM--TY2Wi1WeC1jFmeKffAxdi2k5Fwg_pkdXlFxS7GvbNgbp4ZD0HPciVrkGMaitIt14BoBWicuK4-y86a1p0RjuoMO7ApNgt8jTmx8AQm-eY6cfjopt1wl_nYP-DHpZ5twX1AuGfwFvE44Wm9_5g