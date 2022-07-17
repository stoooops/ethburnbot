all: build start logs

build:
	docker build -f Dockerfile -t ethburnbot .

start:
	docker-compose up -d --force-recreate

stop:
	docker-compose down -d

logs:
	docker-compose logs --tail=100 --follow

lint:
	./bin/lint
