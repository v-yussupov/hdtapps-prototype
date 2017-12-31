## hdtapps-prototype: 
A prototypical implementation of a framework for handling data transformation applications in the context of TraDE Middleware 

Requirements:
Python 3.6, MongoDB, Docker, Celery+Redis as a broker

## Installation

1. Create virtual environment: <br>
  a) navigate to project's folder <br>
  b) create virtual environment: <b>python -m venv venv</b>  <br>

2. Activate virtual environment: <br>
   Linux: source venv/bin/activate <br>
   Windows: venv\Scripts\activate.bat <br>

3. Install using pip: pip install -r requirements.txt (or pip3 install -r requirements.txt) <br>
4. Change MongoDB and Redis configurations in config.py if not default ports are used

## Running

1. In one terminal instance activate the virtual environment and run a Celery worker
 using the following command: <b>celery worker -A celery_worker.celery --loglevel=info</b><br>
2. In another terminal instance activate the virtual environment and run the application using the following command: <b>python -m run </b><br>
3. Connect using localhost:8080 <br>
4. Test API calls at http://localhost:8080/ui using <a href="https://github.com/swagger-api/swagger-ui">Swagger UI</a>

## Project's structure

- app/ - application <br>
--- mod_repo/ - repository module <br>
--- mod_tm/ - task manager module <br>
--- mod_swagger_ui/ - <a href="https://github.com/swagger-api/swagger-ui">Swagger UI</a> to simplify working with prototype's API <br>
--- static/ - static files <br>
--- templates/ - Jinja2 templates <br>
- config.py - configuration settings <br>
- run.py - launcher

