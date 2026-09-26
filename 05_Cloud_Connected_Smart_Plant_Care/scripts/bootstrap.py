"""Prepare a local environment without creating shared demo credentials."""
from pathlib import Path
import secrets

def main():
    destination=Path('.env')
    if not destination.exists():
        destination.write_text('JWT_SECRET='+secrets.token_urlsafe(48)+'\nDATABASE_URL=sqlite:///./plantcare.db\nAPP_ENV=development\n',encoding='utf-8')
        print('Local configuration created. Start the app and choose Try interactive demo or Create an account.')
    else:
        print('Existing local configuration preserved.')

if __name__=='__main__':
    main()
