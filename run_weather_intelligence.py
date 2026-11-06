"""Launch the Weather Intelligence dashboard on localhost and open a browser."""

import threading
import webbrowser

from Backend.app import create_app


HOST = '127.0.0.1'
PORT = 5000
URL = f'http://{HOST}:{PORT}/'


def open_dashboard():
    webbrowser.open(URL, new=2)


if __name__ == '__main__':
    application = create_app()
    print(f'Weather Intelligence will open at {URL}')
    print('Keep this terminal open while using the dashboard. Press Ctrl+C to stop.')
    threading.Timer(1.0, open_dashboard).start()
    try:
        application.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    except OSError as error:
        raise SystemExit(
            f'Could not start the local server at {URL}. '
            'Check whether another app is already using port 5000.'
        ) from error
