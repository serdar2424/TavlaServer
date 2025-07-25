# Backgammon Server

This repository contains the backend server for the Backgammon application, built using **FastAPI**, a modern, fast (high-performance) web framework for building APIs with Python.

A **swagger interface** is automatically provided by FastAPI, and can be accessed at `serveraddressexample.com/docs`, so for example at [localhost:8000/docs](http://localhost:8000/docs)

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Technologies Used](#technologies-used)
4. [Folder Structure](#folder-structure)
5. [Server setup](#server-setup)
6. [Running the Server](#running-the-server)
7. [Testing](#testing)
8. [Authors](#authors)

---

## Overview

The server is responsible for handling game logic, user authentication, and communication with the client application. It exposes a RESTful API that the client can interact with.

---

## Features

- Game logic for Backgammon (validation of moves, turn management, etc.).
- User authentication (token-based).
- Real-time game updates via WebSockets.

---

## Technologies Used

- **Framework:** FastAPI
- **Database:** MongoDB
- **Testing:** Pytest
- **Documentation:** Swagger UI (built-in with FastAPI)
- **Environment Management:** Python `venv`
- **Dependency Management:** `requirements.txt`

---

## Folder Structure

The `server` folder contains the backend code for the application. Below is a description of the key files and directories:

- **`core/`**: Contains core configurations and settings.
    - **`config.py`**: Configuration file for global variables and settings.
  
- **`middleware/`**: Contains middleware modules for the FastAPI application.
  - **`auth.py`**: Middleware for handling user authentication.

- **`models/`**: Contains the data models used by the application.
  - **`board_configuration.py`**: Configuration for the backgammon board.
  - **`tournament.py`**: Data model for tournaments.
  - **`user.py`**: Data model for users.

- **`routes/`**: Contains the route definitions for the API, organized by functionality.
  - **`auth.py`**: Routes for user authentication.
  - **`game.py`**: Routes for game management.
  - **`invites.py`**: Routes for game invitations.
  - **`tournaments.py`**: Routes for tournament management.
  - **`users.py`**: Routes for user management.

- **`services/`**: Contains service modules for various functionalities.
  - **`ai.py`**: Service for AI moves.
  - **`auth.py`**: Service for user authentication.
  - **`board.py`**: Service for board management.
  - **`database.py`**: Service for database operations.
  - **`game.py`**: Service for game logic.
  - **`invite.py`**: Service for game invitations.
  - **`rating.py`**: Service for user ratings.
  - **`tournament.py`**: Service for tournament management.
  - **`user.py`**: Service for user management.
  - **`websocket.py`**: Service for WebSocket communication.

- **`tests/`**: Contains test cases for the server.
  - **`conftest.py`**: Configuration for pytest fixtures.
  - **`test_ai.py`**: Test cases for AI moves.
  - **`test_auth.py`**: Test cases for user authentication.
  - **`test_board_configuration.py`**: Test cases for board management.
  - **`test_board_service.py`**: Test cases for game logic.
  - **`test_game.py`**: Test cases for game management.
  - **`test_invites.py`**: Test cases for game invitations.
  - **`test_rating.py`**: Test cases for user ratings.
  - **`test_tournaments.py`**: Test cases for tournament management.
  - **`test_user.py`**: Test cases for user management.
  - **`test_websocket.py`**: Test cases for WebSocket communication.

- **`.coveragerc`**: Configuration file for code coverage settings.
- **`.env.example`**: Example environment variables file.
- **`coverage.xml`**: Code coverage report in XML format.
- **`Dockerfile`**: Docker configuration file for building the server image.
- **`main.py`**: The entry point for the FastAPI application.
- **`requirements.txt`**: Lists the Python dependencies for the server.
- **`README.md`**: The documentation file for the server directory.

## Server Setup

To manage dependency versions you should use Python virtual environments.

1. Create one with the following command (name it ``venv`` to use the current ``.gitignore`` configuration)
```sh
python3 -m venv venv
```

2. Activate the virtual environment

- On Windows:
    ```sh
    .\venv\Scripts\activate
    ```
- On macOS and Linux:
    ```sh
    source venv/bin/activate
    ```

3. Install the required dependencies
```sh
pip install -r requirements.txt
```

4. Install new packages as needed as usual
```sh
pip install <package-name>
```

5. Update the ``requirements.txt`` file with new dependencies
```sh
pip freeze > requirements.txt
```

6. Deactivate the environment with the following command
```sh
deactivate
```
## Running the Server
Before running the server, make sure you have activated the virtual environment. <br>
To run the server, execute the following command:

```sh
uvicorn main:app --reload
```

## Testing

To test the server code you can use ``pytest``. Run the following command:

```sh
pytest -v
```

To generate an HTML code coverage report that can be opened in the browser:
```sh
pytest --cov --cov-report=xml:coverage.xml --cov-config=.coveragerc
```

Afterwards **remember to replace** all `filename=` with `filename=server/`, as sonarqube requires the coverage to be relative to the absolute path of the root folder.

---

## Authors

The SCRUM team for this project consists of the following members:

- **Scrum Master**: [Cristian Orsi](mailto:cristiam.orsi2@studio.unibo.it)      
- **Product Owner**: [Enis Brajevic](mailto:enis.brajevic@studio.unibo.it)     
- **Developer 1**: [Matteo Fornaini](mailto:matteo.fornaini@studio.unibo.it)     
- **Developer 2**: [Mattia Ferrarini](mailto:mattia.ferrarini3@studio.unibo.it)    
- **Developer 3**: [Enrico Mazzotti](mailto:enrico.mazzotti2@studio.unibo.it)    
- **Developer 4**: [Lorenzo Giarrusso](mailto:lorenzo.giarrusso@studio.unibo.it)   