# AI Nutrition Diary (KI Ernährungstagebuch)

A modern, web-based AI nutrition diary that allows users to log their meals and symptoms via a conversational chat interface. The application uses the `antigravity-cli` (`agy`) as an AI backend to intelligently parse user input (both text and images) into structured data.

## Features
- **Conversational Interface**: Log food and symptoms just by chatting with the AI.
- **Image Support**: Upload pictures of your meals for automatic recognition and logging.
- **Smart Parsing**: Powered by Google's Gemini models via the `antigravity-cli`, extracting structured meal and symptom data automatically.
- **Responsive Web App**: Built with vanilla HTML/JS/CSS for a fast, responsive user experience.
- **FastAPI Backend**: A lightweight and fast Python backend.

## Tech Stack
- **Backend**: Python, FastAPI
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **AI Integration**: `antigravity-cli` (`agy`)
- **Containerization**: Docker, Docker Compose

## Setup and Installation

### Prerequisites
- Docker and Docker Compose installed on your system.

### Running the Application
The application is fully containerized and can be started with Docker Compose:

1. Clone the repository and navigate into the project directory.
2. Build and start the containers:
   ```bash
   docker-compose up --build
   ```
3. Open your web browser and navigate to `http://localhost:8000`.

### Data Storage
Data such as logged meals and symptoms are stored in the local `_nutrition_data_volume` directory, which is mapped into the container.

## Architecture
- `app/main.py`: The FastAPI application entry point, handling routing and HTTP requests.
- `app/agy_client.py`: The client wrapper for interacting with the `antigravity-cli` via subprocesses.
- `app/storage.py`: Handles saving the structured parsed data locally.
- `app/static/`: Contains the frontend assets (`index.html`, `app.js`, `index.css`).
- `docker-compose.yml`: Defines the services and volume mappings for the Docker environment.
