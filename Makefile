
all: build

build:
	docker build -f Dockerfile -t ethburnbot .

up:
	docker-compose up -d

logs:
	docker-compose logs --follow

lint:
	./bin/lint

