from upscale.wsgi import application
import waitress
import logging
import os



if __name__ == "__main__":
    logging.warning("APP RUNNING")
    port = int(os.environ.get("PORT", "80"))
    waitress.serve(application, host="0.0.0.0", port=port)