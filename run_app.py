from upscale.wsgi import application
import waitress
import logging



if __name__ == "__main__":
    logging.warning("APP RUNNING")
    waitress.serve(application , host = '0.0.0.0' ,  port = 80)