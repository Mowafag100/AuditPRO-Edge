up:
	docker compose up --build -d

down:
	docker compose down

rebuild:
	docker compose down
	docker compose up --build -d

setup:
	sudo apt install -y python3-venv
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
